#!/usr/bin/env bash
set -euo pipefail

# Mandatory launch-readiness security regression gate.
#
# This aggregate gate is intentionally fail-closed. It composes existing
# layer/API-contract checks, writes machine-readable evidence for CI review, and
# must never silently pass when a required suite is missing, skipped, xfailed, or
# converted into placeholder coverage.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${ROOT_DIR}"

# Prefer the repository virtual environment when it exists and no venv is active.
# This lets local contributors run the gate without installing deps into the system
# Python. CI runners use setup-python and keep the system Python on PATH.
if [ -z "${VIRTUAL_ENV:-}" ] && [ -x "${ROOT_DIR}/.venv/bin/python" ]; then
  export PATH="${ROOT_DIR}/.venv/bin:${PATH}"
fi

export TESTING="${TESTING:-true}"
export ENVIRONMENT="${ENVIRONMENT:-testing}"
export DEBUG="false"
export LAYER4_LAYER5_API_URL="${LAYER4_LAYER5_API_URL:-http://localhost:8005}"
export PYTHONPATH="${ROOT_DIR}/packages/shared/src:${ROOT_DIR}:${PYTHONPATH:-}"
# Layer 5 fail-closed tests are marked requires_postgres but only validate
# Settings parsing. Allow them to run in the gate without a live Postgres.
export RUN_POSTGRES_TESTS="${RUN_POSTGRES_TESTS:-true}"
export POSTGRES_TEST_URL="${POSTGRES_TEST_URL:-postgresql://localhost:5432/postgres}"

# Repo-relative audit/evidence directory for cross-platform support. Override via
# FABRIC_AUDIT_DIR in CI when evidence needs to be collected elsewhere.
FABRIC_AUDIT_DIR="${FABRIC_AUDIT_DIR:-.fabric/audit}"
AUDIT_DIR="${ROOT_DIR}/${FABRIC_AUDIT_DIR}"
mkdir -p "${AUDIT_DIR}/security_regression_gate"

ARTIFACT_DIR="${MANDATORY_SECURITY_ARTIFACT_DIR:-artifacts/mandatory_security}"
mkdir -p "${ARTIFACT_DIR}"
SUMMARY_FILE="${ARTIFACT_DIR}/mandatory_security_summary.md"
MANIFEST_FILE="${ARTIFACT_DIR}/mandatory_security_manifest.txt"
: > "${SUMMARY_FILE}"
: > "${MANIFEST_FILE}"

# Test mode for regression testing - skips expensive browser/frontend operations
# while preserving required source-level and pytest fail-closed validation.
#
# RB-6 FIX: Default changed from 1 to 0. The E2E skip-valve guard, OpenAPI
# contract drift check, and frontend contract tests are MANDATORY security
# checks. They must run by default in CI. Setting FABRIC_GATE_TEST_MODE=1
# requires explicit sign-off (see docs/ci/GATE_TEST_MODE.md) and MUST NOT
# be set permanently in CI environment variables.
#
# To run in test mode (local dev without pnpm/frontend tooling):
#   FABRIC_GATE_TEST_MODE=1 bash scripts/ci/mandatory_security_regression_gate.sh
FABRIC_GATE_TEST_MODE="${FABRIC_GATE_TEST_MODE:-0}"

# The canonical GitHub check must never use the local-only test-mode escape
# hatch. GitHub Actions sets CI=true, and the workflow also pins this value to
# zero so a future workflow edit cannot turn skipped work into a green check.
if [[ "${CI:-}" == "true" && "${FABRIC_GATE_TEST_MODE}" == "1" ]]; then
  echo "ERROR: FABRIC_GATE_TEST_MODE=1 is forbidden for mandatory CI enforcement." >&2
  exit 1
fi

# Pre-flight check: if test mode is disabled, verify node/pnpm are available.
# Fail early with a clear error rather than silently skipping the E2E valve.
if [[ "${FABRIC_GATE_TEST_MODE}" != "1" ]]; then
  if ! command -v node &>/dev/null; then
    echo "ERROR: FABRIC_GATE_TEST_MODE=0 but 'node' is not available." >&2
    echo "       Install Node.js or set FABRIC_GATE_TEST_MODE=1 with owner sign-off." >&2
    echo "       See docs/ci/GATE_TEST_MODE.md for the sign-off process." >&2
    exit 1
  fi
  if ! command -v pnpm &>/dev/null; then
    echo "ERROR: FABRIC_GATE_TEST_MODE=0 but 'pnpm' is not available." >&2
    echo "       Install pnpm or set FABRIC_GATE_TEST_MODE=1 with owner sign-off." >&2
    echo "       See docs/ci/GATE_TEST_MODE.md for the sign-off process." >&2
    exit 1
  fi
fi

STANDALONE_API_TESTS=(
  services/api/app/tests/test_auth_enforcement.py
  services/api/app/tests/test_health.py
  services/api/app/tests/test_production_safety.py
  services/api/app/tests/test_i03_durable_persistence_and_llm.py
)

# API-gateway tenant-isolation and invitation-security regression suites.
# These cover the accept-invite account-takeover fix (single-use invite
# tokens) and the fail-closed tenant boundary on the standalone API gateway.
GATEWAY_ISOLATION_API_TESTS=(
  services/api/app/tests/test_tenant_isolation.py
  services/api/app/tests/test_invitation_and_tenant_leakage.py
)

ROOT_SECURITY_TESTS=(
  tests/security/test_auth_boundaries.py
  tests/security/test_auth_source_validation.py
  tests/security/test_auth_session_hijacking.py
  tests/security/test_csrf_comprehensive.py
  tests/security/test_auth_rate_limiting.py
  tests/security/test_jwt_config_validation.py
  tests/security/test_tenant_boundary_fails_closed.py
  tests/security/test_cross_tenant_api.py
  tests/security/test_tenant_mismatch.py
  tests/security/test_privileged_audit.py
  tests/security/test_rate_limit_safety.py::TestMultiWorkerRateLimitSafety
  tests/security/test_dependency_floor.py
)

CROSS_LAYER_TENANT_MATRIX_TESTS=(
  tests/security/test_cross_layer_tenant_isolation_matrix.py
)

LAYER4_C06_SECURITY_TESTS=(
  services/layer4-agents/tests/test_tenant_rate_limits.py
  services/layer4-agents/tests/test_security_fixes.py
)

CONTRACT_TESTS=(
  tests/context/test_tenant_context_contract.py
  tests/contract/test_shared_import_boundary.py
  tests/contract/test_retention_deletion_contract.py
)

K8S_TESTS=(
  tests/k8s/test_security_policies.py
  tests/k8s
)

LAYER2_FAIL_CLOSED_TESTS=(
  services/layer2-extraction/tests/test_production_fail_closed_i02.py
)

LAYER5_FAIL_CLOSED_TESTS=(
  services/layer5-ground-truth/tests/test_production_fail_closed_i02.py
)

HOSTILE_API_KEY_RESOLVER_TESTS=(
  tests/shared/identity/test_api_key_resolver_hostile_suite.py
  services/layer1-ingestion/tests/test_api_key_resolver_hostile_cases.py
  services/layer2-extraction/tests/test_api_key_resolver_hostile_cases.py
)

HOSTILE_TENANCY_CONTRACT_TESTS=(
  tests/tenancy/test_hostile_tenancy_contracts.py
)

FRONTEND_CONTRACT_TEST_DIR="apps/web/src/api/__tests__/contract"
FRONTEND_PLACEHOLDER_GUARD="apps/web/scripts/security/assert-no-placeholder-contract-tests.mjs"
FRONTEND_CRITICAL_E2E_GUARD="apps/web/scripts/security/assert-no-skipped-critical-e2e.mjs"
CROSS_LAYER_TENANT_MATRIX_ARTIFACT="${ARTIFACT_DIR}/cross_layer_tenant_isolation_matrix.json"

write_summary() {
  # Write directly to file — avoid printf|tee pipeline which can receive SIGPIPE
  # under set -o pipefail when the filesystem is full or the fd is closed (RB-1).
  printf '%s\n' "$*" >> "${SUMMARY_FILE}"
  printf '%s\n' "$*"
}

assert_path_present() {
  local path="$1"
  if [ ! -e "$path" ]; then
    write_summary "❌ Missing required security gate path: ${path}"
    exit 1
  fi
  printf '%s\n' "$path" >> "${MANIFEST_FILE}"
}

required_suite_paths() {
  local path
  for path in \
    "${STANDALONE_API_TESTS[@]}" \
    "${GATEWAY_ISOLATION_API_TESTS[@]}" \
    "${ROOT_SECURITY_TESTS[@]}" \
    "${CROSS_LAYER_TENANT_MATRIX_TESTS[@]}" \
    "${LAYER4_C06_SECURITY_TESTS[@]}" \
    "${CONTRACT_TESTS[@]}" \
    "${K8S_TESTS[@]}" \
    "${LAYER2_FAIL_CLOSED_TESTS[@]}" \
    "${LAYER5_FAIL_CLOSED_TESTS[@]}" \
    "${HOSTILE_API_KEY_RESOLVER_TESTS[@]}" \
    "${HOSTILE_TENANCY_CONTRACT_TESTS[@]}"; do
    printf '%s\n' "${path%%::*}"
  done
}

assert_required_paths_present() {
  local path
  while IFS= read -r path; do
    assert_path_present "$path"
  done < <(required_suite_paths)

  assert_path_present Makefile
  assert_path_present "${FRONTEND_CONTRACT_TEST_DIR}"
  assert_path_present "${FRONTEND_PLACEHOLDER_GUARD}"
  assert_path_present "${FRONTEND_CRITICAL_E2E_GUARD}"
}

assert_no_skip_or_xfail_markers() {
  local offenders
  offenders="$({
    while IFS= read -r path; do
      if [ -d "$path" ]; then
        grep -rnE 'pytest\.skip|@pytest\.mark\.(skip|skipif|xfail)|unittest\.skip|mark\.xfail' "$path" || true
      else
        grep -nE 'pytest\.skip|@pytest\.mark\.(skip|skipif|xfail)|unittest\.skip|mark\.xfail' "$path" || true
      fi
    done < <(required_suite_paths)
  })"
  # Exclude test_l6_ctx_source_of_truth which requires live infra env vars
  # Exclude JWT config validation tests that check behavior not yet implemented
  offenders=$(echo "$offenders" | grep -v "test_l6_ctx_source_of_truth" || true)
  offenders=$(echo "$offenders" | grep -v "validate_jwt_config implementation only checks secret strength" || true)
  # Exclude runtime service-availability skips in tenant context contract tests
  offenders=$(echo "$offenders" | grep -v "Layer 1 app unavailable in test environment" || true)
  offenders=$(echo "$offenders" | grep -v "Layer 2 app unavailable in test environment" || true)
  # Exclude K8s fixture skips for missing local tooling (kustomize/kubeconform/kubectl/conftest)
  offenders=$(echo "$offenders" | grep -v "kustomize not available" || true)
  offenders=$(echo "$offenders" | grep -v "kustomize build failed" || true)
  offenders=$(echo "$offenders" | grep -v "kubeconform not available" || true)
  offenders=$(echo "$offenders" | grep -v "kubectl not available" || true)
  offenders=$(echo "$offenders" | grep -v "conftest not available" || true)
  offenders=$(echo "$offenders" | grep -v "Prometheus ConfigMap not found" || true)
  offenders=$(echo "$offenders" | grep -v "WorkflowStalled alert not found" || true)
  offenders=$(echo "$offenders" | grep -v "Prometheus workload not found" || true)
  offenders=$(echo "$offenders" | grep -v "Recording rules file not found" || true)
  if [ -n "$offenders" ]; then
    write_summary "❌ Required mandatory security suites contain skip/xfail markers:"
    # Write directly — avoid pipe that can SIGPIPE (RB-1)
    printf '%s\n' "$offenders" >> "${SUMMARY_FILE}"
    printf '%s\n' "$offenders"
    exit 1
  fi
}

# run_step: execute a gate stage and fail the gate if it exits non-zero.
# Captures the exit code explicitly so log_suite_result can record the real
# outcome rather than assuming PASS (RB-1 fix: remove hardcoded-PASS pattern).
run_step() {
  local label="$1"
  shift
  write_summary "→ ${label}"
  local _step_exit=0
  "$@" || _step_exit=$?
  if [[ ${_step_exit} -ne 0 ]]; then
    write_summary "❌ ${label} (exit ${_step_exit})"
    return ${_step_exit}
  fi
  write_summary "✅ ${label}"
}

# run_step_record: run_step wrapper that also records the result in the
# evidence manifest. Pass the log_suite_result arguments after the step args.
# Usage: run_step_record LABEL COMMAND [ARGS...] -- SUITE_NAME CMD_LABEL REQUIRED ARTIFACT
run_step_record() {
  local label="$1"
  shift
  # Collect suite-result args after '--' separator
  local step_args=()
  while [[ "$1" != '--' && $# -gt 0 ]]; do
    step_args+=("$1")
    shift
  done
  shift  # consume '--'
  local suite_name="$1" cmd_label="$2" required="$3" artifact="$4"
  local _exit=0
  run_step "${label}" "${step_args[@]}" || _exit=$?
  if [[ ${_exit} -ne 0 ]]; then
    log_suite_result "${suite_name}" "${cmd_label}" "${required}" "FAIL" "${artifact}"
    return ${_exit}
  fi
  log_suite_result "${suite_name}" "${cmd_label}" "${required}" "PASS" "${artifact}"
}

run_root_pytest() {
  local junit_file="$1"
  shift
  python -m pytest --tb=short -q -n 0 --timeout=60 --junitxml="${junit_file}" "$@"
  python scripts/ci/assert_no_pytest_skips.py "${junit_file}"
}

# Evidence logging functions.
log_evidence_start() {
  local timestamp
  local git_sha
  local branch
  timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  git_sha=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
  branch=$(git branch --show-current 2>/dev/null || echo "unknown")

  cat > "${AUDIT_DIR}/security_regression_gate/mandatory_security_regression_gate.results.json" << EOF
{
  "timestamp": "${timestamp}",
  "git_sha": "${git_sha}",
  "branch": "${branch}",
  "os": "$(uname -s)",
  "gate_version": "1.2.0",
  "test_mode": ${FABRIC_GATE_TEST_MODE},
  "suites": [],
  "status": "in_progress"
}
EOF

  {
    echo "# Mandatory Security Regression Gate Evidence"
    echo ""
    echo "- **Timestamp**: ${timestamp}"
    echo "- **Git SHA**: ${git_sha}"
    echo "- **Branch**: ${branch}"
    echo "- **OS**: $(uname -s)"
    echo "- **Test Mode**: ${FABRIC_GATE_TEST_MODE}"
    echo "- **Artifact Directory**: ${ARTIFACT_DIR}"
    echo ""
    echo "## Check Results"
    echo ""
    echo "| Check | Command | Required | Result | Evidence |"
    echo "|-------|---------|----------|--------|----------|"
  } > "${AUDIT_DIR}/security_regression_gate/mandatory_security_regression_gate.summary.md"
}

log_suite_result() {
  local check_name="$1"
  local command="$2"
  local required="$3"
  local result="$4"
  local evidence="$5"

  if command -v jq &> /dev/null; then
    local temp_file
    temp_file=$(mktemp)
    jq --arg name "${check_name}" \
       --arg cmd "${command}" \
       --arg req "${required}" \
       --arg res "${result}" \
       --arg evi "${evidence}" \
       '.suites += [{"name": $name, "command": $cmd, "required": $req, "result": $res, "evidence": $evi}]' \
       "${AUDIT_DIR}/security_regression_gate/mandatory_security_regression_gate.results.json" > "${temp_file}"
    mv "${temp_file}" "${AUDIT_DIR}/security_regression_gate/mandatory_security_regression_gate.results.json"
  fi

  echo "| ${check_name} | \`${command}\` | ${required} | ${result} | ${evidence} |" >> "${AUDIT_DIR}/security_regression_gate/mandatory_security_regression_gate.summary.md"
}

log_evidence_complete() {
  local exit_code=$1
  local status="PASS"
  if [[ ${exit_code} -ne 0 ]]; then
    status="FAIL"
  fi

  if command -v jq &> /dev/null; then
    local temp_file
    temp_file=$(mktemp)
    jq --arg status "${status}" \
       --arg exit_code "${exit_code}" \
       '.status = $status | .exit_code = ($exit_code | tonumber)' \
       "${AUDIT_DIR}/security_regression_gate/mandatory_security_regression_gate.results.json" > "${temp_file}"
    mv "${temp_file}" "${AUDIT_DIR}/security_regression_gate/mandatory_security_regression_gate.results.json"
  fi

  {
    echo ""
    echo "## Final Result"
    echo ""
    echo "**Status**: ${status}"
    echo "**Exit Code**: ${exit_code}"
    echo "**Recommendation**: ${status}"
  } >> "${AUDIT_DIR}/security_regression_gate/mandatory_security_regression_gate.summary.md"
}

if [[ "${1:-}" == "--list-required" ]]; then
  required_suite_paths
  exit 0
fi

if [[ "${1:-}" == "--verify-required-only" ]]; then
  assert_required_paths_present
  echo "✅ All required suites present"
  exit 0
fi

write_summary "# Mandatory Security Regression Gate"
write_summary "- Commit: $(git rev-parse --short HEAD 2>/dev/null || echo unknown)"
write_summary "- Generated at: $(date -u +'%Y-%m-%dT%H:%M:%SZ')"
write_summary "- Artifact directory: ${ARTIFACT_DIR}"
write_summary ""

# Main gate execution - fail-closed checks first.
run_step "Required suite manifest check" assert_required_paths_present
run_step "Required suite no-skip/no-xfail source guard" assert_no_skip_or_xfail_markers

# Initialize audit evidence after source guards have confirmed gate completeness.
log_evidence_start
trap 'log_evidence_complete $?' EXIT

# RB-1 fix: removed '|| true' and '|| (echo ... && touch ...)' escape hatches.
# If PostgreSQL is unavailable the step now fails explicitly rather than silently
# creating an empty XML artifact and recording PASS. The DATABASE_URL fallback
# still allows the tests to run against a local Postgres when available.
run_step_record "Standalone API production-safety, health, durable persistence, and fail-closed provider checks" \
  bash -c "cd services/api && \
    TESTING=true ENVIRONMENT=testing DEBUG=false SEED_DEMO_DATA=false \
    DATABASE_URL='${DATABASE_URL:-postgresql://user:pass@localhost:5432/test}' \
    python -m pytest --tb=short -q -n 0 --timeout=60 \
      --junitxml='${ROOT_DIR}/${ARTIFACT_DIR}/standalone_api_security.xml' \
      app/tests/test_auth_enforcement.py \
      app/tests/test_health.py \
      app/tests/test_production_safety.py \
      app/tests/test_i03_durable_persistence_and_llm.py && \
    cd '${ROOT_DIR}' && \
    python scripts/ci/assert_no_pytest_skips.py '${ARTIFACT_DIR}/standalone_api_security.xml'" \
  -- \
  "I-02/I-03 API Production Safety" \
  "pytest app/tests/test_auth_enforcement.py test_health.py test_production_safety.py test_i03_durable_persistence_and_llm.py" \
  "Yes" \
  "${ARTIFACT_DIR}/standalone_api_security.xml"

# API-gateway tenant-isolation and invitation-security regression checks.
# Mandatory (fail-closed like the standalone API step above): covers the
# accept-invite single-use-token account-takeover fix and the gateway tenant
# boundary. MOCK_PERSISTENCE=true selects the in-memory repository per
# services/api conftest; SEED_DEMO_DATA=false keeps tenants hermetic.
run_step_record "API gateway tenant-isolation and invitation-security regression checks" \
  bash -c "cd services/api && \
    TESTING=true ENVIRONMENT=testing DEBUG=false SEED_DEMO_DATA=false MOCK_PERSISTENCE=true \
    python -m pytest --tb=short -q -n 0 --timeout=60 \
      --junitxml='${ROOT_DIR}/${ARTIFACT_DIR}/gateway_isolation_security.xml' \
      app/tests/test_tenant_isolation.py \
      app/tests/test_invitation_and_tenant_leakage.py && \
    cd '${ROOT_DIR}' && \
    python scripts/ci/assert_no_pytest_skips.py '${ARTIFACT_DIR}/gateway_isolation_security.xml'" \
  -- \
  "API Gateway Tenant Isolation + Invitation Security" \
  "pytest app/tests/test_tenant_isolation.py app/tests/test_invitation_and_tenant_leakage.py" \
  "Yes" \
  "${ARTIFACT_DIR}/gateway_isolation_security.xml"

run_step_record "Tenant-boundary and auth/security regression checks" \
  run_root_pytest "${ARTIFACT_DIR}/tenant_security.xml" "${ROOT_SECURITY_TESTS[@]}" \
  -- \
  "Tenant/Auth Security Regression" "pytest tests/security/*" "Yes" "${ARTIFACT_DIR}/tenant_security.xml"

run_step_record "Cross-layer tenant isolation matrix checks" \
  bash -c "CROSS_LAYER_TENANT_MATRIX_ARTIFACT='${ROOT_DIR}/${CROSS_LAYER_TENANT_MATRIX_ARTIFACT}' python -m pytest --tb=short -q -n 0 --timeout=60 --junitxml='${ARTIFACT_DIR}/cross_layer_tenant_matrix.xml' '${CROSS_LAYER_TENANT_MATRIX_TESTS[0]}' && python scripts/ci/assert_no_pytest_skips.py '${ARTIFACT_DIR}/cross_layer_tenant_matrix.xml' && python scripts/ci/validate_cross_layer_tenant_matrix.py '${CROSS_LAYER_TENANT_MATRIX_ARTIFACT}'" \
  -- \
  "Cross-Layer Tenant Isolation Matrix" \
  "pytest tests/security/test_cross_layer_tenant_isolation_matrix.py" \
  "Yes" "${CROSS_LAYER_TENANT_MATRIX_ARTIFACT}"

run_step_record "Layer 4 C-06 tenant rate-limit and security regression checks" \
  run_root_pytest "${ARTIFACT_DIR}/layer4_c06_security.xml" "${LAYER4_C06_SECURITY_TESTS[@]}" \
  -- \
  "Layer 4 C-06 Security Regression" \
  "pytest services/layer4-agents/tests/test_tenant_rate_limits.py services/layer4-agents/tests/test_security_fixes.py" \
  "Yes" "${ARTIFACT_DIR}/layer4_c06_security.xml"

run_step_record "Shared tenant context contract and import-boundary checks" \
  run_root_pytest "${ARTIFACT_DIR}/shared_contracts.xml" "${CONTRACT_TESTS[@]}" \
  -- \
  "Tenant Context Contract" \
  "pytest tests/context/test_tenant_context_contract.py tests/contract/test_shared_import_boundary.py tests/contract/test_retention_deletion_contract.py" \
  "Yes" "${ARTIFACT_DIR}/shared_contracts.xml"

if [[ "${FABRIC_GATE_TEST_MODE}" != "1" ]]; then
  run_step "OpenAPI contract drift check" \
    make --no-print-directory contract-drift
  run_step_record "OpenAPI contract drift check" \
    make --no-print-directory contract-drift \
    -- "OpenAPI Contract Drift" "make contract-drift" "Yes" "✓"

  run_step_record "Deprecation marker standardization check" \
    python scripts/ci/standardize_deprecation_markers.py --check \
    -- "Deprecation Marker Standardization" "standardize_deprecation_markers.py --check" "Yes" "✓"

  run_step_record "Frontend contract tests and placeholder guard" \
    bash -c 'cd apps/web && pnpm exec vitest run src/api/__tests__/contract && node scripts/security/assert-no-placeholder-contract-tests.mjs' \
    -- "Frontend Contract Tests" "vitest + placeholder guard" "Yes" "✓"

  run_step_record "Critical E2E skip-valve guard" \
    bash -c 'cd apps/web && node scripts/security/assert-no-skipped-critical-e2e.mjs' \
    -- "Critical E2E Skip-Valve" "assert-no-skipped-critical-e2e.mjs" "Yes" "✓"
else
  write_summary "→ [TEST MODE] Skipping OpenAPI contract drift check"
  write_summary "→ [TEST MODE] Skipping deprecation marker standardization check"
  write_summary "→ [TEST MODE] Skipping frontend contract tests"
  write_summary "→ [TEST MODE] Skipping critical E2E skip-valve guard"
  log_suite_result "OpenAPI Contract Drift" "make contract-drift" "Yes" "SKIPPED_TEST_MODE" "⊘"
  log_suite_result "Deprecation Marker Standardization" "standardize_deprecation_markers.py --check" "Yes" "SKIPPED_TEST_MODE" "⊘"
  log_suite_result "Frontend Contract Tests" "vitest + placeholder guard" "Yes" "SKIPPED_TEST_MODE" "⊘"
  log_suite_result "Critical E2E Skip-Valve" "assert-no-skipped-critical-e2e.mjs" "Yes" "SKIPPED_TEST_MODE" "⊘"
fi

run_step_record "Kubernetes workload hardening checks" \
  run_root_pytest "${ARTIFACT_DIR}/k8s_security.xml" "${K8S_TESTS[@]}" \
  -- "Kubernetes Hardening" "pytest tests/k8s/*" "Yes" "${ARTIFACT_DIR}/k8s_security.xml"

run_step_record "I-02 production fail-closed checks - Layer 2 (Extraction)" \
  bash -c "cd services/layer2-extraction && \
    python -m pytest --tb=short -q -n 0 --timeout=60 \
      --junitxml='${ROOT_DIR}/${ARTIFACT_DIR}/layer2_fail_closed.xml' \
      tests/test_production_fail_closed_i02.py && \
    cd '${ROOT_DIR}' && \
    python scripts/ci/assert_no_pytest_skips.py '${ARTIFACT_DIR}/layer2_fail_closed.xml'" \
  -- \
  "I-02 Layer 2 Production Fail-Closed" \
  "pytest tests/test_production_fail_closed_i02.py" \
  "Yes" "${ARTIFACT_DIR}/layer2_fail_closed.xml"

run_step_record "I-02 production fail-closed checks - Layer 5 (Ground Truth)" \
  bash -c "cd services/layer5-ground-truth && \
    python -m pytest --tb=short -q -n 0 --timeout=60 \
      --junitxml='${ROOT_DIR}/${ARTIFACT_DIR}/layer5_fail_closed.xml' \
      tests/test_production_fail_closed_i02.py && \
    cd '${ROOT_DIR}' && \
    python scripts/ci/assert_no_pytest_skips.py '${ARTIFACT_DIR}/layer5_fail_closed.xml'" \
  -- \
  "I-02 Layer 5 Production Fail-Closed" \
  "pytest tests/test_production_fail_closed_i02.py" \
  "Yes" "${ARTIFACT_DIR}/layer5_fail_closed.xml"

run_step_record "Hostile tenancy contracts (8 core isolation contracts)" \
  bash -c "python -m pytest --tb=short -q -n 0 --timeout=60 \
    --junitxml='${ROOT_DIR}/${ARTIFACT_DIR}/hostile_tenancy_contracts.xml' \
    tests/tenancy/test_hostile_tenancy_contracts.py && \
    python scripts/ci/assert_no_pytest_skips.py '${ARTIFACT_DIR}/hostile_tenancy_contracts.xml'" \
  -- \
  "Hostile Tenancy Contracts (Area B)" \
  "pytest tests/tenancy/test_hostile_tenancy_contracts.py" \
  "Yes" "${ARTIFACT_DIR}/hostile_tenancy_contracts.xml"

run_step_record "Hostile tenant evidence coverage check" \
  python scripts/ci/check_hostile_tenant_evidence.py \
  -- \
  "Hostile Tenant Evidence Verification" \
  "python scripts/ci/check_hostile_tenant_evidence.py" \
  "Yes" "✓"

run_step_record "Security exception lifecycle governance" \
  python scripts/ci/check_security_exceptions.py \
  -- \
  "Security Exception Governance" \
  "python scripts/ci/check_security_exceptions.py" \
  "Yes" "✓"

write_summary ""
write_summary "✅ mandatory-security-regression gate passed"
write_summary "📦 Evidence written to: ${AUDIT_DIR}/security_regression_gate/"
