#!/usr/bin/env bash
# V1 Release Factory — release-candidate certification harness.
#
# Certifies a specific immutable SHA by composing the EXISTING canonical gates
# in the 17-step sequence defined by release/v1/launch-contract.yaml. This
# script is fail-closed and read-only over the repository: the certifier may
# not remediate failures during certification. On the first failing step the
# run stops and the candidate is marked failed.
#
# Steps that require live staging infrastructure are executed only when
# CERTIFY_LIVE=1; otherwise they are recorded as "not-run" and the candidate
# CANNOT be certified (fail closed), only rehearsed.
#
# Usage:
#   scripts/release/certify_candidate.sh <candidate_sha>
#
# Output:
#   artifacts/release/certification-<sha>/steps.jsonl
#   artifacts/release/certification-<sha>/candidate-manifest.json (via build_evidence_bundle.sh)

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${REPO_ROOT}"

CANDIDATE_SHA="${1:-}"
if [ -z "${CANDIDATE_SHA}" ]; then
    echo "usage: scripts/release/certify_candidate.sh <candidate_sha>" >&2
    exit 2
fi

LIVE="${CERTIFY_LIVE:-0}"
OUT_DIR="artifacts/release/certification-${CANDIDATE_SHA}"
STEPS_FILE="${OUT_DIR}/steps.jsonl"
mkdir -p "${OUT_DIR}"
: >"${STEPS_FILE}"

fail() {
    echo "❌ certification failed at: $1" >&2
    echo "The certifier may not remediate failures; candidate ${CANDIDATE_SHA} is NOT certified." >&2
    exit 1
}

record() {
    # record <step> <command> <exit_code> <started> <finished>
    printf '{"gate": "%s", "command": "%s", "exit_code": %d, "started_at": "%s", "finished_at": "%s"}\n' \
        "$1" "$2" "$3" "$4" "$5" >>"${STEPS_FILE}"
}

step() {
    # step <name> <command...>
    local name="$1"; shift
    local started finished
    started="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "→ [${name}] ${*}"
    local log="${OUT_DIR}/$(echo "${name}" | tr ' /' '__').log"
    if "${@}" >"${log}" 2>&1; then
        finished="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
        record "${name}" "${*}" 0 "${started}" "${finished}"
    else
        local rc=$?
        finished="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
        record "${name}" "${*}" "${rc}" "${started}" "${finished}"
        fail "${name} (exit ${rc}, log: ${log})"
    fi
}

live_step() {
    local name="$1"; shift
    if [ "${LIVE}" = "1" ]; then
        step "${name}" "${@}"
    else
        echo "⏭  [${name}] requires CERTIFY_LIVE=1 staging environment — recorded as not-run"
        record "${name}" "${*}" -1 "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    fi
}

# 1. Verify candidate SHA and clean checkout (read-only: refuse to mutate).
[ "$(git rev-parse HEAD)" = "${CANDIDATE_SHA}" ] || fail "checkout is not at candidate SHA ${CANDIDATE_SHA}"
[ -z "$(git status --short)" ] || fail "working tree is not clean"
record "01-verify-candidate-sha" "git rev-parse HEAD" 0 "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$(date -u +%Y-%m-%dT%H:%M:%SZ)"

# 2. Install from lock files.
step "02-install-lockfiles" pnpm install --frozen-lockfile
step "02b-python-setup" make setup

# 3. Full static, unit, integration, contract, and tenant suites.
step "03a-verify" make verify
step "03b-production-readiness-gate" make production-readiness-gate
step "03c-tenant-suite" pytest tests/tenancy -q

# 4. Build production artifacts.
step "04-production-build" pnpm --dir apps/web run build
live_step "04b-docker-build" make docker-build

# 5. SBOM and build provenance (produced by build-deploy workflow attestations).
live_step "05-sbom-provenance" bash scripts/ci/build-reproducibility-check.sh

# 6. Deploy to a clean production-like staging environment.
live_step "06-staging-deploy" make preflight

# 7-8. Migration rehearsal: empty database and previous-release baseline.
live_step "07-migrations-empty-db" make check-migration-postgres-roundtrip
live_step "08-migrations-from-baseline" make db-migrate-check

# 9. Critical browser journeys.
live_step "09-critical-browser-journeys" pnpm --dir apps/web run test:e2e

# 10. DAST and security checks.
step "10a-security-suite" pytest tests/security -q
live_step "10b-dast" make security-readiness-gate

# 11. Launch, burst, and soak load profiles (50 rps sustained / 100 rps burst).
live_step "11-load-profiles" make perf-test

# 12. Provider failures and queue retry behavior.
live_step "12-provider-failure-drills" pytest tests/reliability -q

# 13. Create and restore a backup.
live_step "13-backup-restore" make test-backup-drills

# 14. Application rollback rehearsal.
step "14-rollback-policy" pytest tests/release/test_rollback_procedure.py -q
live_step "14b-rollback-rehearsal" python scripts/ci/verify_release_rollback.py

# 15. AI quality and adversarial evaluation.
live_step "15-ai-evaluation" make evals

# 16. Dashboards, alerts, and runbooks.
step "16-observability-readiness" pytest tests/release/test_observability_deployment_readiness.py -q --no-mandatory-dep-check

# 17. Produce the release evidence bundle.
step "17-evidence-bundle" bash scripts/release/build_evidence_bundle.sh "${CANDIDATE_SHA}" "${OUT_DIR}"

if [ "${LIVE}" = "1" ]; then
    echo "✅ Candidate ${CANDIDATE_SHA} passed the certification sequence."
    echo "   Production rollout still requires human authorization recorded in the manifest."
else
    echo "⚠️  Rehearsal complete. CERTIFY_LIVE=1 with staging infrastructure is required for certification;"
    echo "    steps recorded as not-run keep the candidate uncertified (fail closed)."
fi
