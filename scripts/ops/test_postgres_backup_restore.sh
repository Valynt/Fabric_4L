#!/usr/bin/env bash
# PostgreSQL backup/restore production-readiness drill.
#
# The drill starts isolated source and restore PostgreSQL containers, creates
# tenant-scoped sample data, exercises scripts/ops/postgres_backup.py with
# pg_dump and psql, then compares per-tenant checksums after restore.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PYTHON_BIN="${PYTHON:-python3}"
POSTGRES_IMAGE="${POSTGRES_IMAGE:-postgres:15-alpine}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-vf_backup_restore_drill}"
SOURCE_DB="${POSTGRES_BACKUP_SOURCE_DB:-vf_source}"
RESTORE_DB="${POSTGRES_BACKUP_RESTORE_DB:-vf_restore}"
EVIDENCE_DIR="${POSTGRES_BACKUP_EVIDENCE_DIR:-$ROOT_DIR/artifacts/postgres-backup-restore}"
RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)-$$"
SOURCE_CONTAINER="vf-pg-backup-source-$RUN_ID"
RESTORE_CONTAINER="vf-pg-backup-restore-$RUN_ID"
NETWORK="vf-pg-backup-$RUN_ID"
TMP_DIR="$(mktemp -d)"
BACKUP_DEST="$TMP_DIR/backups"
WRAPPER_DIR="$TMP_DIR/bin"

cleanup() {
  docker rm -f "$SOURCE_CONTAINER" "$RESTORE_CONTAINER" >/dev/null 2>&1 || true
  docker network rm "$NETWORK" >/dev/null 2>&1 || true
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

require_command() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "ERROR: required command not found: $cmd" >&2
    exit 127
  fi
}

wait_for_postgres() {
  local container="$1"
  for _ in $(seq 1 60); do
    if docker exec "$container" pg_isready -U postgres >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done
  echo "ERROR: PostgreSQL did not become ready in $container" >&2
  docker logs "$container" >&2 || true
  return 1
}

psql_exec() {
  local container="$1"
  local database="$2"
  shift 2
  docker exec -i -e PGPASSWORD="$POSTGRES_PASSWORD" "$container" \
    psql --no-password -U postgres --dbname "$database" --set=ON_ERROR_STOP=1 "$@"
}

checksum_query() {
  cat <<'SQL'
SELECT tenant_id,
       count(*) AS row_count,
       md5(string_agg(account_id || ':' || payload || ':' || amount::text, ',' ORDER BY account_id)) AS tenant_checksum
FROM tenant_accounts
GROUP BY tenant_id
ORDER BY tenant_id;
SQL
}

require_command docker
require_command sha256sum
require_command sed
require_command mktemp
mkdir -p "$EVIDENCE_DIR" "$WRAPPER_DIR" "$BACKUP_DEST"

echo "→ Starting isolated PostgreSQL source and restore containers"
docker network create "$NETWORK" >/dev/null
docker run --rm -d --name "$SOURCE_CONTAINER" --network "$NETWORK" -e POSTGRES_PASSWORD="$POSTGRES_PASSWORD" "$POSTGRES_IMAGE" >/dev/null
docker run --rm -d --name "$RESTORE_CONTAINER" --network "$NETWORK" -e POSTGRES_PASSWORD="$POSTGRES_PASSWORD" "$POSTGRES_IMAGE" >/dev/null
wait_for_postgres "$SOURCE_CONTAINER"
wait_for_postgres "$RESTORE_CONTAINER"

cat > "$WRAPPER_DIR/pg_dump" <<'WRAP'
#!/usr/bin/env bash
exec docker run --rm --network __NETWORK__ -e PGPASSWORD="${PGPASSWORD:-}" postgres:15-alpine pg_dump "$@"
WRAP
cat > "$WRAPPER_DIR/psql" <<'WRAP'
#!/usr/bin/env bash
exec docker run --rm --network __NETWORK__ -e PGPASSWORD="${PGPASSWORD:-}" postgres:15-alpine psql "$@"
WRAP
chmod +x "$WRAPPER_DIR/pg_dump" "$WRAPPER_DIR/psql"

# Make the wrapper image match POSTGRES_IMAGE without interpolating secrets into command logs.
sed -i "s#__NETWORK__#$NETWORK#g; s#postgres:15-alpine#$POSTGRES_IMAGE#g" "$WRAPPER_DIR/pg_dump" "$WRAPPER_DIR/psql"

psql_exec "$SOURCE_CONTAINER" postgres --command "CREATE DATABASE $SOURCE_DB;"
psql_exec "$SOURCE_CONTAINER" "$SOURCE_DB" <<'SQL'
CREATE TABLE tenant_accounts (
  tenant_id text NOT NULL,
  account_id text NOT NULL,
  payload text NOT NULL,
  amount integer NOT NULL,
  PRIMARY KEY (tenant_id, account_id)
);
INSERT INTO tenant_accounts (tenant_id, account_id, payload, amount) VALUES
  ('tenant-a', 'acct-001', 'source-a-alpha', 101),
  ('tenant-a', 'acct-002', 'source-a-beta', 202),
  ('tenant-b', 'acct-001', 'source-b-alpha', 303),
  ('tenant-b', 'acct-002', 'source-b-beta', 404);
SQL

psql_exec "$SOURCE_CONTAINER" "$SOURCE_DB" --tuples-only --no-align --command "$(checksum_query)" > "$EVIDENCE_DIR/source-checksums.txt"

echo "→ Running pg_dump logical backup through scripts/ops/postgres_backup.py"
(
  cd "$ROOT_DIR"
  PATH="$WRAPPER_DIR:$PATH" \
  POSTGRES_HOST="$SOURCE_CONTAINER" \
  POSTGRES_PORT=5432 \
  POSTGRES_USER=postgres \
  POSTGRES_PASSWORD="$POSTGRES_PASSWORD" \
  POSTGRES_DB="$SOURCE_DB" \
  BACKUP_STORAGE=local \
  BACKUP_DEST="$BACKUP_DEST" \
  BACKUP_PREFIX=drill \
  BACKUP_RETENTION_DAYS=30 \
  "$PYTHON_BIN" scripts/ops/postgres_backup.py
)

BACKUP_FILE="$(find "$BACKUP_DEST" -type f -name '*.sql.gz' -print -quit)"
if [[ -z "$BACKUP_FILE" ]]; then
  echo "ERROR: no .sql.gz backup artifact was produced" >&2
  exit 1
fi
sha256sum "$BACKUP_FILE" > "$EVIDENCE_DIR/backup-artifact.sha256"

echo "→ Restoring backup into isolated PostgreSQL restore container"
(
  cd "$ROOT_DIR"
  PATH="$WRAPPER_DIR:$PATH" \
  POSTGRES_HOST="$RESTORE_CONTAINER" \
  POSTGRES_PORT=5432 \
  POSTGRES_USER=postgres \
  POSTGRES_PASSWORD="$POSTGRES_PASSWORD" \
  "$PYTHON_BIN" scripts/ops/postgres_backup.py --restore "$BACKUP_FILE" --target-db "$RESTORE_DB" --clean
)

psql_exec "$RESTORE_CONTAINER" "$RESTORE_DB" --tuples-only --no-align --command "$(checksum_query)" > "$EVIDENCE_DIR/restored-checksums.txt"

diff -u "$EVIDENCE_DIR/source-checksums.txt" "$EVIDENCE_DIR/restored-checksums.txt"
EXPECTED_TENANT_COUNT="2"
ACTUAL_TENANT_COUNT="$(psql_exec "$RESTORE_CONTAINER" "$RESTORE_DB" --tuples-only --no-align --command "SELECT count(DISTINCT tenant_id) FROM tenant_accounts;")"
if [[ "$ACTUAL_TENANT_COUNT" != "$EXPECTED_TENANT_COUNT" ]]; then
  echo "ERROR: expected $EXPECTED_TENANT_COUNT tenants after restore, found $ACTUAL_TENANT_COUNT" >&2
  exit 1
fi

cat > "$EVIDENCE_DIR/evidence.json" <<JSON
{
  "run_id": "$RUN_ID",
  "source_database": "$SOURCE_DB",
  "restore_database": "$RESTORE_DB",
  "postgres_image": "$POSTGRES_IMAGE",
  "backup_sha256_file": "$EVIDENCE_DIR/backup-artifact.sha256",
  "source_checksums": "$EVIDENCE_DIR/source-checksums.txt",
  "restored_checksums": "$EVIDENCE_DIR/restored-checksums.txt",
  "tenant_count_verified": $ACTUAL_TENANT_COUNT
}
JSON

echo "✅ PostgreSQL backup/restore drill passed. Evidence: $EVIDENCE_DIR"
