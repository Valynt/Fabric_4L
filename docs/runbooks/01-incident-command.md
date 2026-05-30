# Incident Command Runbook

## Purpose

Coordinate Value Fabric production incidents across engineering, security, customer operations, legal/privacy, and service owners. Use this as the command-and-control procedure before selecting a tactical runbook for deployment, database, security, auth, observability, or agent-specific remediation.

## Trigger

- Production alert, customer escalation, status-page report, support escalation, or operator observation indicates a customer-impacting incident.
- Any suspected tenant-isolation failure, data exposure, secret leak, auth bypass, data loss, failed production deployment, or restore event.
- A readiness gate, CI gate, backup/restore drill, tenant-boundary test, or observability alert indicates production risk requiring coordinated response.

## Severity

Use `docs/troubleshooting/runbooks/incident/severity-classification.md` as the source severity matrix and classify high until evidence supports downgrading.

| Severity | Start here when | Response target | Command requirement |
|---|---|---:|---|
| **SEV1** | Complete outage, data loss, confirmed or suspected security breach, cross-tenant exposure, credential compromise, or ransomware indicators. | 15 minutes | Incident commander required. |
| **SEV2** | Major feature degraded, partial data loss, failed production deployment with bounded impact, or one production layer unavailable with workaround. | 1 hour | Incident commander required. |
| **SEV3** | Minor feature issue, degraded non-critical workflow, or documented workaround available. | 4 hours | On-call lead may coordinate. |
| **SEV4** | Cosmetic or non-user-facing issue with no customer impact. | 24 hours | No formal command required. |

Any suspected security, privacy, tenant-isolation, credential, or unknown data-loss incident starts as **SEV1** until Security or the incident commander records downgrade evidence.

## Preconditions

- On-call responder has access to incident channels, paging system, deployment dashboards, logs/traces/metrics, status page, and CI/readiness gate outputs.
- Escalation contacts are available for Security, Legal/Privacy, Customer Operations, VP Engineering, and service owners for layers L1-L6.
- Evidence capture is possible before restarts, rollbacks, credential rotations, data restores, or destructive operations.

## Immediate Actions

1. Open an incident channel and assign incident commander, technical lead, communications lead, and scribe.
2. Record initial severity, UTC timestamp, reporter, affected environment, affected layer(s), impacted tenants/customers, active alerts, and deployment SHA/version.
3. Freeze non-essential production changes when deploy safety, tenant isolation, data integrity, authentication, or customer availability may be affected.
4. Select the tactical runbook from `docs/runbooks/00-runbook-index.md` or the related runbooks below.
5. Preserve evidence before mitigation: alert payloads, logs, traces, request IDs, audit events, gate output, deployment manifests, config diffs, and screenshots/links to dashboards.
6. Start customer and stakeholder update cadence for SEV1/SEV2 incidents or whenever broad customer impact is likely.

## Diagnosis Steps

1. Confirm the trigger, affected environment, first-bad timestamp, and whether the incident is tenant-specific, dependency-specific, deployment-specific, or global.
2. Check current deployment SHA, recent config/secret changes, feature flags, migrations, dependency status, and infrastructure events.
3. Compare customer-visible symptoms against service dashboards, error budgets, logs, traces, audit records, and CI/readiness gates.
4. Identify whether security/privacy, tenant isolation, data integrity, or auth risk is present; if yes, involve Security and preserve evidence before remediation.
5. Decide whether the safest immediate mitigation is containment, rollback, traffic drain, credential rotation, data restore, rate limiting, or forward fix.

## Resolution Steps

1. Apply the least-risk reversible mitigation that addresses the confirmed failure mode.
2. Keep tenant isolation, contract compatibility, audit logging, and fail-closed security behavior intact.
3. Escalate before destructive operations such as database restore, migration surgery, credential revocation, broad traffic cutover, or customer data export/delete changes.
4. Record every command, approval, mitigation, rollback, feature flag change, credential rotation, and customer communication in the incident timeline.
5. Continue status updates at the severity cadence until mitigation is stable and validation has passed or an explicit exception is approved.

## Validation

- Re-run the relevant readiness, smoke, contract, tenant-boundary, security, migration, backup/restore, or observability gates.
- Confirm impacted tenants/customers can complete the critical path that failed.
- Confirm logs, metrics, traces, and audit records show recovery and no new cross-tenant, auth, secret, or data-integrity errors.
- For SEV1/SEV2 incidents, assign a post-incident review owner and due date before closure.

## Rollback / Fallback

- Prefer the last known-good deployment, configuration, registry record, credential set, backup artifact, or feature-flag state when forward fix is riskier than rollback.
- If rollback is unsafe, isolate the affected component, drain or pause risky traffic, and document the manual workaround.
- Do not delete failed artifacts, logs, snapshots, or alert payloads until the incident commander approves cleanup.

## Customer / Stakeholder Communication

- SEV1: update every 15 minutes until mitigated; SEV2: update every 30 minutes until mitigated; SEV3: update at material changes.
- Share confirmed scope, symptoms, mitigation status, next update time, and customer actions if any.
- Do not share secrets, raw tenant data, provider tokens, unreviewed root cause speculation, or names of other impacted tenants.

## Evidence to Preserve

- Alert names, UTC timestamps, dashboard links/snapshots, incident channel transcript, and runbook version.
- Deployment SHA, image digest, manifest/config/secret diffs, migration IDs, backup IDs, and feature-flag changes.
- Sanitized logs, traces, request IDs, audit events, database query evidence, validation commands, gate outputs, approvals, and operator action timeline.

## Related Gates

- `make verify`
- `make contract-tests`
- `make check-migration-heads`
- `make check-conflict-markers`
- `make check-pytest-skip-governance`
- `pnpm run verify:frontend`
- `pnpm run check:contract-compliance`
- `pnpm run check:api-types`
- Backend integrated release smoke and service health/readiness checks when live stack access is available.

## Related Runbooks

- [Runbook index](00-runbook-index.md)
- [Deploy production release](deployment/deploy-production-release.md)
- [Rollback production release](deployment/rollback-production-release.md)
- [Failed deployment](deployment/failed-deployment.md)
- [Restore Postgres from backup](database/restore-postgres-from-backup.md)
- [Failed migration](database/failed-migration.md)
- [Respond to tenant data exposure](security/respond-to-tenant-data-exposure.md)
- [Respond to secret leak](security/respond-to-secret-leak.md)
- [Auth provider outage](auth/auth-provider-outage.md)
- [Alert triage](observability/alert-triage.md)
- [Severity classification](../troubleshooting/runbooks/incident/severity-classification.md)
- [Customer incident communication](customer-operations/customer-incident-communication.md)

## Post-Incident Follow-Up

- Publish postmortem for SEV1/SEV2 and any security, privacy, data-governance, tenant-isolation, or data-loss incident.
- File corrective actions with owners and dates for missing alerts, missing tests, stale documentation, slow recovery, contract drift, tenant-isolation gaps, or insufficient evidence capture.
- Update this runbook and related gates if the incident exposed undocumented dependencies or ambiguous decision points.
