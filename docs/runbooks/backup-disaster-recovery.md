# Backup and Disaster Recovery Runbook

## Purpose

Restore Layer 3 knowledge graph and dependent platform data services within documented RTO/RPO targets after data loss, corruption, or regional failure.

## Trigger

Backup integrity failure, restore drill failure, data corruption, unrecoverable graph/database outage, or a declared disaster-recovery event.

## Severity

SEV-1 for production data loss, corruption, or unavailable restore path; SEV-2 for failed drills or degraded backup freshness; SEV-3 for documentation or evidence drift.

## Preconditions

Backup storage access, backup metadata/checksums, restore target capacity, tenant-impact assessment, and change/incident commander approval are available.

## Immediate Actions

1. Declare or confirm the incident owner and severity.
2. Freeze risky automated changes affecting the impacted service or control.
3. Capture initial timestamps, tenant/customer scope, deployment version, and active alerts.
4. Use the diagnosis steps below before applying destructive or irreversible changes.

## Diagnosis Steps

1. Confirm the trigger condition and affected environment.
2. Review the relevant dashboards, logs, audit records, and CI/readiness gate output.
3. Identify whether the issue is isolated to one tenant, service, dependency, or deployment version.
4. Preserve evidence before restarting services, rotating credentials, restoring data, or changing routing.

## Resolution Steps

1. Apply the least-risk corrective action that addresses the confirmed failure mode.
2. Keep tenant isolation, contract compatibility, and fail-closed security behavior intact.
3. Escalate to the service owner or incident commander before any destructive operation.
4. Record each operator action, command, and configuration change in the incident record.

## Validation

- Re-run the relevant health checks, smoke tests, contract checks, or readiness gates listed below.
- Confirm impacted tenants/customers can complete the critical path that failed.
- Confirm logs, metrics, and audit records show recovery and no new cross-tenant or security errors.

## Rollback / Fallback

- Prefer rollback to the last known-good deployment, configuration, registry record, backup, or credential set.
- If rollback is unsafe, isolate the impacted component, drain traffic where supported, and use the documented fallback path in the procedure details.
- Do not delete evidence or failed artifacts until the incident commander approves cleanup.

## Customer / Stakeholder Communication

- Notify the incident channel and accountable product/support stakeholders when customer impact is confirmed or likely.
- Provide scope, severity, current mitigation, expected next update time, and known customer-facing symptoms.
- Avoid sharing secrets, raw tenant data, provider tokens, or unreviewed root-cause speculation.

## Evidence to Preserve

- Alert names, timestamps, dashboard snapshots or links, and runbook version.
- Deployment SHAs, configuration diffs, migration IDs, registry versions, or backup artifact IDs.
- Sanitized logs, audit events, gate outputs, validation commands, and operator action timeline.

## Related Gates

Backup/restore readiness gates: backup inventory freshness, checksum validation, restore drill RTO/RPO evidence, `make check-migration-heads` when schema state is involved, and deployment gates before traffic cutover.

## Related Runbooks

- [Neo4j Backup and Restore Runbook](neo4j-backup-restore.md)
- [PostgreSQL High Availability Runbook](postgres-ha.md)
- [Deployment Rollout, Canary/Blue-Green Criteria, and Rollback](deployment-rollout-and-rollback.md)

## Post-Incident Follow-Up

- Attach validation evidence and gate results to the incident record.
- File corrective actions for missing alerts, missing tests, stale documentation, or slow recovery steps.
- Update this runbook and related gates if the incident exposed drift or an undocumented dependency.

---

## Procedure Details

### Scope
Layer 3 knowledge graph backup creation, integrity validation, restore drills, and point-in-time restore (PITR).

### Recovery Objectives
- **RTO (Recovery Time Objective): 30 minutes** — API read/write service for Layer 3 restored within 30 minutes of incident declaration.
- **RPO (Recovery Point Objective): 15 minutes** — Data loss limited to at most 15 minutes by combining periodic full backups with incremental captures.

### Preconditions
1. Backup storage is reachable (`local`, `s3`, `gcs`, `azure`, or `ftp` backend).
2. Latest backup metadata has checksum recorded.
3. Restore target database is available (or dry-run target for drills).

### Runbook Steps Mapped to RTO/RPO

#### 1) Verify backup inventory (supports RPO)
- List backups and identify latest successful full + incremental chain.
- Confirm metadata checksum exists for selected backup.
- **Target time:** 5 minutes.

#### 2) Validate integrity before restore (supports RPO)
- Retrieve backup and verify SHA-256 checksum from metadata sidecar.
- If mismatch occurs, select prior backup and raise incident severity.
- **Target time:** 5 minutes.

#### 3) Execute restore drill (supports RTO)
- Run dry-run restore against selected backup.
- Record entities/relationships that would be restored.
- **Target time:** 10 minutes.

#### 4) Execute actual restore (supports RTO)
- Restore schema, then data to recovery target.
- Use point-in-time parameter when incident requires rollback to known-safe timestamp.
- **Target time:** 10 minutes.

#### 5) Post-restore validation and cutover (supports RTO)
- Validate service health checks and key API queries.
- Cut traffic to recovered instance.
- **Target time:** 5 minutes.

### Drill Cadence
- Weekly automated dry-run drills.
- Monthly PITR drill to a timestamp earlier than the latest incremental backup.

### Failure Handling
- If any integrity check fails, do not proceed with production restore from that artifact.
- If drill exceeds target RTO, open corrective action item to reduce restore runtime.
