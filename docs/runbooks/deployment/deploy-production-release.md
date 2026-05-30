# Deploy Production Release Runbook

## Purpose

Safely promote a Value Fabric production release while preserving tenant isolation, API contracts, auditability, and rollback readiness across the frontend, API gateway, and L1-L6 services.

## Trigger

- Planned production release window.
- Emergency production hotfix approved by the incident commander.
- Blue/green or canary promotion after staging/ephemeral validation passes.

## Severity

- **SEV1:** Deployment causes complete outage, data loss, security regression, credential exposure, or tenant-isolation failure.
- **SEV2:** Deployment degrades a major workflow or one layer with customer impact and workaround.
- **SEV3:** Deployment gate fails before production impact or affects non-critical workflow only.
- **SEV4:** Documentation or release-note drift with no runtime impact.

## Preconditions

- Required CI checks passed for the exact release SHA: structural preflight, per-layer lint/typecheck/test jobs, contract checks, API type drift checks, and frontend verification as applicable.
- Release SHA, image digests, rendered manifests, migration plan, rollback target, and feature-flag plan are documented.
- Secrets are delivered through approved paths only; no production deploy relies on dev auth bypass flags.
- Database migration owners and service owners for affected layers are available during the window.
- Incident channel or release channel is open with an assigned deployment owner and rollback decision maker.

## Immediate Actions

1. Confirm deployment owner, approver, release SHA, image digests, target environment, and maintenance/customer communication plan.
2. Freeze unrelated production changes during the release window.
3. Capture pre-deploy evidence: health dashboards, active alerts, error rates, latency, queue depth, database health, and current deployment versions.
4. Confirm rollback target health and database restore/PITR readiness before applying manifests or migrations.
5. Confirm tenant-isolation, auth, contract, and audit gates are green or have explicit documented exceptions.

## Diagnosis Steps

1. Review release diff for API contract changes, migrations, auth/tenant-context changes, secrets/config changes, and frontend expectations.
2. Confirm OpenAPI/JSON Schema/type generation is aligned when contracts changed.
3. Confirm migration state has exactly one Alembic head per affected service and migration commands are scoped to the intended layer.
4. Validate production configuration for forbidden dev auth bypass flags.
5. Confirm observability monitors and alerts are active for the cutover window.

## Resolution Steps

1. Deploy green/canary stack without broad traffic, using the approved manifests and image digests.
2. Run pre-traffic health, readiness, smoke, contract, and migration validation for the new stack.
3. Shift traffic gradually or by approved blue/green selector change only after green/canary gates pass.
4. Observe the post-cutover window for readiness false, elevated error rate, p95 latency regression, queue buildup, auth failures, tenant-isolation warnings, and database errors.
5. If rollback criteria trigger, stop promotion and use [Rollback production release](rollback-production-release.md).
6. Record all commands, timestamps, gate outputs, dashboard links, and approvals in the release record.

## Validation

- Re-run production smoke checks for affected customer-critical paths.
- Confirm `/health` and readiness endpoints for affected services are healthy.
- Confirm logs show no `cross.tenant`, `tenant.isolation`, auth bypass, migration, or contract errors.
- Confirm API contract and frontend expectations remain aligned when API changes shipped.
- Confirm audit events are emitted for security-sensitive actions.

## Rollback / Fallback

- Roll back to the last known-good deployment if readiness remains false for more than the approved threshold, error rate or latency exceeds deployment criteria, tenant-isolation/auth/security errors appear, or migrations fail.
- Do not roll back across irreversible database migrations without database owner approval and a documented data safety plan.
- If rollback is unsafe, isolate the affected service, disable the risky feature flag, drain traffic, or hold writes while a forward fix is prepared.

## Customer / Stakeholder Communication

- Notify Customer Operations before customer-visible releases or maintenance windows.
- For degraded release outcomes, provide severity, scope, mitigation, next update time, and any customer action required.
- Do not disclose raw tenant data, secrets, or unreviewed root-cause speculation.

## Evidence to Preserve

- Release SHA, image digests, rendered manifests, Helm/Kustomize output, feature-flag changes, and deployment commands.
- CI gate URLs/output, migration IDs, migration logs, smoke test output, dashboards, and alert payloads.
- Operator approvals, timestamps, customer communications, and rollback decision notes.

## Related Gates

- `make verify`
- `make contract-tests`
- `make check-migration-heads`
- `pnpm run verify:frontend`
- `pnpm run check:contract-compliance`
- `pnpm run check:api-types`
- Backend integrated release smoke and blue/green health gate where available.

## Related Runbooks

- [Incident command](../01-incident-command.md)
- [Rollback production release](rollback-production-release.md)
- [Failed deployment](failed-deployment.md)
- [Failed migration](../database/failed-migration.md)
- [Deployment rollout and rollback](../deployment-rollout-and-rollback.md)
- [Alert triage](../observability/alert-triage.md)

## Post-Incident Follow-Up

- Attach release evidence to the change record.
- File follow-up work for slow gates, flaky release checks, missing dashboards, missing rollback automation, or undocumented migration risk.
- Update this runbook if the deployment required undocumented manual steps.
