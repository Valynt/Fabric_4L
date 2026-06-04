#!/usr/bin/env bash
set -euo pipefail

# First-class tenant-isolation gate.
#
# This command is intentionally broader and more visible than the historical
# scattered tenant-boundary tests. It groups tenant-isolation failures by layer
# and control surface so PR/CI output shows whether the regression is in RLS,
# API context propagation, background jobs, graph operations, or cache keys.

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

# Required suites are grouped by layer/control surface for readable CI output.
# Every suite below is also selected by `pytest -m tenant_isolation` through
# explicit marks or the root conftest marker alias.
declare -a PLATFORM_API_TENANT_TESTS=(
  tests/security/test_tenant_boundary_fails_closed.py
  tests/security/test_cross_tenant_api.py
  tests/security/test_cross_tenant_write.py
  tests/security/test_tenant_mismatch.py
  tests/security/test_cross_layer_tenant_isolation_matrix.py
  tests/context/test_tenant_context_contract.py
)

declare -a POSTGRES_RLS_TENANT_TESTS=(
  services/layer1-ingestion/tests/security/test_rls_enforcement_postgres.py
  services/layer1-ingestion/tests/security/test_tenant_isolation_bypass_attempts_postgres.py
  services/layer1-ingestion/tests/security/test_crawl_decisions_tenant_isolation_postgres.py
)

declare -a BACKGROUND_JOB_TENANT_TESTS=(
  services/layer1-ingestion/tests/security/test_celery_tenant_isolation_postgres.py
)

declare -a KNOWLEDGE_GRAPH_TENANT_TESTS=(
  tests/security/test_neo4j_tenant_query_enforcement.py
  tests/security/test_neo4j_tenant_write_enforcement.py
  tests/security/test_neo4j_cross_tenant_write_isolation.py
  tests/security/test_graph_tenant_hostile_regression.py
  tests/layer3/test_endpoint_tenant_isolation.py
)

declare -a CACHE_TENANT_TESTS=(
  tests/cache/test_redis_tenant_isolation.py
  services/layer4-agents/tests/test_tenant_rate_limits.py
)

declare -a TENANT_ISOLATION_SUITES=(
  "${PLATFORM_API_TENANT_TESTS[@]}"
  "${POSTGRES_RLS_TENANT_TESTS[@]}"
  "${BACKGROUND_JOB_TENANT_TESTS[@]}"
  "${KNOWLEDGE_GRAPH_TENANT_TESTS[@]}"
  "${CACHE_TENANT_TESTS[@]}"
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

write_summary "# Tenant Isolation Gate"
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
write_summary "## Execution (grouped by layer/control surface)"
write_summary ""

run_pytest_suite \
  "Platform/API — cross-tenant read/write denial and tenant-context propagation" \
  "${JUNIT_DIR}/platform-api-tenant-isolation.xml" \
  "${PLATFORM_API_TENANT_TESTS[@]}"

run_pytest_suite \
  "Layer 1/PostgreSQL — RLS, SET LOCAL app.tenant_id, and database fail-closed behavior" \
  "${JUNIT_DIR}/layer1-postgres-rls-tenant-isolation.xml" \
  "${POSTGRES_RLS_TENANT_TESTS[@]}"

run_pytest_suite \
  "Layer 1 background jobs — tenant context propagation through Celery/job handlers" \
  "${JUNIT_DIR}/layer1-background-jobs-tenant-isolation.xml" \
  "${BACKGROUND_JOB_TENANT_TESTS[@]}"

run_pytest_suite \
  "Layer 3 knowledge graph — query/write tenant boundary enforcement" \
  "${JUNIT_DIR}/layer3-knowledge-graph-tenant-isolation.xml" \
  "${KNOWLEDGE_GRAPH_TENANT_TESTS[@]}"

run_pytest_suite \
  "Shared cache/rate limits — tenant-scoped cache keys and invalidation" \
  "${JUNIT_DIR}/cache-tenant-isolation.xml" \
  "${CACHE_TENANT_TESTS[@]}"

"${PYTHON_BIN}" scripts/ci/validate_cross_layer_tenant_matrix.py "${MATRIX_ARTIFACT}"
write_summary "✅ Cross-layer tenant isolation matrix artifact validated"
write_summary "  - Matrix: ${MATRIX_ARTIFACT}"
