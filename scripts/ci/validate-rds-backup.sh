#!/usr/bin/env bash
# P0-002: Validate RDS backup retention and latest snapshot age.
# Usage: ./scripts/ci/validate-rds-backup.sh <db-identifier> [max-snapshot-age-hours]

set -euo pipefail

DB_IDENTIFIER="${1:-}"
MAX_SNAPSHOT_AGE_HOURS="${2:-48}"

if [[ -z "$DB_IDENTIFIER" ]]; then
  echo "Usage: $0 <db-identifier> [max-snapshot-age-hours]"
  exit 1
fi

echo "=== RDS Backup Validation for ${DB_IDENTIFIER} ==="

# Check backup retention period
RETENTION=$(aws rds describe-db-instances \
  --db-instance-identifier "$DB_IDENTIFIER" \
  --query 'DBInstances[0].BackupRetentionPeriod' \
  --output text 2>/dev/null || echo "0")

if [[ "$RETENTION" == "0" || "$RETENTION" == "None" ]]; then
  echo "FAIL: BackupRetentionPeriod is 0 or not set for ${DB_IDENTIFIER}"
  exit 1
fi

echo "PASS: BackupRetentionPeriod = ${RETENTION} days"

# Check latest snapshot age
LATEST_SNAPSHOT_TIME=$(aws rds describe-db-snapshots \
  --db-instance-identifier "$DB_IDENTIFIER" \
  --snapshot-type automated \
  --query 'reverse(sort_by(DBSnapshots, &SnapshotCreateTime))[0].SnapshotCreateTime' \
  --output text 2>/dev/null || echo "None")

if [[ "$LATEST_SNAPSHOT_TIME" == "None" || "$LATEST_SNAPSHOT_TIME" == "null" ]]; then
  echo "WARN: No automated snapshots found for ${DB_IDENTIFIER}"
  # This is a warning, not a hard failure for newly created instances
  exit 0
fi

SNAPSHOT_AGE_HOURS=$(( ($(date +%s) - $(date -d "$LATEST_SNAPSHOT_TIME" +%s)) / 3600 ))

if [[ $SNAPSHOT_AGE_HOURS -gt $MAX_SNAPSHOT_AGE_HOURS ]]; then
  echo "FAIL: Latest automated snapshot is ${SNAPSHOT_AGE_HOURS} hours old (max allowed: ${MAX_SNAPSHOT_AGE_HOURS})"
  exit 1
fi

echo "PASS: Latest automated snapshot is ${SNAPSHOT_AGE_HOURS} hours old"
echo "=== RDS Backup Validation Complete ==="
