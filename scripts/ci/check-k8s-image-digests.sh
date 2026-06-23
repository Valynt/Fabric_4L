#!/bin/bash
# CI gate: Fail if production overlays use mutable image tags
# Mutable tags: :main, :latest, :dev, branch names
# This ensures production deployments use immutable SHA256 digests

set -euo pipefail

OVERLAYS="k8s/overlays/production k8s/overlays/staging"
MUTABLE_TAGS=":main :latest :dev :master :develop"

echo "Checking for mutable image tags in production overlays..."

FAILED=0
for overlay in $OVERLAYS; do
  if [ ! -d "$overlay" ]; then
    echo "  SKIP: $overlay (directory not found)"
    continue
  fi

  echo "  Checking $overlay..."
  
  for tag in $MUTABLE_TAGS; do
    if grep -rE "image:.*${tag}" "$overlay" 2>/dev/null; then
      echo "  ERROR: Mutable image tag '${tag}' found in $overlay"
      FAILED=1
    fi
  done
  
  # Also check Kustomize images section for newTag with mutable tags
  if grep -rE "newTag:.*(main|latest|dev|master|develop)" "$overlay/kustomization.yaml" 2>/dev/null; then
    echo "  ERROR: Mutable newTag found in $overlay/kustomization.yaml"
    FAILED=1
  fi
done

if [ $FAILED -eq 1 ]; then
  echo ""
  echo "FAIL: Mutable image tags found in production overlays"
  echo "Production overlays must use SHA256 digest-pinned images:"
  echo "  image: ghcr.io/<org>/<image>@sha256:<real_digest>"
  echo "Or use Kustomize digest field:"
  echo "  digest: sha256:<real_digest>"
  exit 1
fi

echo "PASS: No mutable tags in production overlays"
exit 0
