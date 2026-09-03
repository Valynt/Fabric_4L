#!/usr/bin/env bash
set -euo pipefail

readonly workspace=/workspace/Fabric_4L
cd "$workspace"

echo "Configuring the pinned JavaScript toolchain..."
if ! command -v pnpm >/dev/null 2>&1; then
  sudo corepack enable
  corepack prepare pnpm@10.34.5 --activate
fi

echo "Installing workspace dependencies from the frozen lockfile..."
pnpm install --frozen-lockfile

echo "Installing Python service dependencies through the canonical Make target..."
make setup

echo "Installing pre-commit hooks when available..."
if command -v pre-commit >/dev/null 2>&1; then
  pre-commit install || echo "pre-commit install skipped; run 'pre-commit install' manually if desired."
fi

echo "Verifying dev container environment health..."
bash "$workspace/.devcontainer/verify.sh"

cat <<'EOF'

Dev Container bootstrap complete. No secrets, migrations, or services were started.
See docs/development/DEV_CONTAINERS.md or run:
  .devcontainer/dev-stack.sh help
EOF
