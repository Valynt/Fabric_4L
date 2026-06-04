# Stabilization War Room

Root coordination entrypoint for stabilization, incident response, rollback, and validation work. Use this page to find the authoritative operational documentation; do not duplicate long runbook content here.

## First actions

1. Classify severity with the incident runbook before selecting a response path: [severity classification](docs/troubleshooting/runbooks/incident/severity-classification.md).
2. Open the operational index for current policies, escalation, SLOs, and runbook navigation: [docs/operations/](docs/operations/).
3. If this is stabilization work rather than a live incident, confirm the active gate and freeze rules in the [Gate 0 stabilization intake](docs/launch/stabilization-gate-0-intake-2026-06-03.md).
4. Record owners, evidence, decisions, and follow-up links in the appropriate launch, incident, or operations document.

## Operational coordination

- [Operations package](docs/operations/) — primary index for incident standards, escalation, postmortems, operational KPIs, and runbooks.
- [Runbook overview](docs/operations/runbook-overview.md) — incident response flow, rollback overview, monitoring checks, and common operational issues.
- [Escalation policy and drills](docs/operations/escalation-policy-and-drills.md) — escalation expectations and drill coordination.
- [Severity escalation policy](docs/operations/severity-escalation-policy.md) — operations severity matrix and escalation commitments.
- [MTTA/MTTR reporting](docs/operations/mtta-mttr-reporting.md) — incident response metrics and monthly reporting expectations.
- [Postmortem template](docs/operations/postmortem-template.md) — post-incident review template and corrective action tracking.

## Stabilization and launch gates

- [Gate 0 stabilization intake](docs/launch/stabilization-gate-0-intake-2026-06-03.md) — stabilization start conditions, merge-freeze policy, ownership register, and backlog rules.
- [Launch blocker register](docs/launch/launch-blocker-register.md) — authoritative blocker status for ship/no-ship decisions.
- [Environment-dependent evidence matrix](docs/launch/environment-dependent-evidence-matrix.md) — required environment evidence and validation gaps.
- [Final testing launch checklist](docs/launch/final-testing-launch-checklist.md) — final gate checklist and validator evidence references.

## Incident runbooks

- [Incident severity classification](docs/troubleshooting/runbooks/incident/severity-classification.md) — required first stop for SEV assignment.
- [Incident communication template](docs/troubleshooting/runbooks/incident/communication-template.md) — update cadence and stakeholder messaging template.
- [Incident postmortem template](docs/troubleshooting/runbooks/incident/incident-postmortem-template.md) — incident-specific postmortem template.
- [Tenant isolation failure](docs/troubleshooting/runbooks/incident/tenant-isolation-failure.md) — tenant-boundary incident response.
- [Data breach response](docs/troubleshooting/runbooks/incident/data-breach-response.md) — security/data-exposure response path.
- [Backup and disaster recovery](docs/troubleshooting/runbooks/incident/backup-disaster-recovery.md) — backup/restore response entrypoint.
- [Cloud provider outage](docs/troubleshooting/runbooks/incident/cloud-provider-outage.md) — regional or provider-level outage response.
- [Ransomware response](docs/troubleshooting/runbooks/incident/ransomware-response.md) — containment, evidence, and recovery guidance.

## Rollback and recovery runbooks

- [Deployment rollback](docs/troubleshooting/runbooks/infrastructure/deployment-rollback.md) — emergency deployment rollback procedure.
- [Deployment rollout and rollback](docs/troubleshooting/runbooks/infrastructure/deployment-rollout-and-rollback.md) — controlled rollout and rollback operations.
- [Database migration rollback](docs/operations/runbooks/database-migration-rollback.md) — database migration rollback coordination.
- [Release checklist](docs/troubleshooting/runbooks/infrastructure/release-checklist.md) — release readiness and rollback checkpoints.
- [PostgreSQL backup/restore](docs/troubleshooting/runbooks/infrastructure/postgres-backup-restore.md) — PostgreSQL recovery path.
- [DR gameday: region loss](docs/troubleshooting/runbooks/incident/dr-gameday-region-loss.md) — disaster recovery drill for regional loss.
- [DR gameday: service failover](docs/troubleshooting/runbooks/incident/dr-gameday-service-failover.md) — service failover drill.

## Validation and evidence

- [Production readiness execution status](docs/validation/production_readiness_execution_status.md) — current readiness and validation status.
- [Production readiness prioritized execution plan](docs/validation/production_readiness_prioritized_execution_plan.md) — prioritized validation/remediation plan.
- [Final testing launch gate design](docs/validation/final_testing_launch_gate_design.md) — final testing gate design and evidence model.
- [Launch readiness final sign-off evidence](docs/validation/launch_readiness_final_sign_off_evidence.md) — final sign-off evidence record.
- [Live workflow validation](docs/validation/live-workflow-validation.md) — live workflow validation procedure and CI gate context.
- [Backend platform validation ownership matrix](docs/validation/backend_platform_validation_ownership_matrix.md) — backend validation ownership and accountability.
- [Tenant isolation evidence summary](docs/validation/tenant-isolation-evidence-summary.md) — tenant-boundary validation evidence.

## War-room hygiene

- Keep active coordination in the incident channel or stabilization tracker; link back to these source-of-truth docs.
- Assign a single owner and backup for every live workstream.
- Preserve evidence before destructive remediation, especially for SEV-0/SEV-1 and security incidents.
- Update the referenced runbook or launch artifact when a decision, mitigation, or validation result changes.
