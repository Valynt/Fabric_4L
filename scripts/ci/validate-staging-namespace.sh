#!/usr/bin/env bash
# Validate that staging kustomize overlays render into exactly one canonical
# namespace and that ExternalSecrets required by staging workloads render
# into the same namespace.
#
# Usage:
#   bash scripts/ci/validate-staging-namespace.sh [overlay-path]
#
# Defaults:
#   overlay-path: k8s/envs/staging
#
# Exit codes:
#   0  Staging renders consistently to value-fabric-staging
#   1  Validation failed (namespace drift detected)
#
set -euo pipefail

OVERLAY="${1:-k8s/envs/staging}"
CANONICAL_NS="value-fabric-staging"
BAD_NS_1="value-fabric"
BAD_NS_2="fabric-4l-staging"
TMPDIR="$(mktemp -d)"
trap 'rm -rf "${TMPDIR}"' EXIT

echo "==> Validating staging namespace consistency for overlay: ${OVERLAY}"

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
# Check 1: No resources render into the old / conflicting namespaces
# -----------------------------------------------------------------------------
echo "==> Checking for forbidden namespaces in rendered output ..."

if grep -E "^  namespace: ${BAD_NS_1}$" "${MANIFEST}" >/dev/null 2>&1; then
  echo "::error::Found resources rendering into forbidden namespace '${BAD_NS_1}'"
  grep -E "^  namespace: ${BAD_NS_1}$" "${MANIFEST}" | head -n 5
  ERRORS=$((ERRORS + 1))
fi

if grep -E "^  namespace: ${BAD_NS_2}$" "${MANIFEST}" >/dev/null 2>&1; then
  echo "::error::Found resources rendering into forbidden namespace '${BAD_NS_2}'"
  grep -E "^  namespace: ${BAD_NS_2}$" "${MANIFEST}" | head -n 5
  ERRORS=$((ERRORS + 1))
fi

# -----------------------------------------------------------------------------
# Check 2: All namespaced resources render into the canonical namespace
# -----------------------------------------------------------------------------
echo "==> Checking that all namespaced resources use canonical namespace ..."

# Extract all namespace declarations from namespaced resources
# (skip Namespace resources themselves and un-namespaced resources)
ACTUAL_NAMESPACES="${TMPDIR}/actual-namespaces.txt"
yq eval '
  select(.kind != "Namespace" and .metadata.namespace != null) |
  .metadata.namespace
' "${MANIFEST}" | sed '/^---$/d' | sort -u > "${ACTUAL_NAMESPACES}"

# Allow only the canonical staging namespace, plus shared infrastructure
# namespaces that are explicitly expected (e.g., cert-manager, monitoring).
# Any production namespace references are failures.
while IFS= read -r ns; do
  [[ -z "${ns}" ]] && continue
  if [[ "${ns}" != "${CANONICAL_NS}" ]]; then
    # Check if this is an allowlisted shared namespace
    if [[ "${ns}" == "cert-manager" || "${ns}" == "monitoring" || "${ns}" == "external-secrets" || "${ns}" == "istio-system" ]]; then
      echo "   Allowlisted shared namespace: ${ns}"
      continue
    fi
    echo "::error::Unexpected namespace in staging output: ${ns}"
    # Show which resources use this namespace
    yq eval "select(.metadata.namespace == \"${ns}\") | \"\(.kind)/\(.metadata.name) -> ${ns}\"" "${MANIFEST}" | head -n 10
    ERRORS=$((ERRORS + 1))
  fi
done < "${ACTUAL_NAMESPACES}"

# -----------------------------------------------------------------------------
# Check 3: ExternalSecrets render into the canonical namespace
# -----------------------------------------------------------------------------
echo "==> Checking ExternalSecret namespace consistency ..."

EXTERNALSECRET_NAMESPACES="${TMPDIR}/externalsecret-namespaces.txt"
yq eval '
  select(.kind == "ExternalSecret") |
  .metadata.namespace
' "${MANIFEST}" | sed '/^---$/d' | sort -u > "${EXTERNALSECRET_NAMESPACES}"

while IFS= read -r ns; do
  [[ -z "${ns}" ]] && continue
  if [[ "${ns}" != "${CANONICAL_NS}" ]]; then
    echo "::error::ExternalSecret renders into wrong namespace: ${ns} (expected ${CANONICAL_NS})"
    ERRORS=$((ERRORS + 1))
  fi
done < "${EXTERNALSECRET_NAMESPACES}"

# -----------------------------------------------------------------------------
# Check 4: Workloads (Deployments, StatefulSets, DaemonSets, Jobs, CronJobs)
# do not reference secrets in a different namespace
# -----------------------------------------------------------------------------
echo "==> Checking workload/secret namespace alignment ..."

# Extract all unique (kind, name, namespace) tuples for workloads
WORKLOAD_NS="${TMPDIR}/workload-namespaces.txt"
yq eval '
  select((.kind == "Deployment" or .kind == "StatefulSet" or .kind == "DaemonSet" or .kind == "Job" or .kind == "CronJob") and .metadata.namespace != null) |
  "\(.kind)/\(.metadata.name): \(.metadata.namespace)"
' "${MANIFEST}" | sed '/^---$/d' | sort -u > "${WORKLOAD_NS}"

# Check that all workloads are in the canonical namespace
while IFS= read -r line; do
  [[ -z "${line}" ]] && continue
  workload_ns="$(echo "${line}" | sed 's/.*: //')"
  [[ -z "${workload_ns}" ]] && continue
  if [[ "${workload_ns}" != "${CANONICAL_NS}" ]]; then
    echo "::error::Workload in unexpected namespace: ${line}"
    ERRORS=$((ERRORS + 1))
  fi
done < "${WORKLOAD_NS}"

# -----------------------------------------------------------------------------
# Summary
# -----------------------------------------------------------------------------
echo ""
if [[ ${ERRORS} -eq 0 ]]; then
  echo "==> PASS: Staging renders consistently to '${CANONICAL_NS}'"
  echo "    Namespaced resources: $(wc -l < "${ACTUAL_NAMESPACES}" | tr -d ' ') unique namespaces"
  echo "    ExternalSecrets:      $(wc -l < "${EXTERNALSECRET_NAMESPACES}" | tr -d ' ') unique namespaces"
  echo "    Workloads:            $(wc -l < "${WORKLOAD_NS}" | tr -d ' ') items"
  exit 0
else
  echo "==> FAIL: ${ERRORS} namespace consistency error(s) detected in staging output"
  echo "    Review the errors above and ensure all patches target the canonical namespace."
  exit 1
fi
