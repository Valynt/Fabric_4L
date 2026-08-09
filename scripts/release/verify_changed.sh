#!/usr/bin/env bash
# V1 Release Factory — narrowest-first verification for a change set.
#
# Given the files changed relative to a base ref, run the narrowest relevant
# existing gates first, then the broader local gate. This wraps canonical
# make/pnpm targets; it defines no new gates.
#
# Usage:
#   scripts/release/verify_changed.sh [base_ref]   (default: origin/main)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${REPO_ROOT}"

BASE_REF="${1:-origin/main}"
CHANGED="$(git diff --name-only "${BASE_REF}"...HEAD 2>/dev/null || git diff --name-only HEAD~1)"

if [ -z "${CHANGED}" ]; then
    echo "No changed files detected against ${BASE_REF}; nothing to verify."
    exit 0
fi

echo "Changed files:"
echo "${CHANGED}" | sed 's/^/  /'

run() {
    echo "→ ${*}"
    "${@}"
}

matches() {
    echo "${CHANGED}" | grep -qE "$1"
}

# Layer-scoped Python suites
matches '^services/layer1-ingestion/'   && run make test-layer1 lint-layer1
matches '^services/layer2-extraction/'  && run make test-layer2 lint-layer2
matches '^services/layer3-knowledge/'   && run make test-layer3 lint-layer3
matches '^services/layer4-agents/'      && run make test-layer4 lint-layer4
matches '^services/layer5-ground-truth/' && run make test-layer5 lint-layer5
matches '^services/layer6-benchmarks/'  && run make test-layer6 lint-layer6

# Frontend
matches '^apps/web/' && {
    run pnpm --dir apps/web run lint
    run pnpm --dir apps/web run typecheck
    run pnpm --dir apps/web run test
}

# Cross-cutting surfaces
matches '^packages/'                        && run pytest tests/contract -q
matches '^contracts/'                       && run pnpm run check:contract-compliance
matches 'migrations/|alembic'               && run make check-migration-heads
matches '^tests/tenancy/|tenant'            && run pytest tests/tenancy -q
matches '^release/v1/|^scripts/release/'    && run pytest tests/release -q
matches '^\.github/workflows/'              && run python scripts/ci/check_workflow_references.py

# Broad local gate last
run make verify
echo "✅ verify_changed complete (production readiness NOT assessed; run make production-readiness-gate)"
