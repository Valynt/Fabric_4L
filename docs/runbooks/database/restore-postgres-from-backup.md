# Restore Postgres from Backup Runbook

## Purpose

Restore a Value Fabric PostgreSQL database from a verified backup or point-in-time recovery chain while preserving tenant boundaries, auditability, and documented RTO/RPO evidence.

## Trigger

- Production Postgres data loss, corruption, accidental destructive write, failed migration requiring restore, or disaster-recovery event.
- Backup integrity or restore drill failure requiring operator intervention.
- Incident commander or database owner approves restoring to a known-safe timestamp.

## Severity

- **SEV1:** Production data loss, corruption, unavailable restore path, cross-tenant data corruption, or restore needed for customer-critical service.
- **SEV2:** Bounded dataset restore, degraded backup freshness, or failed restore drill with no active customer impact.
- **SEV3:** Non-production restore failure or evidence/documentation drift.
- **SEV4:** Backup metadata typo or non-impacting dashboard issue.

## Preconditions

- Incident commander and database owner approval are recorded for production restore.
- Target database/cluster, restore timestamp, backup artifact ID, checksum, encryption key path, and tenant/customer impact are identified.
- Current database state is preserved with a snapshot or export before destructive restore when feasible.
- Application write traffic can be paused, drained, or routed away for the affected service/tenant scope.
- Secrets are available through approved secret-management paths; no credentials are pasted into incident channels.

## Immediate Actions

1. Declare or confirm severity, database owner, restore owner, and communications lead.
2. Freeze deployments, migrations, background jobs, and non-essential writes for affected services.
3. Capture current database status, active connections, replication state, backup inventory, WAL/PITR position, and affected tenant/customer scope.
4. Preserve evidence before restore: logs, audit events, query evidence, migration IDs, backup metadata, checksums, and current snapshot ID.
5. Confirm selected backup is from before the corruption/loss timestamp and after the required RPO point.

## Diagnosis Steps

1. Determine the failure mode: corruption, accidental delete/update, migration failure, hardware/storage failure, tenant-scoped data issue, or regional outage.
2. Identify first-bad timestamp and last-known-good timestamp using audit logs, application traces, WAL/query logs, deployment history, and customer reports.
3. Validate backup inventory and checksums; if the latest artifact fails validation, select the prior valid artifact and raise severity.
4. Decide whether full database restore, point-in-time restore, tenant-scoped repair, or application-level replay is safest.
5. Confirm downstream services, caches, search/vector/graph projections, and frontend/API expectations after restore.

## Resolution Steps

1. Stop writes and background workers for the affected scope.
2. Take a final protective snapshot/export of the current state if time and safety permit.
3. Restore backup to an isolated recovery target first when possible.
4. Validate schema, migration version, tenant counts, critical records, and application smoke paths on the recovery target.
5. Promote/cut over to the restored database only after database owner and incident commander approval.
6. Rebuild dependent derived stores or caches if restore invalidates them.
7. Record all commands, backup IDs, timestamps, approvals, and validation outputs.

## Validation

- Verify backup checksum and restore completion status.
- Confirm schema migration version and exactly one Alembic head for affected services.
- Run tenant-scoped data checks for affected tenants and at least one unaffected tenant.
- Run service health checks, customer-critical smoke tests, contract checks, and audit-log checks.
- Confirm no cross-tenant records, missing `tenant_id` ownership, or stale derived projections were introduced.

## Rollback / Fallback

- If restore validation fails, do not cut over; select the prior valid backup or move to isolated repair.
- If cutover causes regression, route traffic back to the previous database snapshot only if no new writes would be lost or after explicit data-loss approval.
- If full restore is too risky, use tenant-scoped repair/replay with database owner and Security approval.

## Customer / Stakeholder Communication

- Notify Customer Operations for any customer-visible data loss, degraded service, or restore window.
- Security/Legal must review communications for data exposure, cross-tenant corruption, or regulated data impact.
- Communicate known scope, RPO/RTO status, mitigation, next update time, and any customer action required.

## Evidence to Preserve

- Backup artifact IDs, metadata sidecars, checksums, WAL/PITR target timestamp, encryption key reference, and restore commands.
- Current-state snapshot/export ID, migration IDs, schema version, affected tenant IDs, sanitized query evidence, and audit events.
- Validation outputs, dashboards, logs/traces, cutover approvals, and customer communication timeline.

## Related Gates

- Backup inventory freshness and checksum validation.
- Restore drill RTO/RPO evidence.
- `make check-migration-heads`
- `make contract-tests`
- Tenant-boundary/security regression tests for restored paths.
- Service health/readiness and backend integrated smoke checks when live stack is available.

## Related Runbooks

- [Incident command](../01-incident-command.md)
- [Failed migration](failed-migration.md)
- [Backup and disaster recovery](../backup-disaster-recovery.md)
- [PostgreSQL high availability](../postgres-ha.md)
- [Investigate data corruption](../data-governance/investigate-data-corruption.md)
- [Rollback production release](../deployment/rollback-production-release.md)

## Post-Incident Follow-Up

- Attach restore evidence, RTO/RPO measurements, and validation outputs to the incident record.
- File corrective actions for backup gaps, slow restore, missing tenant-scoped validation, missing alerts, or stale runbooks.
- Schedule a restore drill if the incident exposed untested backup assumptions.
