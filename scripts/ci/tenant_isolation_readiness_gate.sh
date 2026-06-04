#!/usr/bin/env bash
set -euo pipefail

# Dedicated launch-readiness gate for tenant isolation.
#
# This is the first-class repository gate behind `pnpm test:isolation`. It
# intentionally overlaps tenant-specific portions of the broader security suite
# while grouping results by layer and boundary type so failures are immediately
# actionable. Skips/xfails are rejected for every suite: tenant isolation must
# fail closed, not silently degrade when dependencies or fixtures drift.

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
export PYTHONPATH="${ROOT_DIR}/packages/shared/src:${ROOT_DIR}/packages/platform-contract/src/python:${ROOT_DIR}:${PYTHONPATH:-}"
export CROSS_LAYER_TENANT_MATRIX_ARTIFACT="${ROOT_DIR}/${MATRIX_ARTIFACT}"

TENANT_ISOLATION_SUITES=(
  # PostgreSQL RLS and background job tenant context (Layer 1)
  services/layer1-ingestion/tests/security/test_rls_enforcement_postgres.py
  services/layer1-ingestion/tests/security/test_celery_tenant_isolation_postgres.py
  services/layer1-ingestion/tests/security/test_require_tenant_false_allowlist_postgres.py

  # Cross-tenant read/write denial and fail-closed boundaries (cross-layer)
  tests/security/test_tenant_boundary_fails_closed.py
  tests/security/test_cross_tenant_api.py
  tests/security/test_cross_tenant_write.py
  tests/security/test_tenant_mismatch.py

  # API tenant-context propagation (L1-L6)
  tests/context/test_tenant_context_contract.py
  services/layer1-ingestion/tests/test_api_tenant_propagation.py
  services/layer2-extraction/tests/test_api_tenant_propagation.py
  services/layer3-knowledge/tests/test_api_tenant_propagation.py
  services/layer4-agents/tests/test_api_tenant_propagation.py
  services/layer5-ground-truth/tests/test_api_tenant_propagation.py
  services/layer6-benchmarks/tests/test_api_tenant_propagation.py

  # Knowledge graph tenant boundaries (Layer 3)
  tests/security/test_cross_layer_tenant_isolation_matrix.py
  services/layer3-knowledge/tests/test_tenant_isolation_static.py
  services/layer3-knowledge/tests/test_tenant_read_isolation.py
  services/layer3-knowledge/tests/test_vector_store_tenant_write_isolation.py

  # Cache-key tenant isolation (shared cache + API key/session cache)
  tests/cache/test_redis_tenant_isolation.py
  tests/shared/identity/test_api_key_cache.py

  # Layer-owned hostile-access regressions and rate limits
  services/layer2-extraction/tests/test_cross_tenant_hostile.py
  services/layer3-knowledge/tests/test_cross_tenant_hostile.py
  services/layer4-agents/tests/test_cross_tenant_hostile.py
  services/layer4-agents/tests/test_tenant_rate_limits.py
  services/layer5-ground-truth/tests/test_cross_tenant_hostile.py
  services/layer6-benchmarks/tests/test_cross_tenant_hostile.py
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
write_summary "## Boundary Coverage"
write_summary ""
write_summary "- PostgreSQL RLS tests"
write_summary "- Cross-tenant read/write denial tests"
write_summary "- API tenant-context propagation tests"
write_summary "- Background job tenant-context tests"
write_summary "- Knowledge graph tenant boundary tests"
write_summary "- Cache-key tenant isolation tests"
write_summary ""
write_summary "## Execution"
write_summary ""

run_pytest_suite \
  "Layer 1 — PostgreSQL RLS and background job tenant context" \
  "${JUNIT_DIR}/layer1-postgres-rls-and-jobs.xml" \
  services/layer1-ingestion/tests/security/test_rls_enforcement_postgres.py \
  services/layer1-ingestion/tests/security/test_celery_tenant_isolation_postgres.py \
  services/layer1-ingestion/tests/security/test_require_tenant_false_allowlist_postgres.py

run_pytest_suite \
  "Cross-layer — read/write denial, fail-closed, and mismatch regressions" \
  "${JUNIT_DIR}/cross-layer-read-write-denial.xml" \
  tests/security/test_tenant_boundary_fails_closed.py \
  tests/security/test_cross_tenant_api.py \
  tests/security/test_cross_tenant_write.py \
  tests/security/test_tenant_mismatch.py

run_pytest_suite \
  "L1-L6 — API tenant-context propagation" \
  "${JUNIT_DIR}/api-tenant-context-propagation.xml" \
  tests/context/test_tenant_context_contract.py \
  services/layer1-ingestion/tests/test_api_tenant_propagation.py \
  services/layer2-extraction/tests/test_api_tenant_propagation.py \
  services/layer3-knowledge/tests/test_api_tenant_propagation.py \
  services/layer4-agents/tests/test_api_tenant_propagation.py \
  services/layer5-ground-truth/tests/test_api_tenant_propagation.py \
  services/layer6-benchmarks/tests/test_api_tenant_propagation.py

run_pytest_suite \
  "Layer 3 — knowledge graph tenant boundaries" \
  "${JUNIT_DIR}/layer3-knowledge-graph-boundaries.xml" \
  tests/security/test_cross_layer_tenant_isolation_matrix.py \
  services/layer3-knowledge/tests/test_tenant_isolation_static.py \
  services/layer3-knowledge/tests/test_tenant_read_isolation.py \
  services/layer3-knowledge/tests/test_vector_store_tenant_write_isolation.py

"${PYTHON_BIN}" scripts/ci/validate_cross_layer_tenant_matrix.py "${MATRIX_ARTIFACT}"
write_summary "✅ Cross-layer tenant isolation matrix artifact validated"
write_summary "  - Matrix: ${MATRIX_ARTIFACT}"

run_pytest_suite \
  "Shared/cache — cache-key tenant isolation" \
  "${JUNIT_DIR}/shared-cache-key-isolation.xml" \
  tests/cache/test_redis_tenant_isolation.py \
  tests/shared/identity/test_api_key_cache.py

run_pytest_suite \
  "Layer-owned hostile-access regressions and tenant rate limits" \
  "${JUNIT_DIR}/layer-owned-hostile-access.xml" \
  services/layer2-extraction/tests/test_cross_tenant_hostile.py \
  services/layer3-knowledge/tests/test_cross_tenant_hostile.py \
  services/layer4-agents/tests/test_cross_tenant_hostile.py \
  services/layer4-agents/tests/test_tenant_rate_limits.py \
  services/layer5-ground-truth/tests/test_cross_tenant_hostile.py \
  services/layer6-benchmarks/tests/test_cross_tenant_hostile.py
