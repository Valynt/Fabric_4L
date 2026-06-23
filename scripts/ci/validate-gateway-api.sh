#!/usr/bin/env bash
# Validate that the production overlay includes Gateway API routing resources
# and that TLS certificate references are correctly configured.
#
# Usage:
#   bash scripts/ci/validate-gateway-api.sh [overlay-path]
#
# Defaults:
#   overlay-path: k8s/deployments/prod-gateway-api
#
# Exit codes:
#   0  Gateway API resources are properly integrated
#   1  Validation failed
#
set -euo pipefail

OVERLAY="${1:-k8s/deployments/prod-gateway-api}"
TMPDIR="$(mktemp -d)"
trap 'rm -rf "${TMPDIR}"' EXIT

echo "==> Validating Gateway API integration for overlay: ${OVERLAY}"

if ! command -v kustomize >/dev/null 2>&1; then
  echo "::error::kustomize is required" >&2
  exit 1
fi

if [[ ! -f "${OVERLAY}/kustomization.yaml" ]]; then
  echo "::error::Overlay not found: ${OVERLAY}/kustomization.yaml" >&2
  exit 1
fi

MANIFEST="${TMPDIR}/rendered.yaml"
kustomize build --load-restrictor=LoadRestrictionsNone "${OVERLAY}" > "${MANIFEST}"

ERRORS=0

# -----------------------------------------------------------------------------
# Check 1: Gateway resource exists
# -----------------------------------------------------------------------------
echo "==> Checking Gateway resource exists ..."

if ! yq eval 'select(.kind == "Gateway")' "${MANIFEST}" | grep -q "value-fabric-gateway"; then
  echo "::error::Gateway 'value-fabric-gateway' not found in rendered output"
  ERRORS=$((ERRORS + 1))
fi

# -----------------------------------------------------------------------------
# Check 2: HTTPRoute resources exist
# -----------------------------------------------------------------------------
echo "==> Checking HTTPRoute resources exist ..."

if ! yq eval 'select(.kind == "HTTPRoute")' "${MANIFEST}" | grep -q "frontend"; then
  echo "::error::HTTPRoute 'frontend' not found in rendered output"
  ERRORS=$((ERRORS + 1))
fi

if ! yq eval 'select(.kind == "HTTPRoute")' "${MANIFEST}" | grep -q "layer-apis"; then
  echo "::error::HTTPRoute 'layer-apis' not found in rendered output"
  ERRORS=$((ERRORS + 1))
fi

# -----------------------------------------------------------------------------
# Check 3: Certificate resources exist with valid issuerRef
# -----------------------------------------------------------------------------
echo "==> Checking Certificate resources exist ..."

CERTS="${TMPDIR}/certs.yaml"
yq eval 'select(.kind == "Certificate")' "${MANIFEST}" > "${CERTS}"

if ! grep -q "frontend-tls" "${CERTS}"; then
  echo "::error::Certificate 'frontend-tls' not found in rendered output"
  ERRORS=$((ERRORS + 1))
fi

if ! grep -q "layer-apis-tls" "${CERTS}"; then
  echo "::error::Certificate 'layer-apis-tls' not found in rendered output"
  ERRORS=$((ERRORS + 1))
fi

if ! grep -q "letsencrypt-prod" "${CERTS}"; then
  echo "::error::Certificate issuerRef 'letsencrypt-prod' not found"
  ERRORS=$((ERRORS + 1))
fi

# -----------------------------------------------------------------------------
# Check 4: Hostnames are replaced (no __HOST__ placeholders remain)
# -----------------------------------------------------------------------------
echo "==> Checking hostnames are properly replaced ..."

if grep -q "__HOST__" "${MANIFEST}"; then
  echo "::error::Unresolved __HOST__ placeholder found in rendered output"
  ERRORS=$((ERRORS + 1))
fi

if grep -q "__API_HOST__" "${MANIFEST}"; then
  echo "::error::Unresolved __API_HOST__ placeholder found in rendered output"
  ERRORS=$((ERRORS + 1))
fi

# -----------------------------------------------------------------------------
# Check 5: No conflicting ingress resources (nginx/istio) in same overlay
# -----------------------------------------------------------------------------
echo "==> Checking for conflicting ingress resources ..."

if yq eval 'select(.kind == "Ingress")' "${MANIFEST}" | grep -q "apiVersion"; then
  echo "::warning::Ingress resources found alongside Gateway API (potential conflict)"
fi

echo ""
if [[ ${ERRORS} -eq 0 ]]; then
  echo "==> PASS: Gateway API resources are properly integrated in ${OVERLAY}"
  exit 0
else
  echo "==> FAIL: ${ERRORS} Gateway API integration error(s) detected"
  exit 1
fi
