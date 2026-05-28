#!/usr/bin/env bash
# Validate that rendered staging manifests do not contain hardcoded production
# namespace service DNS references. All inter-service URLs should use unqualified
# service names so they resolve correctly in the staging namespace.
#
# Usage:
#   bash scripts/ci/validate-staging-dns.sh [overlay-path]
#
# Defaults:
#   overlay-path: k8s/envs/staging
#
# Exit codes:
#   0  No hardcoded production DNS references found in staging output
#   1  Hardcoded production DNS references detected
#
set -euo pipefail

OVERLAY="${1:-k8s/envs/staging}"
TMPDIR="$(mktemp -d)"
trap 'rm -rf "${TMPDIR}"' EXIT

echo "==> Validating staging DNS references for overlay: ${OVERLAY}"

if ! command -v kustomize >/dev/null 2>&1; then
  echo "::error::kustomize is required" >&2
  exit 1
fi

if [[ ! -f "${OVERLAY}/kustomization.yaml" ]]; then
  echo "::error::Overlay not found: ${OVERLAY}/kustomization.yaml" >&2
  exit 1
fi

# Render staging manifests
MANIFEST="${TMPDIR}/staging-rendered.yaml"
kustomize build --load-restrictor=LoadRestrictionsNone "${OVERLAY}" > "${MANIFEST}"

ERRORS=0

# -----------------------------------------------------------------------------
# Check 1: No hardcoded production namespace service DNS
# -----------------------------------------------------------------------------
echo "==> Checking for hardcoded production namespace service DNS ..."

# Patterns that indicate cross-namespace hardcoding:
# - value-fabric.svc.cluster.local
# - value-fabric.svc (without .cluster.local)
# We allow external domains like value-fabric.io, value-fabric.local, etc.

HITS="${TMPDIR}/dns-hits.txt"
grep -nE "value-fabric\.svc\.cluster\.local|value-fabric\.svc[^a-zA-Z]" "${MANIFEST}" | \
  grep -vE "# .*value-fabric|value-fabric\.io|value-fabric\.local|docs\.value-fabric|runbooks\.value-fabric" > "${HITS}" || true

if [[ -s "${HITS}" ]]; then
  echo "::error::Found hardcoded production namespace DNS in staging rendered output:"
  cat "${HITS}"
  ERRORS=$((ERRORS + 1))
fi

# -----------------------------------------------------------------------------
# Check 2: No hardcoded production namespace in env values that look like URLs
# -----------------------------------------------------------------------------
echo "==> Checking for namespace-qualified service URLs in env values ..."

URL_HITS="${TMPDIR}/url-hits.txt"
grep -nE "https?://[^/]*\.value-fabric\." "${MANIFEST}" | \
  grep -vE "value-fabric\.io|value-fabric\.local|value-fabric\.example\.com" > "${URL_HITS}" || true

if [[ -s "${URL_HITS}" ]]; then
  echo "::error::Found namespace-qualified URLs in staging rendered output:"
  cat "${URL_HITS}"
  ERRORS=$((ERRORS + 1))
fi

# -----------------------------------------------------------------------------
# Summary
# -----------------------------------------------------------------------------
echo ""
if [[ ${ERRORS} -eq 0 ]]; then
  echo "==> PASS: No hardcoded production namespace DNS references in staging output"
  exit 0
else
  echo "==> FAIL: ${ERRORS} hardcoded DNS error(s) detected in staging output"
  echo "    All inter-service URLs should use unqualified service names (e.g., 'postgres'"
  echo "    instead of 'postgres.value-fabric.svc.cluster.local') so they resolve"
  echo "    correctly within the staging namespace."
  exit 1
fi
