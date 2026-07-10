#!/usr/bin/env bash
# build-reproducibility-check.sh — Verify build determinism by comparing two builds
#
# Builds the same Dockerfile twice with identical inputs and compares layer digests.
# Deterministic builds produce byte-identical layers (excluding timestamps).
#
# Usage:
#   ./scripts/ci/build-reproducibility-check.sh [layer-name]
#   ./scripts/ci/build-reproducibility-check.sh layer3-knowledge
#   ./scripts/ci/build-reproducibility-check.sh all
#
# Exit codes:
#   0 — Builds are reproducible (layer digests match)
#   1 — Builds diverged or an error occurred
set -euo pipefail

LAYER="${1:-all}"
OUTPUT_DIR="artifacts/reproducibility"
mkdir -p "$OUTPUT_DIR"

LAYERS=()
if [[ "$LAYER" == "all" ]]; then
  LAYERS=(layer1-ingestion layer2-extraction layer3-knowledge layer4-agents layer5-ground-truth layer6-benchmarks frontend)
else
  LAYERS=("$LAYER")
fi

FAILURES=0
TOTAL=0

for layer in "${LAYERS[@]}"; do
  TOTAL=$((TOTAL + 1))

  if [[ "$layer" == "frontend" ]]; then
    CONTEXT="frontend"
  else
    CONTEXT="value-fabric/${layer}"
  fi

  if [[ ! -f "${CONTEXT}/Dockerfile" ]]; then
    echo "⚠️  SKIP: ${layer} — no Dockerfile found at ${CONTEXT}/Dockerfile"
    continue
  fi

  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "Building ${layer} (pass 1 of 2)..."
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

  # Build pass 1
  docker build \
    --no-cache \
    --build-arg BUILDKIT_INLINE_CACHE=0 \
    -t "repro-${layer}:build1" \
    "$CONTEXT" > "${OUTPUT_DIR}/${layer}-build1.log" 2>&1 || { cat "${OUTPUT_DIR}/${layer}-build1.log"; exit 1; }
  tail -5 "${OUTPUT_DIR}/${layer}-build1.log"

  echo "Building ${layer} (pass 2 of 2)..."
  # Build pass 2
  docker build \
    --no-cache \
    --build-arg BUILDKIT_INLINE_CACHE=0 \
    -t "repro-${layer}:build2" \
    "$CONTEXT" > "${OUTPUT_DIR}/${layer}-build2.log" 2>&1 || { cat "${OUTPUT_DIR}/${layer}-build2.log"; exit 1; }
  tail -5 "${OUTPUT_DIR}/${layer}-build2.log"

  # Extract layer digests
  DIGEST1=$(docker inspect --format='{{.RootFS.Layers}}' "repro-${layer}:build1")
  DIGEST2=$(docker inspect --format='{{.RootFS.Layers}}' "repro-${layer}:build2")

  # Compare config (excludes container ID and timestamps)
  CONFIG1=$(docker inspect --format='{{.Config}}' "repro-${layer}:build1")
  CONFIG2=$(docker inspect --format='{{.Config}}' "repro-${layer}:build2")

  LAYER_MATCH="false"
  CONFIG_MATCH="false"

  if [[ "$DIGEST1" == "$DIGEST2" ]]; then
    LAYER_MATCH="true"
  fi

  if [[ "$CONFIG1" == "$CONFIG2" ]]; then
    CONFIG_MATCH="true"
  fi

  # Write per-layer report
  cat > "${OUTPUT_DIR}/${layer}-reproducibility.json" <<EOF
{
  "layer": "${layer}",
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "layer_digests_match": ${LAYER_MATCH},
  "config_match": ${CONFIG_MATCH},
  "build1_layers": "${DIGEST1}",
  "build2_layers": "${DIGEST2}"
}
EOF

  if [[ "$LAYER_MATCH" == "true" && "$CONFIG_MATCH" == "true" ]]; then
    echo "  ✅ ${layer}: Builds are reproducible (layers + config match)"
  elif [[ "$LAYER_MATCH" == "true" ]]; then
    echo "  ⚠️  ${layer}: Layer digests match but config differs (timestamps expected)"
  else
    echo "  ❌ ${layer}: Builds DIVERGED — layers differ between builds"
    FAILURES=$((FAILURES + 1))
  fi

  # Cleanup
  docker rmi "repro-${layer}:build1" "repro-${layer}:build2" >/dev/null 2>&1 || true
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Reproducibility Summary: ${TOTAL} checked, ${FAILURES} diverged"
echo "Reports: ${OUTPUT_DIR}/"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [[ $FAILURES -gt 0 ]]; then
  echo "❌ REPRODUCIBILITY CHECK FAILED"
  exit 1
fi

echo "✅ ALL BUILDS REPRODUCIBLE"
exit 0
