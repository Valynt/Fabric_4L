# Recovery Validation Suite

This suite validates backup, restore, and disaster recovery readiness without
touching production data. It is intentionally CI-safe by default and checks that
the real non-production restore drill path, runbooks, Kubernetes backup jobs,
and evidence contracts remain wired.

## Commands

```bash
python -m pytest tests/recovery/
pnpm ops:backup:verify
pnpm ops:restore:dry-run
```

The dry-run command writes machine-readable evidence to:

```text
artifacts/recovery/restore-dry-run-evidence.json
```

The live isolated PostgreSQL drill remains:

```bash
bash scripts/ops/test_postgres_backup_restore.sh
```

That drill requires Docker and creates isolated source and restore PostgreSQL
containers. It writes checksum evidence to `artifacts/postgres-backup-restore/`.

## RPO / RTO

Platform DR targets are documented in
`docs/troubleshooting/runbooks/incident/backup-disaster-recovery.md`:

| Metric | Target | Maximum |
|---|---:|---:|
| RPO | 1 hour | 4 hours |
| RTO | 4 hours | 8 hours |

Daily logical PostgreSQL backups alone do not satisfy the live-customer RPO.
Production must use managed PostgreSQL PITR or equivalent WAL archiving for the
1-hour target.

## Coverage

The suite validates:

- PostgreSQL and Neo4j backup job declarations.
- Restore drill command wiring and evidence emission.
- Tenant-scoped row count and checksum comparison.
- Database, object storage, secrets/config references, and background jobs.
- File assets and object-storage metadata references.
- Append-only audit log restore requirements.
- Billing plans, usage events, aggregates, invoices, payment state, subscriptions,
  and webhook idempotency coverage.

Real cloud PITR, S3/GCS restore, secrets-manager restore, and full environment
restore are environment-dependent checks. They should run through the scheduled
or manually dispatched restore-verification workflow against a non-production
environment with evidence attached.
