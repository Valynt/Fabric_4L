# Failed Deployment Runbook

## Purpose

Triage and recover from a failed production or production-like deployment before it becomes broad customer impact, while preserving release evidence and rollback safety.

## Trigger

- CI/CD deployment job fails, manifests fail to apply, pods fail readiness, smoke checks fail, or post-deploy alerts fire.
- Canary/green deployment fails health gates before or after traffic shift.
- Release owner observes unexpected migration, secret, config, or contract errors during deployment.

## Severity

- **SEV1:** Failed deployment caused complete outage, security regression, tenant exposure, data loss, or broad production unavailability.
- **SEV2:** Failed deployment caused major feature degradation or one layer unavailable with workaround.
- **SEV3:** Failed deployment was contained before broad production impact.
- **SEV4:** Non-production deployment failure or documentation/release metadata issue only.

## Preconditions

- Deployment owner has access to CI logs, Kubernetes events, application logs, metrics, deployment manifests, and rollback target.
- Incident commander is assigned when production customer impact is possible.
- Database owner is available if migrations or schema compatibility are implicated.

## Immediate Actions

1. Stop automatic promotion and freeze unrelated production changes.
2. Confirm whether traffic reached the failed version and whether customers or tenants are impacted.
3. Preserve CI logs, deploy logs, Kubernetes events, pod logs, manifest output, and failed gate output.
4. If customer impact exists, open incident command and classify severity.
5. If the failed deployment reached production traffic, decide whether to roll back immediately or contain with traffic drain/feature flags.

## Diagnosis Steps

1. Identify the failing phase: build, image publish, manifest render/apply, migration, readiness, smoke, traffic shift, or post-cutover observation.
2. Inspect pod status, events, health endpoints, service selectors, ingress, secrets/config maps, and resource limits.
3. Check logs for auth bypass flags, missing secrets, tenant-isolation warnings, contract validation failures, migration errors, and dependency failures.
4. Compare the failed release against the last successful release and recent infrastructure/config changes.
5. Determine whether this is an environment issue, deploy tooling issue, application regression, migration issue, or external dependency outage.

## Resolution Steps

1. If traffic is impacted, route traffic to the last known-good version or use [Rollback production release](rollback-production-release.md).
2. If no traffic is impacted, keep the failed version isolated while diagnosing.
3. Fix only reversible configuration or rollout errors in-place; use a new release artifact for code changes.
4. For migration failures, stop application rollout and follow [Failed migration](../database/failed-migration.md).
5. For missing/invalid secrets, rotate or repair through approved secret-management paths; never paste secrets into manifests or logs.
6. Re-run the failed gate and then the full required release validation before retrying promotion.

## Validation

- Confirm deployment controller reports desired/available replicas and readiness is stable.
- Confirm health endpoints, smoke tests, logs, and metrics are clean for the affected services.
- Confirm customer-critical paths work for affected tenants and at least one unaffected tenant when tenant scope was involved.
- Confirm no CI, contract, migration, or frontend type drift remains.

## Rollback / Fallback

- Prefer rollback when the failure reached production traffic or when root cause is unknown.
- Prefer retry only when failure was isolated to tooling/environment and the release artifact remains valid.
- Use maintenance/read-only mode or feature-flag disablement if rollback is blocked by database state or dependency constraints.

## Customer / Stakeholder Communication

- Communicate only if customer impact occurred, release window is extended, or a planned customer-visible change is delayed.
- Provide scope, mitigation, next update time, and whether customer action is required.
- For security/privacy signals, coordinate all messaging with Security/Legal.

## Evidence to Preserve

- CI run URL, job logs, deployment logs, manifest render output, image digests, release SHA, and Kubernetes events.
- Health/smoke/contract gate outputs, dashboards, alert payloads, logs/traces, migration output, and feature-flag history.
- Timeline of promotion, failure, containment, rollback/retry, and validation.

## Related Gates

- Deployment smoke and readiness gates.
- `make verify`
- `make contract-tests`
- `make check-migration-heads`
- `pnpm run verify:frontend`
- `pnpm run check:contract-compliance`
- `pnpm run check:api-types`

## Related Runbooks

- [Incident command](../01-incident-command.md)
- [Deploy production release](deploy-production-release.md)
- [Rollback production release](rollback-production-release.md)
- [Failed migration](../database/failed-migration.md)
- [Alert triage](../observability/alert-triage.md)
- [Deployment rollout and rollback](../deployment-rollout-and-rollback.md)

## Post-Incident Follow-Up

- Add missing preflight checks, smoke coverage, deploy automation guardrails, or observability alerts.
- Update release notes and the deployment record with failure cause and evidence.
- Create regression tests for any application, contract, tenant-isolation, or migration issue found.
