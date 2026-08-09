#!/usr/bin/env bash
# V1 Release Factory — Phase 1 baseline.
#
# Runs the canonical gates from a clean checkout and records a classified
# baseline. This script VALIDATES; it never repairs, commits, or pushes.
#
# Classification buckets (recorded per failed gate in the baseline artifact):
#   repo-owned-failure | env-failure | external-failure | flaky |
#   missing-credential | informational | launch-blocker
#
# Usage:
#   scripts/release/baseline.sh [--skip-setup]
#
# Output:
#   artifacts/readiness/release-baseline-<sha>.json
#   (copy the classified summary into release/v1/current-state.yaml deliberately;
#    this script does not write into release/v1/ so that CI never mutates
#    contract artifacts.)

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${REPO_ROOT}"

SKIP_SETUP=false
[ "${1:-}" = "--skip-setup" ] && SKIP_SETUP=true

SHA="$(git rev-parse HEAD)"
BRANCH="$(git rev-parse --abbrev-ref HEAD)"
OUT_DIR="artifacts/readiness"
OUT_FILE="${OUT_DIR}/release-baseline-${SHA}.json"
mkdir -p "${OUT_DIR}"

if [ -n "$(git status --short)" ]; then
    echo "❌ baseline requires a clean checkout; working tree is dirty" >&2
    git status --short >&2
    exit 1
fi

GATES=()
$SKIP_SETUP || GATES+=("make setup")
GATES+=(
    "make verify"
    "make production-readiness-gate"
    "make check-behavior-contract"
    "make check-behavior-readiness-audit"
)

results=""
overall=0
for gate in "${GATES[@]}"; do
    started="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    log="${OUT_DIR}/baseline-$(echo "${gate}" | tr ' /' '__')-${SHA:0:12}.log"
    echo "→ baseline gate: ${gate}"
    if ${gate} >"${log}" 2>&1; then
        exit_code=0
    else
        exit_code=$?
        overall=1
    fi
    finished="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    # Classification is a human/Release-Director decision; failures default to
    # "unclassified" and MUST be triaged before any launch-readiness claim.
    # Flaky classification must come from the flakiness-tracker workflow output,
    # not from local retries.
    classification="pass"
    [ "${exit_code}" -ne 0 ] && classification="unclassified"
    results="${results}$(printf '        {"gate": "%s", "exit_code": %d, "classification": "%s", "started_at": "%s", "finished_at": "%s", "log": "%s"},\n' "${gate}" "${exit_code}" "${classification}" "${started}" "${finished}" "${log}")"
done
results="${results%,*}"

cat >"${OUT_FILE}" <<EOF
{
    "schema_version": 1,
    "kind": "release-baseline",
    "sha": "${SHA}",
    "branch": "${BRANCH}",
    "generated_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "classification_buckets": [
        "repo-owned-failure", "env-failure", "external-failure",
        "flaky", "missing-credential", "informational", "launch-blocker"
    ],
    "gates": [
${results}
    ]
}
EOF

echo "Baseline written to ${OUT_FILE}"
if [ "${overall}" -ne 0 ]; then
    echo "⚠️  One or more baseline gates failed; triage and classify each failure before proceeding." >&2
fi
exit "${overall}"
