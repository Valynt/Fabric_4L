#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: prepare_kustomize_deploy.sh <overlay> <rendered-output>

Required environment variables:
  REGISTRY                  Container registry, for example ghcr.io.
  IMAGE_TAG                 Mutable tag to resolve to immutable image digests.
  GITHUB_REPOSITORY_OWNER   Registry owner or organization.

Optional environment variables:
  KUSTOMIZE_ROOT            Root containing env overlays; defaults to k8s/envs.
  DEPLOY_DIGESTS_FILE       File that receives layer=digest pairs.
USAGE
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

OVERLAY="${1:?overlay is required}"
RENDERED_OUTPUT="${2:?rendered manifest output path is required}"
REGISTRY="${REGISTRY:?REGISTRY is required}"
IMAGE_TAG="${IMAGE_TAG:?IMAGE_TAG is required}"
OWNER="${GITHUB_REPOSITORY_OWNER:?GITHUB_REPOSITORY_OWNER is required}"
KUSTOMIZE_ROOT="${KUSTOMIZE_ROOT:-k8s/envs}"
DEPLOY_DIGESTS_FILE="${DEPLOY_DIGESTS_FILE:-deployment-digests.env}"
OVERLAY_DIR="${KUSTOMIZE_ROOT}/${OVERLAY}"
RENDERED_OUTPUT="$(mkdir -p "$(dirname "$RENDERED_OUTPUT")" && cd "$(dirname "$RENDERED_OUTPUT")" && pwd)/$(basename "$RENDERED_OUTPUT")"
DEPLOY_DIGESTS_FILE="$(mkdir -p "$(dirname "$DEPLOY_DIGESTS_FILE")" && cd "$(dirname "$DEPLOY_DIGESTS_FILE")" && pwd)/$(basename "$DEPLOY_DIGESTS_FILE")"
ZERO_DIGEST='sha256:0000000000000000000000000000000000000000000000000000000000000000'

layers=(
  layer1-ingestion
  layer2-extraction
  layer3-knowledge
  layer4-agents
  layer5-ground-truth
  layer6-benchmarks
  frontend
)

if [[ ! -d "$OVERLAY_DIR" ]]; then
  echo "::error::Kustomize overlay does not exist: ${OVERLAY_DIR}" >&2
  exit 1
fi
OVERLAY_DIR="$(cd "$OVERLAY_DIR" && pwd)"

if ! command -v kustomize >/dev/null 2>&1; then
  echo "::error::kustomize is required to render deployment manifests" >&2
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "::error::docker is required to resolve image tags to immutable digests" >&2
  exit 1
fi

: > "$DEPLOY_DIGESTS_FILE"

for layer in "${layers[@]}"; do
  image_name="${REGISTRY}/${OWNER}/fabric_4l/${layer}"
  image_ref="${image_name}:${IMAGE_TAG}"
  echo "Resolving digest for ${image_ref}"

  digest="$(docker buildx imagetools inspect "$image_ref" --format '{{json .Manifest.Digest}}' | tr -d '"')"

  if [[ ! "$digest" =~ ^sha256:[a-f0-9]{64}$ ]]; then
    echo "::error::Failed to resolve a valid sha256 digest for ${image_ref}; got '${digest}'" >&2
    exit 1
  fi

  if [[ "$digest" == "$ZERO_DIGEST" ]]; then
    echo "::error::Refusing to deploy zero digest for ${image_ref}" >&2
    exit 1
  fi

  echo "${layer}=${digest}" >> "$DEPLOY_DIGESTS_FILE"
  (
    cd "$OVERLAY_DIR"
    kustomize edit --reorder none set image "services/${layer}=${image_name}@${digest}" >/dev/null
  )
  echo "Pinned services/${layer} to ${image_name}@${digest}"
done

kustomize build --load-restrictor=LoadRestrictionsNone "$OVERLAY_DIR" > "$RENDERED_OUTPUT"

if grep -q "$ZERO_DIGEST" "$RENDERED_OUTPUT"; then
  echo "::error::Rendered manifest still contains zero digests" >&2
  exit 1
fi

for layer in "${layers[@]}"; do
  if grep -Eq "fabric_4l/${layer}:[^[:space:]\"']+" "$RENDERED_OUTPUT"; then
    echo "::error::Rendered manifest contains mutable tag reference for ${layer}; digest pinning is required" >&2
    exit 1
  fi
  if ! grep -Eq "fabric_4l/${layer}@sha256:[a-f0-9]{64}" "$RENDERED_OUTPUT"; then
    echo "::error::Rendered manifest does not contain an immutable digest reference for ${layer}" >&2
    exit 1
  fi
done

echo "Rendered immutable manifest: ${RENDERED_OUTPUT}"
echo "Resolved digests written to: ${DEPLOY_DIGESTS_FILE}"
