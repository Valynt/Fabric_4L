# PostgreSQL Backup and Restore Runbook

This runbook is PostgreSQL-specific and separate from the Neo4j/Layer 3 graph backup procedures.

**Scope:** Value Fabric production PostgreSQL — logical backups via `pg_dump`  
**Owner:** Platform Engineering  
**Review cycle:** Quarterly  
**Last reviewed:** 2025-01-01

---

## Overview

Value Fabric uses `scripts/ops/postgres_backup.py` for scheduled logical backups.
The script:
- Runs `pg_dump` in plain-SQL format and gzip-compresses the output
- Optionally encrypts the archive with a Fernet symmetric key
- Uploads to a local path, S3 bucket, or GCS bucket
- Enforces retention by deleting objects older than `BACKUP_RETENTION_DAYS` (default 30 days)

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `POSTGRES_HOST` | yes | Database host (default: `localhost`) |
| `POSTGRES_PORT` | yes | Database port (default: `5432`) |
| `POSTGRES_USER` | yes | Database user |
| `POSTGRES_PASSWORD` | yes | Database password (passed as `PGPASSWORD`) |
| `POSTGRES_DB` | yes | Database name to back up |
| `BACKUP_STORAGE` | yes | `local`, `s3`, or `gcs` |
| `BACKUP_DEST` | yes | Local directory, S3 bucket name, or GCS bucket name |
| `BACKUP_PREFIX` | no | Object prefix inside the bucket (default: `postgres-backups`) |
| `BACKUP_ENCRYPTION_KEY` | recommended | 32-byte base64-URL Fernet key for at-rest encryption |
| `BACKUP_RETENTION_DAYS` | no | Days to keep backups (default: `30`) |

---

## Generating an Encryption Key

```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Store the key in Infisical under the path `production/postgres-backup/BACKUP_ENCRYPTION_KEY`.

---

## Running a Manual Backup

### Dry-run (print configuration, no side effects)

```bash
infisical run -- python3 scripts/ops/postgres_backup.py --dry-run
```

### Live backup

```bash
infisical run -- python3 scripts/ops/postgres_backup.py
```

### Logical backup/restore smoke drill

Run this before release candidates and at least quarterly. The drill starts two
isolated PostgreSQL containers, creates tenant-scoped sample data, runs
`scripts/ops/postgres_backup.py` with `pg_dump`, restores the artifact with
`psql`, and compares per-tenant checksums.

```bash
make db-production-readiness-gate
```

Evidence is written to `artifacts/postgres-backup-restore/`:

- `backup-artifact.sha256` — SHA-256 checksum of the logical backup artifact.
- `source-checksums.txt` — per-tenant source row counts and checksums.
- `restored-checksums.txt` — per-tenant restored row counts and checksums.
- `evidence.json` — image, database names, run ID, and evidence file paths.

The gate fails if any checksum differs or if the restored tenant count is not
exactly the expected source tenant count.

---

## Scheduled Backup via Kubernetes CronJob

Apply the manifest below to run daily at 02:00 UTC:

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: postgres-backup
  namespace: value-fabric
spec:
  schedule: "0 2 * * *"
  jobTemplate:
    spec:
      template:
        spec:
          restartPolicy: OnFailure
          containers:
          - name: backup
            image: python:3.11-slim
            command:
            - /bin/sh
            - -c
            - |
              pip install cryptography boto3 --quiet
              python3 /scripts/postgres_backup.py
            envFrom:
            - secretRef:
                name: postgres-backup-secrets
            volumeMounts:
            - name: scripts
              mountPath: /scripts
          volumes:
          - name: scripts
            configMap:
              name: postgres-backup-script
```

Store secrets (all variables listed above) in a Kubernetes Secret named
`postgres-backup-secrets`.

---

## Verify a Backup

1. Download the backup file from S3/GCS or the local directory.
2. If encrypted, decrypt:
   ```bash
   python3 - <<'EOF'
   import os
   from cryptography.fernet import Fernet
   key = os.environ["BACKUP_ENCRYPTION_KEY"].encode()
   f = Fernet(key)
   data = open("backup.sql.gz.enc", "rb").read()
   open("backup.sql.gz", "wb").write(f.decrypt(data))
   print("Decrypted OK")
   EOF
   ```
3. Decompress and inspect:
   ```bash
   gunzip -c backup.sql.gz | head -20
   ```

---

## Restore Procedure

> **IMPORTANT:** Restoring to a running database will overwrite existing data.
> Take a final backup of the target database before restoring.

### Restore to an existing database (drop + recreate)

```bash
# 1. Decrypt if encrypted
python3 -c "
import os; from cryptography.fernet import Fernet
f = Fernet(os.environ['BACKUP_ENCRYPTION_KEY'].encode())
open('backup.sql.gz', 'wb').write(f.decrypt(open('backup.sql.gz.enc', 'rb').read()))
"

# 2. Drop and recreate the target database
psql -h $POSTGRES_HOST -U $POSTGRES_USER -c "DROP DATABASE IF EXISTS value_fabric_restore;"
psql -h $POSTGRES_HOST -U $POSTGRES_USER -c "CREATE DATABASE value_fabric_restore;"

# 3. Restore
gunzip -c backup.sql.gz | psql -h $POSTGRES_HOST -U $POSTGRES_USER value_fabric_restore

# 4. Verify row counts
psql -h $POSTGRES_HOST -U $POSTGRES_USER value_fabric_restore \
  -c "SELECT tablename, n_live_tup FROM pg_stat_user_tables ORDER BY n_live_tup DESC LIMIT 20;"
```

### Restore to production (blue-green)

1. Restore into the standby cluster/database (see above).
2. Run application migrations: `make migrate`.
3. Smoke-test with `make test-backend-integrated-release-smoke`.
4. If healthy, flip the load balancer to the restored instance.
5. Keep the old instance available for 24 hours before decommissioning.

---

## Physical Backups and PITR Strategy

Logical `pg_dump` backups are the smoke-testable safety net and are suitable for
schema-level validation, tenant-integrity checks, and small emergency restores.
Production PostgreSQL should also use a physical backup and point-in-time
recovery (PITR) strategy:

### Managed PostgreSQL (recommended production posture)

Use the managed provider's native continuous backup feature as the physical/PITR
source of truth. Examples include AWS RDS/Aurora automated backups plus
point-in-time restore, Cloud SQL automated backups plus PITR, or Azure Database
for PostgreSQL automated backups plus PITR. Configure:

1. Continuous WAL archiving / transaction-log backup.
2. Cross-AZ or regional backup durability where available.
3. Backup retention that satisfies customer and compliance commitments.
4. Quarterly point-in-time restore drills into an isolated staging database.
5. Post-restore validation with `make migrate` and
   `make test-backend-integrated-release-smoke` before traffic cutover.

### Self-managed PostgreSQL

If production ever runs self-managed PostgreSQL, add `pg_basebackup` or an
equivalent base-backup tool plus continuous WAL archiving. Store base backups and
WAL segments in encrypted object storage with lifecycle retention. The restore
sequence is: restore the latest base backup, replay WAL to the target recovery
time, start PostgreSQL in recovery mode, then run the validation steps below.

Keep logical `pg_dump` drills even when physical/PITR is enabled; they provide a
fast contract check that tenant-scoped data can be backed up and restored
without relying on provider control-plane operations.

---

## RTO / RPO Targets

| Target | Value |
|---|---|
| RPO (max data loss) | 24 hours (daily backup) |
| RTO (max restore time) | 4 hours |

To improve RPO, enable WAL archiving in addition to this logical backup. See
`docs/troubleshooting/runbooks/infrastructure/postgres-down.md` for recovery
from a complete database failure.

---

## Retention Policy

| Tier | Retention |
|---|---|
| Daily logical backups | 30 days (enforced by `BACKUP_RETENTION_DAYS`) |
| WAL archives (when enabled) | 7 days |
| Pre-migration backups | 90 days (manual retention, tag with `pre-migration-YYYYMMDD`) |

---

## Alerting

The K8s CronJob emits a `Failed` event if the backup script exits non-zero.
Configure a `KubeJobFailed` alert in your Prometheus Alertmanager to page
on-call when the `postgres-backup` job fails.

---

## Related Runbooks

- [postgres-down](postgres-down.md)
- [postgres-unreachable](postgres-unreachable.md)
- [deployment-rollback](deployment-rollback.md)
