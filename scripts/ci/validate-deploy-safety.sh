#!/usr/bin/env bash
# Validate that the deploy workflow contains explicit safety checks and cannot
# proceed with a placeholder kubeconfig.
#
# Usage:
#   bash scripts/ci/validate-deploy-safety.sh
#
# Exit codes:
#   0  Deploy workflow has safety guardrails
#   1  Validation failed
#
set -euo pipefail

DEPLOY_WORKFLOW=".github/workflows/deploy.yml"

echo "==> Validating deploy safety guardrails in ${DEPLOY_WORKFLOW}"

if [[ ! -f "${DEPLOY_WORKFLOW}" ]]; then
  echo "::error::Deploy workflow not found: ${DEPLOY_WORKFLOW}"
  exit 1
fi

ERRORS=0

# -----------------------------------------------------------------------------
# Check 1: Deploy workflow kubeconfig step exits with error (fail-closed)
# -----------------------------------------------------------------------------
echo "==> Checking deploy kubeconfig step fails closed ..."

if ! grep -A 5 "echo \"::error::Kubeconfig is not configured\"" "${DEPLOY_WORKFLOW}" | grep -q "exit 1"; then
  echo "::error::Deploy workflow kubeconfig step does not exit with error (fail-closed)"
  ERRORS=$((ERRORS + 1))
fi

# -----------------------------------------------------------------------------
# Check 2: Rollback job kubeconfig step also exits with error
# -----------------------------------------------------------------------------
echo "==> Checking rollback kubeconfig step fails closed ..."

ROLLBACK_KUBECONFIG=$(grep -n "Configure kubeconfig" "${DEPLOY_WORKFLOW}" | tail -1 | cut -d: -f1)
if [[ -n "${ROLLBACK_KUBECONFIG}" ]]; then
  # Check the second occurrence (rollback job) has exit 1
  if ! sed -n "${ROLLBACK_KUBECONFIG},+20p" "${DEPLOY_WORKFLOW}" | grep -q "exit 1"; then
    echo "::error::Rollback workflow kubeconfig step does not exit with error (fail-closed)"
    ERRORS=$((ERRORS + 1))
  fi
fi

# -----------------------------------------------------------------------------
# Check 3: Deploy workflow has cluster context confirmation
# -----------------------------------------------------------------------------
echo "==> Checking deploy workflow has cluster context confirmation ..."

if ! grep -q "Confirm cluster context and namespace" "${DEPLOY_WORKFLOW}"; then
  echo "::error::Deploy workflow missing 'Confirm cluster context and namespace' step"
  ERRORS=$((ERRORS + 1))
fi

# -----------------------------------------------------------------------------
# Check 4: Deploy workflow rejects mutable image refs in preflight
# -----------------------------------------------------------------------------
echo "==> Checking deploy workflow rejects mutable image refs ..."

if ! grep -q "Mutable image reference is forbidden" "${DEPLOY_WORKFLOW}"; then
  echo "::error::Deploy workflow does not reject mutable image references"
  ERRORS=$((ERRORS + 1))
fi

# -----------------------------------------------------------------------------
# Check 5: Deploy workflow has rollback job
# -----------------------------------------------------------------------------
echo "==> Checking deploy workflow has rollback job ..."

if ! grep -q "rollback-on-failure" "${DEPLOY_WORKFLOW}"; then
  echo "::error::Deploy workflow missing rollback job"
  ERRORS=$((ERRORS + 1))
fi

# -----------------------------------------------------------------------------
# Summary
# -----------------------------------------------------------------------------
echo ""
if [[ ${ERRORS} -eq 0 ]]; then
  echo "==> PASS: Deploy workflow has required safety guardrails"
  exit 0
else
  echo "==> FAIL: ${ERRORS} deploy safety error(s) detected"
  exit 1
fi
