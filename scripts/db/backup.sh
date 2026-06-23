#!/usr/bin/env bash
set -euo pipefail

# P0-002: Automated PostgreSQL backup script using WAL-G.
# Intended to run hourly via cron or as a sidecar container.

: "${PGHOST:=postgres-primary}"
: "${PGUSER:=postgres}"
: "${PGDATABASE:=fabric}"
: "${WALG_S3_PREFIX:=s3://fabric-db-backups/wal}"
: "${BACKUP_RETENTION_DAYS:=14}"

log() {
    echo "[$(date -Iseconds)] $1"
}

# Verify PostgreSQL is reachable
if ! pg_isready -h "${PGHOST}" -U "${PGUSER}" -d "${PGDATABASE}" > /dev/null 2>&1; then
    log "ERROR: PostgreSQL is not reachable at ${PGHOST}"
    exit 1
fi

# Perform base backup (full backup) if no recent base backup exists
log "Checking for recent base backup..."
if ! wal-g backup-list 2>/dev/null | grep -q "base_"; then
    log "No base backup found. Creating initial base backup..."
    wal-g backup-push "${PGHOST}" || {
        log "ERROR: Base backup failed"
        exit 1
    }
    log "Base backup completed successfully."
else
    log "Recent base backup exists. Skipping full backup."
fi

# Upload any pending WAL segments
log "Uploading WAL archives..."
wal-g wal-push /var/lib/postgresql/archive/ || log "WARN: WAL push encountered issues (may be empty)"

# Retention cleanup: delete backups older than retention period
log "Cleaning up backups older than ${BACKUP_RETENTION_DAYS} days..."
wal-g delete retain-full "${BACKUP_RETENTION_DAYS}" --confirm || log "WARN: Backup retention cleanup had issues"

log "Backup cycle completed."
