#!/usr/bin/env bash
# Validate that the deploy workflow contains explicit safety checks, real SBOM
# verification, environment health probes, and cloud-provider kubeconfig setup.
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
# Check 1: Workflow does not contain known deployment placeholders.
# -----------------------------------------------------------------------------
echo "==> Checking deploy workflow has no forbidden placeholder strings ..."

for forbidden in \
  "SBOM verification placeholder" \
  "Environment health check placeholder" \
  "Kubeconfig is not configured"; do
  if grep -qF "${forbidden}" "${DEPLOY_WORKFLOW}"; then
    echo "::error::Deploy workflow still contains forbidden placeholder string: ${forbidden}"
    ERRORS=$((ERRORS + 1))
  fi
done

# -----------------------------------------------------------------------------
# Check 2: SBOM verification retrieves artifacts and validates image digests.
# -----------------------------------------------------------------------------
echo "==> Checking SBOM artifact retrieval and digest verification ..."

for required in \
  "Download SBOM and signing artifacts" \
  "Verify SBOMs against deploy image digests" \
  "deployed_digest" \
  "cosign verify-attestation" \
  "cosign verify-blob"; do
  if ! grep -qF "${required}" "${DEPLOY_WORKFLOW}"; then
    echo "::error::Deploy workflow missing SBOM verification control: ${required}"
    ERRORS=$((ERRORS + 1))
  fi
done

# Accept both the plain version tag and the SHA-pinned form (with a version
# comment) for the artifact download action. v4 is the legacy Node 20 major;
# v7 is the Node 24-compatible major used after the Node 20 migration.
if ! grep -qE "actions/download-artifact@(v[47]|[0-9a-f]{40}\s*#\s*v[47])" "${DEPLOY_WORKFLOW}"; then
  echo "::error::Deploy workflow missing SBOM verification control: actions/download-artifact@v4 or v7"
  ERRORS=$((ERRORS + 1))
fi

# -----------------------------------------------------------------------------
# Check 3: Environment health checks call API and service readiness endpoints.
# -----------------------------------------------------------------------------
echo "==> Checking deploy workflow has environment-specific health checks ..."

for required in \
  "Check environment health" \
  "DEV_API_BASE_URL" \
  "STAGING_API_BASE_URL" \
  "PRODUCTION_API_BASE_URL" \
  "/health/live" \
  "/ready" \
  "/api/v1/ingestion/health" \
  "/layer4/health" \
  "curl --fail"; do
  if ! grep -qF "${required}" "${DEPLOY_WORKFLOW}"; then
    echo "::error::Deploy workflow missing health-check control: ${required}"
    ERRORS=$((ERRORS + 1))
  fi
done

# -----------------------------------------------------------------------------
# Check 4: Deploy and rollback configure kubeconfig through AWS/EKS OIDC.
# -----------------------------------------------------------------------------
echo "==> Checking cloud-provider kubeconfig setup ..."

if [[ $(grep -c "Configure AWS credentials (OIDC)" "${DEPLOY_WORKFLOW}") -lt 2 ]]; then
  echo "::error::Deploy workflow must configure AWS OIDC credentials for deploy and rollback"
  ERRORS=$((ERRORS + 1))
fi

if [[ $(grep -c "Configure kubeconfig (EKS)" "${DEPLOY_WORKFLOW}") -lt 2 ]]; then
  echo "::error::Deploy workflow must configure EKS kubeconfig for deploy and rollback"
  ERRORS=$((ERRORS + 1))
fi

for required in \
  "aws eks update-kubeconfig" \
  "AWS_DEPLOY_ROLE_ARN secret is required" \
  "kubectl current-context is empty" \
  "kubectl cluster-info"; do
  if ! grep -qF "${required}" "${DEPLOY_WORKFLOW}"; then
    echo "::error::Deploy workflow missing kubeconfig fail-closed control: ${required}"
    ERRORS=$((ERRORS + 1))
  fi
done

# -----------------------------------------------------------------------------
# Check 5: Deploy workflow has cluster context confirmation.
# -----------------------------------------------------------------------------
echo "==> Checking deploy workflow has cluster context confirmation ..."

if ! grep -q "Confirm cluster context and namespace" "${DEPLOY_WORKFLOW}"; then
  echo "::error::Deploy workflow missing 'Confirm cluster context and namespace' step"
  ERRORS=$((ERRORS + 1))
fi

# -----------------------------------------------------------------------------
# Check 6: Deploy workflow rejects mutable image refs in preflight.
# -----------------------------------------------------------------------------
echo "==> Checking deploy workflow rejects mutable image refs ..."

if ! grep -q "Mutable image reference is forbidden" "${DEPLOY_WORKFLOW}"; then
  echo "::error::Deploy workflow does not reject mutable image references"
  ERRORS=$((ERRORS + 1))
fi

# -----------------------------------------------------------------------------
# Check 7: Deploy workflow has rollback job.
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
