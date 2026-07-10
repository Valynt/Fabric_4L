#!/usr/bin/env bash
set -euo pipefail

NAMESPACE="${NAMESPACE:-value-fabric}"
TIMEOUT="${TIMEOUT:-240s}"

declare -a DEPLOYMENTS=(
  "layer1-ingestion"
  "layer2-extraction"
  "layer3-knowledge"
  "layer4-agents"
  "layer5-ground-truth"
  "frontend"
)

declare -A SMOKE_URLS=(
  ["layer1-ingestion"]="http://layer1-ingestion:8000/health"
  ["layer2-extraction"]="http://layer2-extraction:8000/health"
  ["layer3-knowledge"]="http://layer3-knowledge:8001/health"
  ["layer4-agents"]="http://layer4-agents:8000/health"
  ["layer5-ground-truth"]="http://layer5-ground-truth:8005/api/v1/health"
  ["frontend"]="http://frontend:3000/"
)

echo "🔎 Waiting for deployment rollouts in namespace ${NAMESPACE}..."
for deployment in "${DEPLOYMENTS[@]}"; do
  kubectl rollout status "deployment/${deployment}" -n "${NAMESPACE}" --timeout="${TIMEOUT}"
done

echo "🔎 Running post-deploy smoke checks..."
for deployment in "${DEPLOYMENTS[@]}"; do
  url="${SMOKE_URLS[$deployment]}"
  echo "  • ${deployment}: ${url}"
  kubectl run "smoke-${deployment}" \
    --namespace "${NAMESPACE}" \
    --image=curlimages/curl:8.12.1 \
    --restart=Never \
    --rm -i \
    --command -- sh -c "curl -fsS --max-time 10 '${url}' >/dev/null"
done

echo "✅ Post-deploy smoke checks passed (L1-L5 + frontend)."
