# Restore Postgres From Backup Runbook

## Scope

Use this runbook to restore Value Fabric PostgreSQL data from a verified backup. It adapts the existing PostgreSQL backup/restore material and the backup disaster recovery objectives into the canonical Phase 1 database recovery path.

## Severity

- **SEV1:** Restore is required because of data loss, corruption, security incident, or production database unavailable with customer impact.
- **SEV2:** Restore is required for a bounded dataset, failed migration recovery, or degraded production function with workaround.
- **SEV3:** Non-production restore drill or isolated validation restore.

## Immediate Actions

1. Activate Incident Command for production restores and declare restore objective: full restore, point-in-time restore, tenant-scoped recovery, or validation-only restore.
2. Freeze writes, queue consumers, scheduled jobs, and downstream workflows that could amplify corruption or overwrite recovery state.
3. Preserve evidence and take a final snapshot/backup of the current target before any destructive action.
4. Identify the latest successful full backup and any incremental/WAL chain needed to meet RPO.
5. Verify checksum, encryption key availability, and restore target isolation before touching production.
6. Restore into a standby or recovery database first; do not overwrite the active production database until validation passes.
7. Coordinate cutover and post-restore monitoring with service owners.

## Procedure

```bash
# 1. Run a final manual backup/snapshot of the current target when safe.
infisical run -- python3 scripts/ops/postgres_backup.py

# 2. Decrypt an encrypted backup if needed.
python3 - <<'PY'
import os
from cryptography.fernet import Fernet
key = os.environ["BACKUP_ENCRYPTION_KEY"].encode()
f = Fernet(key)
open("backup.sql.gz", "wb").write(f.decrypt(open("backup.sql.gz.enc", "rb").read()))
print("Decrypted OK")
PY

# 3. Inspect the backup before restore.
gunzip -c backup.sql.gz | head -20

# 4. Create an isolated restore database.
psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -c "DROP DATABASE IF EXISTS value_fabric_restore;"
psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -c "CREATE DATABASE value_fabric_restore;"

# 5. Restore into the isolated database.
gunzip -c backup.sql.gz | psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" value_fabric_restore

# 6. Verify row counts and core tables.
psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" value_fabric_restore \
  -c "SELECT tablename, n_live_tup FROM pg_stat_user_tables ORDER BY n_live_tup DESC LIMIT 20;"
```

For production cutover, restore to a standby cluster/database, run required migrations, execute smoke tests, then flip traffic to the restored instance. Keep the old instance available for at least 24 hours unless Security or Legal requires longer retention.

## Validation

- Backup checksum and metadata match the selected restore artifact.
- Restore completed into an isolated target without SQL errors.
- Core table counts, tenant-scoped sample queries, and application health checks match expected recovery point.
- Migrations are at the expected version and `make check-migration-heads` passes when applicable.
- Backend release smoke passes before production cutover.
- Post-cutover dashboards show normal database connections, query latency, error rate, and queue processing.

## Evidence to Preserve

- Backup object URI/path, timestamp, checksum, encryption status, and retention tag.
- Restore target name, operator, commands, start/end timestamps, and restore logs.
- Final pre-restore snapshot reference.
- Row-count validation, tenant sample query results, and application smoke output.
- Cutover decision record and any data-loss/RPO assessment.

## Related Gates

- `make check-migration-heads`
- `make migrate`
- `make test-backend-integrated-release-smoke`
- `make contract-tests`
- `make verify`

## Related Runbooks

- [Incident Command](../01-incident-command.md)
- [Failed Migration](failed-migration.md)
- [Rollback Production Release](../deployment/rollback-production-release.md)
- [Respond to Tenant Data Exposure](../security/respond-to-tenant-data-exposure.md)
- [Alert Triage](../observability/alert-triage.md)
