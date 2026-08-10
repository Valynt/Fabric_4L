#!/usr/bin/env bash
# Validate that Redis deployments require authentication in production-like
# overlays and that health checks use the authenticated connection.
#
# Usage:
#   bash scripts/ci/validate-redis-auth.sh [overlay-path]
#
# Defaults:
#   overlay-path: k8s/envs/prod
#
# Exit codes:
#   0  Redis auth is properly configured
#   1  Validation failed
#
set -euo pipefail

OVERLAY="${1:-k8s/envs/prod}"
TMPDIR="$(mktemp -d)"
trap 'rm -rf "${TMPDIR}"' EXIT

echo "==> Validating Redis auth configuration for overlay: ${OVERLAY}"

if ! command -v kustomize >/dev/null 2>&1; then
  echo "::error::kustomize is required" >&2
  exit 1
fi

if [[ ! -f "${OVERLAY}/kustomization.yaml" ]]; then
  echo "::error::Overlay not found: ${OVERLAY}/kustomization.yaml" >&2
  exit 1
fi

# Render manifests
MANIFEST="${TMPDIR}/rendered.yaml"
kustomize build --load-restrictor=LoadRestrictionsNone "${OVERLAY}" > "${MANIFEST}"

ERRORS=0

# -----------------------------------------------------------------------------
# Check 1: Redis Deployment has --requirepass in command
# -----------------------------------------------------------------------------
echo "==> Checking Redis deployment requires password ..."

REDIS_DEPLOY="${TMPDIR}/redis-deployment.yaml"
yq eval 'select(.kind == "Deployment" and .metadata.name == "redis")' "${MANIFEST}" > "${REDIS_DEPLOY}"

if [[ ! -s "${REDIS_DEPLOY}" ]]; then
  echo "::error::Redis Deployment not found in rendered output"
  ERRORS=$((ERRORS + 1))
else
  if ! yq eval '.spec.template.spec.containers[0].command[]' "${REDIS_DEPLOY}" | grep -q "requirepass"; then
    echo "::error::Redis deployment does not have '--requirepass' in command"
    ERRORS=$((ERRORS + 1))
  fi

  if ! yq eval '.spec.template.spec.containers[0].command[]' "${REDIS_DEPLOY}" | grep -q "REDIS_PASSWORD"; then
    echo "::error::Redis deployment command does not reference REDIS_PASSWORD"
    ERRORS=$((ERRORS + 1))
  fi
fi

# -----------------------------------------------------------------------------
# Check 2: Redis Deployment references redis-secret
# -----------------------------------------------------------------------------
echo "==> Checking Redis deployment references redis-secret ..."

if [[ -s "${REDIS_DEPLOY}" ]]; then
  if ! yq eval '.spec.template.spec.containers[0].envFrom[]' "${REDIS_DEPLOY}" | grep -q "redis-secret"; then
    echo "::error::Redis deployment does not mount 'redis-secret' via envFrom"
    ERRORS=$((ERRORS + 1))
  fi
fi

# -----------------------------------------------------------------------------
# Check 3: Redis health probes use authentication
# -----------------------------------------------------------------------------
echo "==> Checking Redis health probes use authentication ..."

if [[ -s "${REDIS_DEPLOY}" ]]; then
  LIVENESS="${TMPDIR}/liveness.yaml"
  yq eval '.spec.template.spec.containers[0].livenessProbe' "${REDIS_DEPLOY}" > "${LIVENESS}"
  
  if ! grep -q "REDIS_PASSWORD" "${LIVENESS}"; then
    echo "::error::Redis livenessProbe does not use REDIS_PASSWORD authentication"
    ERRORS=$((ERRORS + 1))
  fi

  READINESS="${TMPDIR}/readiness.yaml"
  yq eval '.spec.template.spec.containers[0].readinessProbe' "${REDIS_DEPLOY}" > "${READINESS}"
  
  if ! grep -q "REDIS_PASSWORD" "${READINESS}"; then
    echo "::error::Redis readinessProbe does not use REDIS_PASSWORD authentication"
    ERRORS=$((ERRORS + 1))
  fi
fi

# -----------------------------------------------------------------------------
# Check 4: ExternalSecret redis-credentials exists in overlay
# -----------------------------------------------------------------------------
echo "==> Checking ExternalSecret redis-credentials exists ..."

if ! yq eval 'select(.kind == "ExternalSecret" and .metadata.name == "redis-credentials")' "${MANIFEST}" | grep -q "redis-credentials"; then
  echo "::error::ExternalSecret 'redis-credentials' not found in rendered output"
  ERRORS=$((ERRORS + 1))
fi

# -----------------------------------------------------------------------------
# Summary
# -----------------------------------------------------------------------------
echo ""
if [[ ${ERRORS} -eq 0 ]]; then
  echo "==> PASS: Redis auth is properly configured in ${OVERLAY}"
  exit 0
else
  echo "==> FAIL: ${ERRORS} Redis auth error(s) detected"
  exit 1
fi
