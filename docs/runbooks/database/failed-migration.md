# Failed Migration Runbook

## Scope

Use this runbook when an Alembic/database migration fails, partially applies, creates schema drift, blocks application startup, or causes post-deploy data integrity concerns.

## Severity

- **SEV1:** Migration causes data loss, corruption, tenant exposure, complete outage, or unsafe production writes.
- **SEV2:** Migration blocks a production release or degrades a major function but production data remains intact.
- **SEV3:** Migration fails in staging, CI, or before production traffic is affected.

## Immediate Actions

1. Stop the deployment and prevent retries until the database state is understood.
2. Activate Incident Command for production impact and freeze writes/consumers when data integrity is uncertain.
3. Preserve migration logs, current schema version, database events, and release SHA.
4. Take a final backup/snapshot before attempting manual repair, downgrade, or re-run.
5. Identify whether the migration is unapplied, partially applied, applied with bad data, or applied but incompatible with the application.
6. Prefer roll-forward corrective migrations for production unless a tested rollback is explicitly safe.
7. If restore is needed, switch to the Postgres restore runbook.

## Diagnosis

```bash
# Show migration heads expected by the repository.
make check-migration-heads

# Inspect current migration state for the affected service.
cd services/<layer-service>
alembic current
alembic heads
alembic history --verbose | tail -50

# Capture database migration/version table.
psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" "$POSTGRES_DB" \
  -c "SELECT * FROM alembic_version;"
```

Check the affected service's canonical migration path before making assumptions; this repository has service-specific Alembic setups.

## Validation

- Database backup/snapshot exists from before manual intervention.
- Current schema version and intended target revision are documented.
- Migration state is either restored to last known-good version or advanced to a corrected version.
- Application starts against the resulting schema and critical read/write paths pass smoke tests.
- Tenant-scoped queries still enforce `tenant_id` filters and no cross-tenant data was introduced.
- Release/incident channel records whether the release was aborted, rolled forward, rolled back, or restored.

## Evidence to Preserve

- Migration file names, revision IDs, release SHA, and service/layer name.
- Alembic logs, stack traces, `alembic current`, `alembic heads`, and migration table output.
- Database backup/snapshot reference and restore test evidence if used.
- Schema diff, data correction SQL, and approvals for any manual changes.
- Application errors and dashboard snapshots from before and after mitigation.

## Related Gates

- `make check-migration-heads`
- `make migrate`
- `make test-backend-integrated-release-smoke`
- `make contract-tests`
- `make verify`

## Related Runbooks

- [Incident Command](../01-incident-command.md)
- [Restore Postgres From Backup](restore-postgres-from-backup.md)
- [Deploy Production Release](../deployment/deploy-production-release.md)
- [Rollback Production Release](../deployment/rollback-production-release.md)
- [Respond to Tenant Data Exposure](../security/respond-to-tenant-data-exposure.md)
