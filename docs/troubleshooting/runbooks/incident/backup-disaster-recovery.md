# Backup and Disaster Recovery Runbook

## RTO/RPO Targets

| Metric | Target | Maximum |
|--------|--------|---------|
| **RTO** (Recovery Time Objective) | 4 hours | 8 hours |
| **RPO** (Recovery Point Objective) | 1 hour | 4 hours |

These are platform DR targets for live customer data. Daily logical backups are
the portable safety net, but production must also use managed PostgreSQL
point-in-time recovery or equivalent WAL archiving to meet the 1-hour RPO target.

---

## Backup Strategy

### Types of Backups

1. **Full Backups** - Complete dataset snapshot
   - Schedule: Daily at 02:00 UTC
   - Retention: 30 days
   - Storage: Primary (S3) + Cross-region replica

2. **Incremental Backups** - Changed data since last backup
   - Schedule: Every 4 hours
   - Retention: 7 days
   - Storage: Primary (S3)

3. **Configuration Backups** - Schema and settings
   - Schedule: On every schema migration
   - Retention: 90 days
   - Storage: Version-controlled + S3

---

## Runbook Steps

### 1. Verify Backup Health (Daily)

```bash
# Run backup drill (dry-run restore)
make test-backup-drills

# Check last backup status
python -c "from layer3_knowledge.backup import BackupManager; bm = BackupManager(); print(bm.get_backup_info())"
```

**Evidence required:**
- Last backup checksum verified
- Backup age < 25 hours for full backups
- No failed backup alerts in monitoring

---

### 2. Point-in-Time Restore (PITR)

When data corruption or accidental deletion occurs:

```python
from datetime import datetime, timezone
from layer3_knowledge.backup import BackupManager, RestoreRequest

bm = BackupManager()

# Restore to specific point in time
request = RestoreRequest(
    point_in_time=datetime(2026, 4, 14, 10, 30, tzinfo=timezone.utc),
    verify_checksum=True,
    dry_run=False
)

result = bm.restore_backup(request)
print(f"Restore result: {result.status}")
print(f"Warnings: {result.warnings}")
```

**Steps:**
1. Identify target restore time (before corruption occurred)
2. Run PITR in `dry_run=True` mode first to validate
3. If dry-run succeeds, execute actual restore with `dry_run=False`
4. Verify restored data integrity
5. Update RPO incident log

---

### 3. Disaster Recovery Drill

**Frequency:** Monthly

```bash
# Execute full DR drill
python -m layer3_knowledge.backup.drill --full

# Verify drill results
cat artifacts/backup-drill-$(date +%Y%m%d).json
```

For the repository-maintained non-production restore drill:

```bash
python -m pytest tests/recovery/
pnpm ops:backup:verify
pnpm ops:restore:dry-run
bash scripts/ops/test_postgres_backup_restore.sh
```

The `pnpm ops:restore:dry-run` command writes CI-safe evidence to
`artifacts/recovery/restore-dry-run-evidence.json`. The shell drill starts
isolated PostgreSQL source and restore containers and writes checksum evidence
to `artifacts/postgres-backup-restore/`.

**Drill checklist:**
- [ ] Restore to isolated DR environment
- [ ] Verify all backup storage backends accessible
- [ ] Validate checksums on restored data
- [ ] Confirm application can connect to restored data
- [ ] Confirm database, object storage, secrets/config references, and background jobs are validated
- [ ] Document any issues or delays
- [ ] Update DR playbook with lessons learned

---

### 4. Partial Tenant Restore

Use this path for bounded data loss affecting one tenant. Run it only in a
non-production recovery environment first.

1. Identify the affected `tenant_id` from authenticated tenant context and audit evidence.
2. Restore the candidate backup into an isolated recovery database.
3. Export only tenant-scoped rows and file metadata for the affected `tenant_id`.
4. Validate source and restored row counts, per-tenant checksums, object-storage metadata references, and billing/audit references.
5. Run hostile cross-tenant validation before promotion: Tenant A must not receive Tenant B rows, files, billing state, or audit events.
6. Emit audit evidence for the restore decision, approver, restore timestamp, checksum comparison, and affected records.

Do not trust request-body tenant IDs for restore scope. Tenant identity must be
derived from authenticated tenant context or an approved incident commander
system action with audit evidence.

---

### 5. Full Environment Restore

Use this path for environment loss, regional loss, or unrecoverable corruption.

1. Freeze non-essential writers and preserve incident evidence.
2. Restore PostgreSQL through managed PITR or the latest validated logical backup.
3. Restore Neo4j from the latest validated graph backup and rebuild vector indexes if required.
4. Restore files and customer-uploaded assets from S3 or MinIO-compatible object storage.
5. Rehydrate secrets/config references through Infisical or the target secrets manager; never copy plaintext secrets into evidence.
6. Restart background jobs only after database, graph, object storage, and secrets references validate.
7. Run release smoke, tenant isolation, billing, audit, and workflow recovery checks before traffic cutover.
8. Record RTO/RPO calculations and attach restore-verification evidence.

---

### 6. Object Storage and File Asset Restore

Files and customer-uploaded assets must be restored together with their database
metadata references. Validate:

- S3, GCS, or MinIO-compatible bucket availability.
- Object keys referenced by restored database rows exist in object storage.
- Restored files are scoped by tenant ownership and cannot be fetched cross-tenant.
- Deleted or quarantined objects are not accidentally resurrected without incident approval.

---

### 7. Audit Log Restore

Audit logs are recovery-critical. Validate that `audit_events` and any external
audit sink exports are restored without weakening append-only behavior,
tenant-scoped queries, hash-chain or canonical-hash checks, and trace
correlation. Restores must preserve audit evidence for the restore operation
itself.

---

### 8. Billing State Restore

Billing state must restore with tenant scope and webhook idempotency intact.
Validate billing plans, usage events, aggregates, invoices, payment state,
customers, subscriptions, and webhook idempotency records before re-enabling
billing jobs or accepting new billing webhooks.

---

### 9. CI / Scheduled Restore Verification Evidence

Restore verification runs through the scheduled/manual GitHub workflow
`.github/workflows/dr-drill.yml`. Local dry-run evidence still uses:

```bash
python -m pytest tests/recovery/ --junitxml artifacts/recovery/junit/recovery.xml
pnpm ops:restore:dry-run
```

It uploads `artifacts/recovery/**` as restore-verification evidence. Live
provider PITR and cloud object-storage restores remain environment-dependent and
must run against staging or another approved non-production environment.

---

### 10. Storage Backend Failover

If primary storage (S3) is unavailable:

```python
from layer3_knowledge.backup import BackupManager

# Automatic failover to GCS or Azure
bm = BackupManager(fallback_storage=['gcs', 'azure'])

# List available backups from all sources
backups = bm.list_backups(include_all_sources=True)
```

**Fallback order:**
1. S3 (primary)
2. GCS (secondary, different region)
3. Azure (tertiary, different cloud)
4. Local NFS (emergency only)

---

## Retention Policy Enforcement

Backups are automatically cleaned up based on:

| Backup Type | Max Age | Max Count |
|-------------|---------|-----------|
| Full | 30 days | 30 |
| Incremental | 7 days | 42 |
| Config | 90 days | unlimited |

**Manual cleanup (if needed):**

```python
bm = BackupManager()
bm._cleanup_old_backups(force=True)  # Override safety checks
```

---

## Alerting and Monitoring

**Critical alerts:**
- `BackupFailed` - Last backup attempt failed
- `BackupStale` - No successful backup in 25 hours
- `DRDrillFailed` - Monthly DR drill did not complete
- `StorageBackendDown` - Primary or secondary storage unreachable

**Runbook links:**
- Backup failure → Follow step 1 above, escalate if 2nd attempt fails
- Storage backend down → Initiate failover to secondary

---

## Contact and Escalation

| Role | Contact | Escalation |
|------|---------|------------|
| On-call Engineer | PagerDuty rotation | Auto-escalate after 15 min |
| Database Admin | #dba-team Slack | Page after 30 min if unresolved |
| Platform Lead | platform-lead@company.com | Executive escalation after 2 hours |

---

## Testing Requirements

All backup/restore functionality must be tested:

```bash
# Unit tests
pytest services/layer3-knowledge/tests/test_backup_manager.py -v

# Integration tests (requires test storage backend)
pytest services/layer3-knowledge/tests/test_backup_manager.py -m integration -v

# Full DR drill (production-like environment)
make test-backup-drills
```

---

## Related Documentation

- [Threat Model](../../../security/threat-model.md) - Security controls for backup encryption
- [API Reference](../../../API_REFERENCE.md) - Backup management endpoints
- [Semantic Contract](../../../semantic_contract.md) - Data integrity guarantees
