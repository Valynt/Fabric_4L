#!/usr/bin/env bash
set -euo pipefail

# P2-008: Rollback kubeconfig script for Helm releases.
# Usage: ./rollback-kubeconfig.sh <release-name> [namespace]
# Rolls back the specified Helm release to the previous revision.

RELEASE_NAME="${1:-}"
NAMESPACE="${2:-default}"

if [[ -z "${RELEASE_NAME}" ]]; then
    echo "Usage: $0 <release-name> [namespace]"
    echo "Example: $0 fabric default"
    exit 1
fi

echo "Checking current revision for release '${RELEASE_NAME}' in namespace '${NAMESPACE}'..."

CURRENT_REVISION=$(helm history "${RELEASE_NAME}" --namespace "${NAMESPACE}" --max 2 2>/dev/null | tail -n 1 | awk '{print $1}')

if [[ -z "${CURRENT_REVISION}" ]]; then
    echo "ERROR: No history found for release '${RELEASE_NAME}'."
    exit 1
fi

PREVIOUS_REVISION=$((CURRENT_REVISION - 1))

if [[ ${PREVIOUS_REVISION} -lt 1 ]]; then
    echo "ERROR: No previous revision available to roll back to."
    exit 1
fi

echo "Current revision: ${CURRENT_REVISION}"
echo "Rolling back to revision: ${PREVIOUS_REVISION}"
echo ""

helm rollback "${RELEASE_NAME}" "${PREVIOUS_REVISION}" --namespace "${NAMESPACE}"

echo ""
echo "Rollback completed. Verifying rollout status..."

kubectl rollout status deployment -l app.kubernetes.io/instance="${RELEASE_NAME}" --namespace "${NAMESPACE}" --timeout=300s

echo "Rollback verification complete."
