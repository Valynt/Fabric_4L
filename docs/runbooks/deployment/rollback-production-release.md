# Rollback Production Release Runbook

## Purpose

Restore Value Fabric production to a known-good release after a deployment introduces availability, correctness, security, tenant-isolation, contract, or performance regressions.

## Trigger

- Post-deploy health, smoke, readiness, contract, or observability gate fails.
- Error rate, latency, crash-loop, auth failures, tenant-isolation warnings, or customer reports exceed rollback criteria.
- Incident commander or deployment owner decides forward fix is riskier than reverting.

## Severity

- **SEV1:** Rollback is required for complete outage, data loss, tenant exposure, credential compromise, or active security risk.
- **SEV2:** Rollback is required for major workflow degradation or one layer unavailable with workaround.
- **SEV3:** Rollback is required before broad traffic exposure or for non-critical degradation.
- **SEV4:** Documentation, release metadata, or observability label rollback only.

## Preconditions

- Last known-good release SHA/image digest/manifests are identified and were previously validated.
- Database owner confirms whether schema/data state is backward compatible.
- Traffic shift controls, feature flags, and service selectors are available.
- Incident commander approves rollback if customer impact, data integrity, or security risk is present.

## Immediate Actions

1. Declare or confirm incident owner, severity, rollback owner, and rollback decision maker.
2. Freeze new deploys and automated promotions for affected services.
3. Preserve failed deployment evidence before changing traffic or deleting pods.
4. Identify the first bad version and last known-good version for each affected component.
5. Confirm whether migrations, background jobs, or data writes occurred after the bad deployment.

## Diagnosis Steps

1. Compare pre- and post-deploy dashboards, alerts, logs, traces, and customer reports.
2. Determine whether the failure is code, config, secret, dependency, migration, contract, frontend/back-end drift, or tenant-specific data.
3. Check whether rollback crosses a database or contract boundary that requires compatibility handling.
4. Confirm no active data exposure or secret leak requires security containment before traffic rollback.

## Resolution Steps

1. Stop or pause further rollout and hold new traffic on the healthiest track.
2. Repoint traffic to the last known-good blue/green or canary target when available.
3. Reapply the last known-good manifests/image digests or revert the deployment controller to the previous revision.
4. Disable feature flags introduced by the failed release if traffic rollback is incomplete.
5. Coordinate database rollback, point-in-time restore, or forward migration fix only with database owner approval.
6. Record each command, timestamp, manifest version, selector change, and approval in the incident record.

## Validation

- Confirm affected services are ready and healthy on the rollback version.
- Confirm error rate, p95 latency, crash loops, auth failures, and tenant-isolation warnings return to baseline.
- Run customer-critical smoke paths and relevant contract/tenant-boundary checks.
- Confirm no new migration drift or frontend/API type drift remains after rollback.

## Rollback / Fallback

This runbook is the rollback procedure. If rollback fails or is unsafe:

- Isolate the failing service, drain traffic, or put affected write paths into read-only/maintenance mode.
- Revert risky feature flags/configuration independently from code.
- Use database restore or failed migration runbooks for data/schema issues.
- Escalate to incident commander for emergency forward fix.

## Customer / Stakeholder Communication

- Notify stakeholders when rollback starts, when traffic is restored, and when validation is complete.
- Provide affected scope, expected customer symptoms, mitigation, and next update time.
- Security/privacy incidents must be reviewed by Security/Legal before external details are shared.

## Evidence to Preserve

- Failed release SHA/image digest, rollback SHA/image digest, deployment commands, selectors, manifests, and feature flag history.
- Alert payloads, dashboards, sanitized logs/traces, migration logs, customer reports, and validation outputs.
- Timeline of rollback decision, approvals, traffic shifts, and post-rollback recovery.

## Related Gates

- Blue/green health gate and post-cutover smoke checks.
- `make verify`
- `make contract-tests`
- `make check-migration-heads`
- `pnpm run verify:frontend`
- Backend integrated release smoke when live stack is available.

## Related Runbooks

- [Incident command](../01-incident-command.md)
- [Deploy production release](deploy-production-release.md)
- [Failed deployment](failed-deployment.md)
- [Failed migration](../database/failed-migration.md)
- [Restore Postgres from backup](../database/restore-postgres-from-backup.md)
- [Deployment rollout and rollback](../deployment-rollout-and-rollback.md)

## Post-Incident Follow-Up

- Document root cause, rollback duration, validation evidence, and any customer impact.
- File corrective actions for missing rollback tests, non-backward-compatible migrations, contract drift, or insufficient deploy observability.
- Update release and rollback automation if manual intervention was needed.
