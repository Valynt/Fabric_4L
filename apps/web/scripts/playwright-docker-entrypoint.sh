#!/bin/bash
set -e

# Ensure pnpm is available (corepack state may not persist across volume mounts)
corepack enable 2>/dev/null || true
corepack prepare pnpm@10.34.5 --activate 2>/dev/null || true

cd /app

# -----------------------------------------------------------------------------
# Seed node_modules from the baked image when the named volume is empty
# or when the image has been rebuilt.
# -----------------------------------------------------------------------------
NEEDS_SEED=false
if [ ! -d "/app/node_modules/.pnpm" ]; then
  NEEDS_SEED=true
elif [ -f "/baked/image-build.timestamp" ] && [ -f "/app/node_modules/.image-build.timestamp" ]; then
  if ! diff -q /baked/image-build.timestamp /app/node_modules/.image-build.timestamp >/dev/null 2>&1; then
    NEEDS_SEED=true
  fi
else
  NEEDS_SEED=true
fi

if [ "$NEEDS_SEED" = "true" ]; then
  echo "[playwright-docker] Seeding node_modules from baked image..."
  rm -rf /app/node_modules/..?* /app/node_modules/.[!.]* /app/node_modules/* 2>/dev/null || true
  cp -a /baked-node_modules/. /app/node_modules/
  if [ -f "/baked/image-build.timestamp" ]; then
    cp /baked/image-build.timestamp /app/node_modules/.image-build.timestamp
  fi
  echo "[playwright-docker] node_modules ready."
fi

# ---------------------------------------------------------------------------
# Production build for fast contract-test page loads
# ---------------------------------------------------------------------------
# When PLAYWRIGHT_WEBSERVER_COMMAND uses 'preview', we need a built dist/
# before Playwright starts its webServer. Building here ensures the bind
# mount sees the latest source while still benefiting from bundled assets.
# ---------------------------------------------------------------------------
if echo "$PLAYWRIGHT_WEBSERVER_COMMAND" | grep -q "preview"; then
  if [ ! -f /app/dist/public/index.html ] || [ /app/dist/public/index.html -ot /app/src/main.tsx ]; then
    echo "[playwright-docker] Building production bundle for preview server..."
    pnpm exec vite build
    echo "[playwright-docker] Build complete."
  else
    echo "[playwright-docker] Reusing existing production build."
  fi
fi

exec "$@"
