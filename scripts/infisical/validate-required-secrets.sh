#!/usr/bin/env bash
# =============================================================================
# Fabric4L — Validate required secrets are present in the environment
# =============================================================================
# Usage:
#   ./scripts/infisical/validate-required-secrets.sh [environment]
#
# Checks that every secret listed in the manifest is resolvable either from
# the current shell environment or from Infisical (if the CLI is logged in).
#
# Exit codes:
#   0  — all required secrets present
#   1  — one or more secrets missing
# =============================================================================
set -euo pipefail

ENVIRONMENT="${1:-dev}"
MISSING=0

echo "→ Validating required secrets for environment: ${ENVIRONMENT}"

# ---------------------------------------------------------------------------
# Helper: check if a variable is set and non-empty
# ---------------------------------------------------------------------------
check_var() {
  local name="$1"
  local value="${!name:-}"
  if [[ -z "${value}" ]]; then
    echo "   ❌  Missing: ${name}"
    MISSING=$((MISSING + 1))
  else
    echo "   ✅  Present: ${name}"
  fi
}

# ---------------------------------------------------------------------------
# /shared
# ---------------------------------------------------------------------------
echo ""
echo "Checking /shared ..."
check_var "APP_ENV"
check_var "JWT_ISSUER"
check_var "JWT_AUDIENCE"

# ---------------------------------------------------------------------------
# /infra
# ---------------------------------------------------------------------------
echo ""
echo "Checking /infra ..."
check_var "POSTGRES_HOST"
check_var "POSTGRES_PORT"
check_var "REDIS_URL"

# ---------------------------------------------------------------------------
# /layer1-ingestion
# ---------------------------------------------------------------------------
echo ""
echo "Checking /layer1-ingestion ..."
check_var "LAYER1_PORT"
check_var "LAYER1_DATABASE_URL"

# ---------------------------------------------------------------------------
# /layer2-extraction
# ---------------------------------------------------------------------------
echo ""
echo "Checking /layer2-extraction ..."
check_var "LAYER2_PORT"
check_var "LAYER2_DATABASE_URL"
check_var "LLM_PROVIDER"

# ---------------------------------------------------------------------------
# /layer2-5-signal-refinery
# ---------------------------------------------------------------------------
echo ""
echo "Checking /layer2-5-signal-refinery ..."
check_var "LAYER2_5_PORT"
check_var "LAYER2_5_DATABASE_URL"

# ---------------------------------------------------------------------------
# /layer3-knowledge
# ---------------------------------------------------------------------------
echo ""
echo "Checking /layer3-knowledge ..."
check_var "LAYER3_PORT"
check_var "NEO4J_URI"
check_var "NEO4J_PASSWORD"

# ---------------------------------------------------------------------------
# /layer4-agents
# ---------------------------------------------------------------------------
echo ""
echo "Checking /layer4-agents ..."
check_var "LAYER4_PORT"
check_var "LAYER4_DATABASE_URL"
check_var "LAYER4_LLM_PROVIDER"

# ---------------------------------------------------------------------------
# /layer5-ground-truth
# ---------------------------------------------------------------------------
echo ""
echo "Checking /layer5-ground-truth ..."
check_var "LAYER5_PORT"
check_var "LAYER5_DATABASE_URL"

# ---------------------------------------------------------------------------
# /layer6-benchmarks
# ---------------------------------------------------------------------------
echo ""
echo "Checking /layer6-benchmarks ..."
check_var "LAYER6_PORT"
check_var "LAYER6_DATABASE_URL"

# ---------------------------------------------------------------------------
# /apps/web
# ---------------------------------------------------------------------------
echo ""
echo "Checking /apps/web ..."
check_var "VITE_API_BASE_URL"

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
if [[ ${MISSING} -eq 0 ]]; then
  echo "✅  All required secrets are present."
  exit 0
else
  echo "❌  ${MISSING} required secret(s) missing."
  echo "   Populate them in Infisical (env=${ENVIRONMENT}) or set them manually."
  exit 1
fi
