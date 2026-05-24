#!/usr/bin/env bash
# =============================================================================
# Fabric4L — Export Infisical dev secrets for Docker Compose
# =============================================================================
# Usage:
#   ./scripts/infisical/export-dev-env.sh
#
# Generates .env.generated from Infisical dev environment. All service paths
# are included so that docker-compose.dev.yml (or compose.live.yml) can read
# every variable it needs from a single env file.
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
OUTPUT_FILE="${ROOT_DIR}/.env.generated"

echo "→ Exporting Infisical dev secrets to ${OUTPUT_FILE} ..."

infisical export \
  --env=dev \
  --path=/shared \
  --path=/infra \
  --path=/layer1-ingestion \
  --path=/layer2-extraction \
  --path=/layer2-5-signal-refinery \
  --path=/layer3-knowledge \
  --path=/layer4-agents \
  --path=/layer5-ground-truth \
  --path=/layer6-benchmarks \
  --path=/apps/web \
  --format=dotenv \
  --output-file="${OUTPUT_FILE}"

echo "✅  ${OUTPUT_FILE} generated."
echo "   Run: docker compose --env-file .env.generated up"
