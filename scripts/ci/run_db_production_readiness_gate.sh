#!/usr/bin/env bash
# Run the production-like database readiness gate.
#
# The gate is intentionally fail-closed: every migration, rollback, drift,
# tenant-isolation, backup/restore, cross-store, credential, and observability
# evidence step must pass before release policy can print SHIP.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
COMPOSE_FILE="${DB_READINESS_COMPOSE_FILE:-docker-compose.db-readiness.yml}"
PROJECT_NAME="${DB_READINESS_PROJECT_NAME:-fabric-db-readiness}"
ARTIFACT_DIR="${DB_READINESS_ARTIFACT_DIR:-${ROOT}/artifacts/release/db-readiness}"
PYTHON_BIN="${PYTHON:-python3}"
PYTEST_CMD=("${PYTHON_BIN}" -m pytest -v --tb=short -n 0)
COMPOSE=(docker compose -p "${PROJECT_NAME}" -f "${COMPOSE_FILE}")

mkdir -p "${ARTIFACT_DIR}"
cd "${ROOT}"

cleanup() {
  if [ "${DB_READINESS_KEEP_STACK:-0}" = "1" ]; then
    echo "DB_READINESS_KEEP_STACK=1 set; leaving ${PROJECT_NAME} running"
    return
  fi
  "${COMPOSE[@]}" down -v --remove-orphans >/dev/null 2>&1 || true
}
trap cleanup EXIT

run_step() {
  local name="$1"
  shift
  echo "→ [db-readiness] ${name}"
  "$@"
}

postgres_exec() {
  "${COMPOSE[@]}" exec -T postgres "$@"
}

psql_db() {
  local db="$1"
  shift
  postgres_exec env PGPASSWORD=vf_migrator_readiness_secret psql -h 127.0.0.1 -v ON_ERROR_STOP=1 -U vf_migrator -d "${db}" "$@"
}

run_alembic() {
  local label="$1"
  local service_dir="$2"
  shift 2
  echo "   ↳ ${label}: alembic $*"
  (cd "${service_dir}" && alembic "$@")
}

run_alembic_check() {
  local label="$1"
  local service_dir="$2"
  echo "   ↳ ${label}: alembic check"
  (cd "${service_dir}" && alembic check)
}

run_api_alembic() {
  local cmd="$1"
  shift
  echo "   ↳ API: alembic ${cmd} $*"
  (cd services/api && alembic -c migrations/alembic.ini "${cmd}" "$@")
}

run_keyword_pytest() {
  local label="$1"
  shift
  echo "   ↳ pytest ${label}: $*"
  "${PYTEST_CMD[@]}" "$@"
}


wait_for_http() {
  local label="$1"
  local url="$2"
  "${PYTHON_BIN}" - "$label" "$url" <<'PYWAIT'
import sys
import time
import urllib.request

label, url = sys.argv[1], sys.argv[2]
last_error = None
for _ in range(30):
    try:
        with urllib.request.urlopen(url, timeout=3) as response:
            if response.status < 500:
                print(f"{label} ready: {url} -> HTTP {response.status}")
                raise SystemExit(0)
    except Exception as exc:  # noqa: BLE001 - gate diagnostics need the final exception text
        last_error = exc
        time.sleep(2)
print(f"{label} did not become ready at {url}: {last_error}", file=sys.stderr)
raise SystemExit(1)
PYWAIT
}

export ENVIRONMENT="${ENVIRONMENT:-staging}"
export JWT_SECRET="${JWT_SECRET:-vf-db-readiness-jwt-secret-minimum-32-chars}"
export SERVICE_AUTH_SECRET="${SERVICE_AUTH_SECRET:-vf-db-readiness-service-auth-secret-minimum-32-chars}"
export CORS_ORIGINS="${CORS_ORIGINS:-https://readiness.local}"
export REDIS_URL="${REDIS_URL:-redis://:vf_redis_readiness_secret@127.0.0.1:56379/0}"
export NEO4J_URI="${NEO4J_URI:-bolt://127.0.0.1:57687}"
export NEO4J_USER="${NEO4J_USER:-neo4j}"
export NEO4J_PASSWORD="${NEO4J_PASSWORD:-vf_neo4j_readiness_secret}"
export QDRANT_URL="${QDRANT_URL:-http://127.0.0.1:56333}"
export S3_ENDPOINT_URL="${S3_ENDPOINT_URL:-http://127.0.0.1:59000}"
export AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID:-vf_minio_readiness}"
export AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY:-vf_minio_readiness_secret_32_chars}"
export AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-us-east-1}"

SYNC_BASE="postgresql://vf_migrator:vf_migrator_readiness_secret@127.0.0.1:55432"
ASYNC_BASE="postgresql+asyncpg://vf_migrator:vf_migrator_readiness_secret@127.0.0.1:55432"
export LAYER1_DATABASE_URL="${SYNC_BASE}/layer1_ingestion_readiness"
export LAYER2_DATABASE_URL="${ASYNC_BASE}/layer2_extraction_readiness"
export LAYER25_DATABASE_URL="${SYNC_BASE}/signal_refinery_readiness"
export LAYER4_DATABASE_URL="${SYNC_BASE}/layer4_agents_readiness"
export CHECKPOINT_DATABASE_URL="${SYNC_BASE}/layer4_agents_readiness"
export LAYER5_DATABASE_URL_SYNC="${SYNC_BASE}/ground_truth_readiness"
export API_DATABASE_URL_SYNC="${SYNC_BASE}/api_readiness"

run_step "bootstrap production-like DB/readiness stack" "${COMPOSE[@]}" up -d --wait
run_step "verify Qdrant readiness" wait_for_http Qdrant "${QDRANT_URL}/"
run_step "verify MinIO readiness" wait_for_http MinIO "${S3_ENDPOINT_URL}/minio/health/live"
run_step "verify Alertmanager readiness" wait_for_http Alertmanager "http://127.0.0.1:59093/-/ready"
run_step "verify PostgreSQL database inventory" psql_db fabric_readiness -c "SELECT datname FROM pg_database WHERE datname LIKE '%readiness%' ORDER BY datname;"

run_step "DB credential and role safety checks" psql_db fabric_readiness -c "SELECT rolname, rolsuper, rolcreaterole, rolcreatedb FROM pg_roles WHERE rolname = 'vf_migrator';"
if psql_db fabric_readiness -Atc "SELECT rolsuper OR rolcreaterole FROM pg_roles WHERE rolname = 'vf_migrator';" | grep -q t; then
  echo "❌ vf_migrator must not be superuser or role-admin in the readiness stack"
  exit 1
fi
if env | grep -E 'DATABASE_URL|LAYER[0-9_]*_DATABASE_URL|API_DATABASE_URL' | grep -E 'postgres:postgres|password|changeme' >/dev/null; then
  echo "❌ database readiness environment contains default or placeholder DB credentials"
  exit 1
fi
run_step "static credential scan" "${PYTHON_BIN}" scripts/ci/check_hardcoded_credentials.py

run_step "Layer 1 Alembic upgrade/rollback/drift" bash -c "cd '${ROOT}' && export DATABASE_URL='${LAYER1_DATABASE_URL}' && cd services/layer1-ingestion && alembic upgrade head && alembic downgrade -1 && alembic upgrade head && alembic check"

run_step "Layer 2 Alembic upgrade/rollback/drift" bash -c "cd '${ROOT}' && export DATABASE_URL='${LAYER2_DATABASE_URL}' && cd services/layer2-extraction && alembic upgrade head && alembic downgrade -1 && alembic upgrade head && alembic check"

run_step "Layer 2.5 Alembic upgrade/rollback/drift" bash -c "cd '${ROOT}' && export DATABASE_URL='${LAYER25_DATABASE_URL}' && cd services/layer2-5-signal-refinery && alembic upgrade head && alembic downgrade -1 && alembic upgrade head && alembic check"

run_step "Layer 4 Alembic upgrade/rollback/drift" bash -c "cd '${ROOT}' && cd services/layer4-agents && alembic upgrade head && alembic downgrade -1 && alembic upgrade head && alembic check"

run_step "Layer 5 Alembic upgrade/rollback/drift" bash -c "cd '${ROOT}' && export DATABASE_URL_SYNC='${LAYER5_DATABASE_URL_SYNC}' && cd services/layer5-ground-truth && alembic upgrade head && alembic downgrade -1 && alembic upgrade head && alembic check"

run_step "API Alembic upgrade/rollback" bash -c "cd '${ROOT}' && export DATABASE_URL_SYNC='${API_DATABASE_URL_SYNC}' && cd services/api && alembic -c migrations/alembic.ini upgrade head && alembic -c migrations/alembic.ini downgrade -1 && alembic -c migrations/alembic.ini upgrade head"

run_step "migration static graph and safety checks" "${PYTHON_BIN}" scripts/ci/check_migration_entrypoints.py
run_step "migration destructive-change safety scan" "${PYTHON_BIN}" scripts/ci/check_migration_safety.py --strict --use-baseline

run_step "PostgreSQL backup/restore smoke" postgres_exec env PGPASSWORD=vf_migrator_readiness_secret pg_dump -h 127.0.0.1 -U vf_migrator -d layer4_agents_readiness -f /tmp/fabric_readiness_backup.sql
psql_db postgres_restore_readiness -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
postgres_exec env PGPASSWORD=vf_migrator_readiness_secret psql -h 127.0.0.1 -v ON_ERROR_STOP=1 -U vf_migrator -d postgres_restore_readiness -f /tmp/fabric_readiness_backup.sql
psql_db postgres_restore_readiness -c "SELECT COUNT(*) AS restored_tables FROM information_schema.tables WHERE table_schema = 'public';"

run_step "tenant-isolation suites under tests/security and tests/integration" run_keyword_pytest \
  "tenant isolation" \
  tests/security tests/integration \
  -k "tenant or isolation or rls or postgres or cross_tenant" \
  --junitxml="${ARTIFACT_DIR}/tenant-isolation.xml"

run_step "service-local Postgres-backed security tests" run_keyword_pytest \
  "service-local postgres security" \
  services/api/app/tests/test_database_tenant_boundary.py \
  services/api/app/tests/test_postgresql_database.py \
  services/api/app/tests/test_tenant_isolation.py \
  services/layer2-5-signal-refinery/tests/test_tenant_isolation.py \
  -k "tenant or isolation or postgres or database" \
  --junitxml="${ARTIFACT_DIR}/service-postgres-security.xml"

run_step "cross-store projection/replay tests for derived data" run_keyword_pytest \
  "cross-store projection replay" \
  tests/contract tests/security services/layer3-knowledge/tests services/layer4-agents/tests \
  -k "projection or replay or vector or neo4j or object_store or objectstore or minio or s3" \
  --junitxml="${ARTIFACT_DIR}/cross-store-projection-replay.xml"

run_step "observability and backup alert evidence checks" "${PYTHON_BIN}" scripts/ci/check_production_alert_metadata.py
run_step "observability deployment readiness evidence" "${PYTEST_CMD[@]}" tests/release/test_observability_deployment_readiness.py --junitxml="${ARTIFACT_DIR}/observability-evidence.xml"
run_step "backup manager smoke coverage" "${PYTEST_CMD[@]}" services/layer3-knowledge/tests/test_backup_manager.py --junitxml="${ARTIFACT_DIR}/backup-manager.xml"

cat > "${ARTIFACT_DIR}/db-production-readiness-summary.md" <<SUMMARY
# DB Production Readiness Gate

- Stack: ${COMPOSE_FILE} / project ${PROJECT_NAME}
- PostgreSQL migrations: Layer 1, Layer 2, Layer 2.5, Layer 4, Layer 5, API
- Rollback smoke: alembic downgrade -1 then upgrade head per migration owner
- Drift checks: alembic check plus migration entrypoint/safety scans
- Tenant isolation: tests/security, tests/integration, service-local PostgreSQL security tests
- Backup/restore: pg_dump restore smoke and Layer 3 backup manager tests
- Cross-store replay/projection: Neo4j/vector/object-store keyword suite
- Credential/role safety: non-default DSNs, non-superuser role assertion, hardcoded credential scan
- Observability: production alert metadata and readiness evidence checks
SUMMARY

echo "✅ gate-database-live database readiness script passed"
