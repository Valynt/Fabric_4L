#!/usr/bin/env bash
# scan_frontend.sh — Frontend audit scanner
# Usage: bash scan_frontend.sh <path-to-frontend-src>
# Outputs a structured report of dead-code signals and refactor opportunities.
# Excludes: ui/ component libraries, test files, __tests__ directories.

SRC="${1:-.}"
echo "=== Frontend Audit Scan: $SRC ==="
echo ""

# Helper: grep excluding tests and ui/ library components
src_grep() {
  grep -rn "$@" "$SRC" --include="*.ts" --include="*.tsx" \
    | grep -v "\.test\.\|\.spec\.\|__tests__\|/ui/"
}

# ── 1. Unused Zustand stores ──────────────────────────────────────────────────
echo "--- [1] Zustand store files (check usage outside stores/) ---"
find "$SRC/stores" -name "*.ts" -not -name "index.ts" 2>/dev/null | while read f; do
  name=$(basename "$f" .ts)
  count=$(grep -rl "$name" "$SRC" --include="*.ts" --include="*.tsx" \
          | grep -v "stores/" | grep -v "\.test\.\|\.spec\." | wc -l)
  if [ "$count" -eq 0 ]; then
    echo "  UNUSED: $name  ($f)"
  else
    echo "  OK ($count refs): $name"
  fi
done
echo ""

# ── 2. console.log in production source ──────────────────────────────────────
echo "--- [2] console.log / console.warn in source (not tests) ---"
src_grep "console\.log\|console\.warn" | grep -v "/ui/" | head -20
echo ""

# ── 3. Duplicate staleTime / poll interval magic numbers ─────────────────────
echo "--- [3] Inline staleTime / refetchInterval magic numbers ---"
src_grep "staleTime:\s*[0-9]\|refetchInterval:\s*[0-9]\|STALE_TIME\s*=\s*[0-9]\|POLL_INTERVAL\s*=\s*[0-9]" \
  | grep -v "useApiShared\|usePolling\|test-utils\|staleTime: 0"
echo ""

# ── 4. Duplicate query-key factories ─────────────────────────────────────────
echo "--- [4] Local query-key factory objects (candidates for centralisation) ---"
src_grep "^const [A-Z_]*KEYS\s*="
echo ""

# ── 5. Layer-prefix env-var reads outside a central config ───────────────────
echo "--- [5] Layer prefix env-var reads outside central apiConfig ---"
src_grep "import\.meta\.env\.VITE_L[0-9]_PREFIX\|import\.meta\.env\.VITE_API_BASE" \
  | grep -v "apiConfig\|api/client"
echo ""

# ── 6. ReactQueryDevtools not gated on dev ────────────────────────────────────
echo "--- [6] ReactQueryDevtools — should be dev-only ---"
result=$(src_grep "^import.*ReactQueryDevtools" | grep -v "import.meta.env.DEV")
if [ -z "$result" ]; then
  echo "  OK: ReactQueryDevtools is gated on DEV (or dynamically imported)"
else
  echo "  WARNING — ungated static import:"
  echo "$result"
fi
echo ""

# ── 7. Page imports not using React.lazy ─────────────────────────────────────
echo "--- [7] Eager page imports in routing file (not lazy) ---"
for f in "$SRC/App.tsx" "$SRC/Router.tsx" "$SRC/routes.tsx"; do
  [ -f "$f" ] && grep -n "^import.*from.*pages/" "$f" | grep -v "lazy\|Suspense"
done
echo ""

# ── 8. RouteGuard / ProtectedRoute missing auth check ────────────────────────
echo "--- [8] RouteGuard / ProtectedRoute — auth check present? ---"
found=0
for f in "$SRC/App.tsx" "$SRC/components/RouteGuard.tsx" "$SRC/components/ProtectedRoute.tsx"; do
  if [ -f "$f" ]; then
    hits=$(grep -c "isAuthenticated\|isLoggedIn\|useAuth\|session" "$f" 2>/dev/null || echo 0)
    if [ "$hits" -gt 0 ]; then
      echo "  OK ($hits hits): $f"
      found=1
    else
      echo "  WARNING — no auth check: $f"
    fi
  fi
done
[ "$found" -eq 0 ] && echo "  WARNING: no routing guard files found"
echo ""

# ── 9. Large page components missing memo ────────────────────────────────────
echo "--- [9] Page components >80 lines without React.memo ---"
find "$SRC/pages" -name "*.tsx" 2>/dev/null | grep -v "\.test\." | while read f; do
  lines=$(wc -l < "$f")
  if [ "$lines" -gt 80 ]; then
    has_memo=$(grep -c "React\.memo\|= memo(" "$f" 2>/dev/null)
    has_memo=${has_memo:-0}
    if [ "$has_memo" -eq 0 ]; then
      echo "  CANDIDATE ($lines lines): $f"
    fi
  fi
done
echo ""

# ── 10. Dead exported functions (not imported anywhere) ───────────────────────
echo "--- [10] Exported symbols with zero external imports ---"
src_grep "^export function\|^export const\|^export async function" \
  | grep -v "index\.ts\|queryKeys\|apiConfig\|usePolling\|useApiShared" \
  | while IFS=: read file line match; do
  sym=$(echo "$match" | grep -oP '(?<=function |const )\w+' | head -1)
  [ -z "$sym" ] && continue
  uses=$(grep -rl "\b$sym\b" "$SRC" --include="*.ts" --include="*.tsx" \
         | grep -v "^$file$" | grep -v "\.test\.\|\.spec\." | wc -l)
  if [ "$uses" -eq 0 ]; then
    echo "  UNUSED: $sym  ($file:$line)"
  fi
done
echo ""

echo "=== Scan complete ==="
