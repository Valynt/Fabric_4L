#!/usr/bin/env bash
# Validate that production and staging kustomize overlays do not contain
# mutable image tags (latest, main, semver, branch names). All production-like
# overlays must use immutable digests.
#
# Usage:
#   bash scripts/ci/validate-k8s-image-tags.sh [overlay-path]
#
# Defaults:
#   overlay-path: k8s/envs/prod
#
# Exit codes:
#   0  No mutable tags found
#   1  Mutable tags detected
#
set -euo pipefail

OVERLAY="${1:-k8s/envs/prod}"
TMPDIR="$(mktemp -d)"
trap 'rm -rf "${TMPDIR}"' EXIT

echo "==> Validating image tags in overlay: ${OVERLAY}"

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

# Patterns for mutable tags that are forbidden in production-like overlays:
# - :latest
# - :main, :master, :develop, :dev, :staging, :production, :stable, :edge, :nightly
# - :v1.1.0, :v2.0.0 (semver tags)
# - :sha-<commit> is OK (immutable)
# - @sha256:... is OK (immutable digest)

echo "==> Checking for mutable image tags ..."

# Extract container images from pod specs in the rendered manifest.
# Intentionally narrow: Deployment/StatefulSet/DaemonSet/CronJob/Job containers
# and initContainers. This avoids Kyverno policy patterns and other non-image
# fields that happen to be named "image".
IMAGES="${TMPDIR}/images.txt"
yq eval '
  (.spec.template.spec.containers // [])[].image,
  (.spec.template.spec.initContainers // [])[].image,
  (.spec.jobTemplate.spec.template.spec.containers // [])[].image,
  (.spec.jobTemplate.spec.template.spec.initContainers // [])[].image
' "${MANIFEST}" | sort -u > "${IMAGES}" || true

while IFS= read -r img; do
  [[ -z "${img}" ]] && continue

  # Skip digest-pinned images (OK)
  if [[ "${img}" =~ @sha256:[a-f0-9]{64}$ ]]; then
    continue
  fi

  # Extract tag
  tag=""
  if [[ "${img}" =~ :([^:]+)$ ]]; then
    tag="${BASH_REMATCH[1]}"
  fi

  [[ -z "${tag}" ]] && continue

  # Check for forbidden mutable tags
  if [[ "${tag}" == "latest" ]] || \
     [[ "${tag}" =~ ^(main|master|develop|dev|staging|production|stable|edge|nightly)$ ]] || \
     [[ "${tag}" =~ ^v[0-9]+\.[0-9]+\.[0-9]+ ]]; then
    echo "::error::Mutable image tag detected: ${img}"
    ERRORS=$((ERRORS + 1))
  fi
done < "${IMAGES}"

# Also check the kustomization.yaml directly for newTag values that are mutable
KUSTOMIZATION="${OVERLAY}/kustomization.yaml"
if [[ -f "${KUSTOMIZATION}" ]]; then
  echo "==> Checking kustomization.yaml for mutable newTag values ..."
  if grep -E "newTag: (latest|main|master|develop|dev|staging|production|stable|edge|nightly|v[0-9]+\.[0-9]+\.[0-9]+)" "${KUSTOMIZATION}" >/dev/null 2>&1; then
    echo "::error::Mutable newTag found in ${KUSTOMIZATION}:"
    grep -E "newTag: (latest|main|master|develop|dev|staging|production|stable|edge|nightly|v[0-9]+\.[0-9]+\.[0-9]+)" "${KUSTOMIZATION}"
    ERRORS=$((ERRORS + 1))
  fi
fi

echo ""
if [[ ${ERRORS} -eq 0 ]]; then
  echo "==> PASS: No mutable image tags in ${OVERLAY}"
  exit 0
else
  echo "==> FAIL: ${ERRORS} mutable image tag(s) detected"
  echo "    Production-like overlays must use immutable digests (@sha256:...)"
  exit 1
fi
