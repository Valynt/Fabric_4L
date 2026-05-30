# Backup and Disaster Recovery Runbook

## RTO/RPO Targets

| Metric | Target | Maximum |
|--------|--------|---------|
| **RTO** (Recovery Time Objective) | 4 hours | 8 hours |
| **RPO** (Recovery Point Objective) | 1 hour | 4 hours |

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

**Drill checklist:**
- [ ] Restore to isolated DR environment
- [ ] Verify all backup storage backends accessible
- [ ] Validate checksums on restored data
- [ ] Confirm application can connect to restored data
- [ ] Document any issues or delays
- [ ] Update DR playbook with lessons learned

---

### 4. Storage Backend Failover

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
