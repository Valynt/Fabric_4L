#!/usr/bin/env bash
set -euo pipefail

# Dedicated launch-readiness gate for tenant isolation.
# This intentionally overlaps the tenant-specific portions of the broader
# mandatory security regression gate so release decisions have a visible,
# blocking tenant-isolation signal and artifact.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${ROOT_DIR}"

PYTHON_BIN="${PYTHON:-python3}"
ARTIFACT_DIR="${TENANT_ISOLATION_ARTIFACT_DIR:-artifacts/security}"
JUNIT_DIR="${ARTIFACT_DIR}/junit"
SUMMARY_FILE="${ARTIFACT_DIR}/tenant-isolation-summary.md"
MATRIX_ARTIFACT="${ARTIFACT_DIR}/cross_layer_tenant_isolation_matrix.json"

mkdir -p "${JUNIT_DIR}"
: > "${SUMMARY_FILE}"

export TESTING="${TESTING:-true}"
export ENVIRONMENT="${ENVIRONMENT:-testing}"
export DEBUG="false"
export LAYER4_LAYER5_API_URL="${LAYER4_LAYER5_API_URL:-http://localhost:8005}"
export PYTHONPATH="${ROOT_DIR}/packages/shared/src:${ROOT_DIR}:${PYTHONPATH:-}"
export CROSS_LAYER_TENANT_MATRIX_ARTIFACT="${ROOT_DIR}/${MATRIX_ARTIFACT}"

TENANT_ISOLATION_SUITES=(
  tests/security/test_tenant_boundary_fails_closed.py
  tests/security/test_cross_tenant_api.py
  tests/security/test_tenant_mismatch.py
  tests/security/test_cross_layer_tenant_isolation_matrix.py
  tests/context/test_tenant_context_contract.py
  services/layer4-agents/tests/test_tenant_rate_limits.py
)

write_summary() {
  printf '%s\n' "$*" | tee -a "${SUMMARY_FILE}"
}

finalize_summary() {
  local exit_code=$?
  local status="PASS"
  if [[ ${exit_code} -ne 0 ]]; then
    status="FAIL"
  fi

  {
    echo ""
    echo "## Final Result"
    echo ""
    echo "- **Status**: ${status}"
    echo "- **Exit Code**: ${exit_code}"
    echo "- **Generated at**: $(date -u +'%Y-%m-%dT%H:%M:%SZ')"
    echo "- **Artifact directory**: ${ARTIFACT_DIR}"
  } >> "${SUMMARY_FILE}"
}
trap finalize_summary EXIT

assert_path_present() {
  local path="$1"
  if [[ ! -e "${path}" ]]; then
    write_summary "❌ Missing required tenant isolation gate path: ${path}"
    exit 1
  fi
}

run_pytest_suite() {
  local label="$1"
  local junit_file="$2"
  local log_file="${junit_file%.xml}.log"
  local rc=0
  shift 2
  local cmd=("${PYTHON_BIN}" -m pytest --tb=short -q -n 0 --timeout=60 --junitxml="${junit_file}" "$@")

  write_summary "→ ${label}"
  write_summary "  - Command: \`${cmd[*]}\`"
  write_summary "  - Log: ${log_file}"
  "${cmd[@]}" 2>&1 | tee "${log_file}" || rc=$?
  if [[ ${rc} -ne 0 ]]; then
    write_summary "❌ ${label} failed during pytest execution (exit ${rc})"
    exit "${rc}"
  fi

  "${PYTHON_BIN}" scripts/ci/assert_no_pytest_skips.py "${junit_file}" 2>&1 | tee -a "${log_file}" || rc=$?
  if [[ ${rc} -ne 0 ]]; then
    write_summary "❌ ${label} failed skip/xfail enforcement (exit ${rc})"
    exit "${rc}"
  fi

  write_summary "✅ ${label}"
  write_summary "  - JUnit: ${junit_file}"
}

write_summary "# Tenant Isolation Readiness Gate"
write_summary ""
write_summary "- **Commit**: $(git rev-parse --short HEAD 2>/dev/null || echo unknown)"
write_summary "- **Generated at**: $(date -u +'%Y-%m-%dT%H:%M:%SZ')"
write_summary "- **Artifact directory**: ${ARTIFACT_DIR}"
write_summary "- **Cross-layer matrix artifact**: ${MATRIX_ARTIFACT}"
write_summary ""
write_summary "## Required Suites"
write_summary ""
for suite in "${TENANT_ISOLATION_SUITES[@]}"; do
  assert_path_present "${suite}"
  write_summary "- ${suite}"
done
write_summary ""
write_summary "## Execution"
write_summary ""

run_pytest_suite \
  "Tenant boundary fail-closed, cross-tenant API, and mismatch regression tests" \
  "${JUNIT_DIR}/tenant-boundary-api.xml" \
  tests/security/test_tenant_boundary_fails_closed.py \
  tests/security/test_cross_tenant_api.py \
  tests/security/test_tenant_mismatch.py

run_pytest_suite \
  "Tenant context contract tests" \
  "${JUNIT_DIR}/tenant-context-contract.xml" \
  tests/context/test_tenant_context_contract.py

run_pytest_suite \
  "Layer 4 tenant rate-limit isolation tests" \
  "${JUNIT_DIR}/layer4-tenant-rate-limits.xml" \
  services/layer4-agents/tests/test_tenant_rate_limits.py

run_pytest_suite \
  "Cross-layer tenant isolation matrix tests" \
  "${JUNIT_DIR}/cross-layer-tenant-isolation-matrix.xml" \
  tests/security/test_cross_layer_tenant_isolation_matrix.py

"${PYTHON_BIN}" scripts/ci/validate_cross_layer_tenant_matrix.py "${MATRIX_ARTIFACT}"
write_summary "✅ Cross-layer tenant isolation matrix artifact validated"
write_summary "  - Matrix: ${MATRIX_ARTIFACT}"
