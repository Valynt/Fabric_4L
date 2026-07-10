#!/usr/bin/env bash
# P1-006: Verify demo customer data is not in the production bundle.
set -euo pipefail

echo "Checking for demo data leakage in production build..."

pnpm --dir apps/web run build

if rg --fixed-strings "Medtronic" apps/web/dist/; then
    echo "ERROR: Demo customer data (Medtronic) found in production bundle!"
    exit 1
fi

echo "OK: No demo customer data in production bundle"
