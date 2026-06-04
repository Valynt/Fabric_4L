# Recovery Validation Suite

## What This Suite Validates

This suite validates backup, restore, and disaster recovery readiness without touching production data. It is intentionally CI-safe and checks that the non-production restore drill path, runbooks, Kubernetes backup jobs, tenant restore checks, audit-log restore checks, and billing-state restore checks remain wired.

## Production Risks Covered

- Backups that exist but cannot be restored.
- Tenant-scoped data, file assets, audit logs, or billing state missing from restore evidence.
- RPO/RTO targets missing from runbooks and release evidence.
- Restore workflows depending on undocumented manual steps.

## Existing Coverage Aggregated

- `tests/recovery/test_backup_exists.py`
- `tests/recovery/test_restore_smoke.py`
- `tests/recovery/test_restore_tenant_data.py`
- `tests/recovery/test_restore_file_assets.py`
- `tests/recovery/test_restore_audit_logs.py`
- `tests/recovery/test_restore_billing_state.py`
- `.github/workflows/restore-verification.yml`
- `scripts/ops/restore_dry_run.py`

## Known Gaps

- LIVE_CLOUD_PITR: real cloud PITR, S3/GCS restore, secrets-manager restore, and full environment restore are environment-dependent checks.
- LIVE_POSTGRES_CONTAINER_DRILL: the isolated PostgreSQL drill requires Docker and remains outside the default fast suite.

## How To Run

```bash
python -m pytest tests/recovery/
pnpm test:recovery
pnpm ops:backup:verify
pnpm ops:restore:dry-run
```

## CI Artifact

CI should publish `artifacts/production-readiness/recovery/junit.xml`. The dry-run command writes:

```text
artifacts/recovery/restore-dry-run-evidence.json
```

## RPO / RTO

Platform DR targets are documented in `docs/troubleshooting/runbooks/incident/backup-disaster-recovery.md`:

| Metric | Target | Maximum |
|---|---:|---:|
| RPO | 1 hour | 4 hours |
| RTO | 4 hours | 8 hours |

Daily logical PostgreSQL backups alone do not satisfy the live-customer RPO. Production must use managed PostgreSQL PITR or equivalent WAL archiving for the 1-hour target.

The live isolated PostgreSQL drill remains:

```bash
bash scripts/ops/test_postgres_backup_restore.sh
```

That drill requires Docker and writes checksum evidence to `artifacts/postgres-backup-restore/`.

