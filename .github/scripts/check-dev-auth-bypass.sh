#!/bin/bash
# Check for dev auth bypass flags in production docker-compose files
# This script prevents accidental deployment with dev auth bypass enabled

set -e

# Bypass flags that must never appear in production compose files
BYPASS_FLAGS=("DEV_AUTH_BYPASS" "ALLOW_DEV_AUTH_BYPASS" "AUTH_BYPASS_ENABLED" "ALLOW_INSECURE_DEV_AUTH_BYPASS")

# Production-like compose files to check
# Note: Testing compose files (release-smoke, backend-integrated, live, playwright-live) are excluded
# as they legitimately use dev auth bypass for testing purposes
PROD_COMPOSE_FILES=(
  "infra/compose/docker-compose.prod.yml"
  "docker-compose.staging.yml"
  "docker-compose.preprod.yml"
  "docker-compose.full.yml"
)

# Check if we're in the repo root
if [ ! -f "docker-compose.dev.yml" ]; then
  echo "ERROR: This script must be run from the repository root"
  exit 1
fi

echo "🔍 Scanning for dev auth bypass flags in production compose files..."

errors_found=0

for compose_file in "${PROD_COMPOSE_FILES[@]}"; do
  if [ -f "$compose_file" ]; then
    for flag in "${BYPASS_FLAGS[@]}"; do
      if grep -q "$flag" "$compose_file"; then
        echo "❌ ERROR: Found $flag in $compose_file"
        echo "   Dev auth bypass flags are not allowed in production compose files"
        echo "   Line(s):"
        grep -n "$flag" "$compose_file" | sed 's/^/     /'
        errors_found=1
      fi
    done
  fi
done

if [ $errors_found -ne 0 ]; then
  echo ""
  echo "❌ Dev auth bypass flags found in production compose files"
  echo "   Remove all bypass flags from production compose files before deployment"
  exit 1
fi

echo "✅ No dev auth bypass flags found in production compose files"
exit 0
