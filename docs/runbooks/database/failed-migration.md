# Failed Migration Runbook

## Purpose

Contain, diagnose, and recover from failed Alembic/database migrations without corrupting tenant-owned data, breaking API contracts, or leaving services in mixed schema states.

## Trigger

- `make migrate`, service-specific migration command, CI migration gate, or production migration job fails.
- Application deployment fails because schema version is missing, duplicated, partially applied, or incompatible.
- Runtime errors indicate schema drift, missing columns/tables/indexes, migration head mismatch, or data backfill failure.

## Severity

- **SEV1:** Failed migration causes production outage, data loss/corruption, tenant-isolation regression, or irreversible partial write.
- **SEV2:** Migration blocks production release or degrades major workflow with bounded data impact.
- **SEV3:** Migration fails in staging/CI or before production traffic.
- **SEV4:** Documentation, migration metadata, or non-runtime drift only.

## Preconditions

- Database owner and affected service owner are assigned.
- Current schema version, target migration revision, affected service/layer, and release SHA are known.
- Recent backup/PITR point is verified before any destructive fix.
- Application write traffic and migration jobs can be paused for affected services.

## Immediate Actions

1. Stop the rollout and freeze additional migrations/deployments for affected services.
2. Preserve migration logs, DB error messages, release SHA, migration revision IDs, and current schema state.
3. Confirm whether the migration reached production and whether application traffic wrote to a partially migrated schema.
4. Pause writes/background workers if mixed schema state could corrupt data.
5. Escalate to incident command for customer impact, data loss, tenant risk, or production service degradation.

## Diagnosis Steps

1. Identify the failed phase: migration precheck, DDL, data backfill, index creation, constraint validation, downgrade/rollback, or application startup.
2. Check current revision and heads for the affected service; confirm there is exactly one intended head.
3. Inspect whether the failure is safe to retry, requires idempotency fix, requires forward migration, or requires database restore.
4. Check recent application errors for contract drift, missing tenant filters, or repository assumptions about schema shape.
5. Confirm whether any tenants have partial data updates and whether audit logs can prove scope.

## Resolution Steps

1. Keep application traffic on the compatible version or roll back code if schema remains compatible.
2. Prefer a forward-only corrective migration for partially applied production DDL/data changes when safe.
3. Retry only after making the migration idempotent and verifying the database state matches retry assumptions.
4. Use restore/PITR only when data corruption or unsafe partial state cannot be corrected safely.
5. Update application code, contracts, and generated types if migration changes public response shapes or frontend expectations.
6. Record all commands, SQL/Alembic revisions, approvals, and validation outputs.

## Validation

- Run `make check-migration-heads`.
- Verify the affected service reports the expected Alembic revision.
- Run targeted service tests and contract checks for API paths affected by the schema.
- Run tenant-scoped data integrity checks for affected tenants and hostile cross-tenant access checks when tenant-owned tables changed.
- Confirm logs show no missing schema, duplicate revision, lock timeout, or data backfill errors.

## Rollback / Fallback

- Do not run destructive downgrade or manual SQL cleanup without database owner and incident commander approval.
- If schema is backward compatible, roll application code back while preparing a corrective migration.
- If schema is not backward compatible and data is unsafe, use [Restore Postgres from backup](restore-postgres-from-backup.md).
- If a long index/constraint migration blocks traffic, pause migration, restore service health, and reschedule with an online migration plan.

## Customer / Stakeholder Communication

- Notify release stakeholders when migration blocks or delays a release.
- Notify Customer Operations if customer-visible degradation, data unavailability, or maintenance window extension occurs.
- Security/Legal must review messaging if tenant isolation or data integrity is implicated.

## Evidence to Preserve

- Migration revision IDs, Alembic output, SQL errors, schema snapshots, lock/deadlock logs, DB version, release SHA, and backup/PITR evidence.
- Affected tenant/customer scope, partial row counts, audit events, application errors, and validation commands.
- Timeline of pause, retry, forward fix, rollback, or restore decisions.

## Related Gates

- `make check-migration-heads`
- `make migrate` or service-specific migration command in controlled environments.
- `make contract-tests`
- Targeted service tests for changed repositories/models.
- Tenant-boundary/security tests for tenant-owned tables.

## Related Runbooks

- [Incident command](../01-incident-command.md)
- [Restore Postgres from backup](restore-postgres-from-backup.md)
- [Deploy production release](../deployment/deploy-production-release.md)
- [Rollback production release](../deployment/rollback-production-release.md)
- [Investigate data corruption](../data-governance/investigate-data-corruption.md)
- [PostgreSQL high availability](../postgres-ha.md)

## Post-Incident Follow-Up

- Add migration prechecks, idempotency tests, data backfill tests, and rollback/forward-fix documentation.
- Update contracts/types/docs if the migration changed API-visible behavior.
- Record compatibility debt or cleanup tasks with owners and target dates.
