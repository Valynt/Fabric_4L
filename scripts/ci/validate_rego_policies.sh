#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

if ! command -v opa >/dev/null 2>&1; then
    echo "[SKIP] opa CLI not installed; Rego validation deferred"
    exit 0
fi

echo "[OK] Running OPA tests for k8s/policy ..."
opa test "${REPO_ROOT}/k8s/policy"
