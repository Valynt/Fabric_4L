# Respond to Tenant Data Exposure Runbook

## Purpose

Contain, investigate, and remediate suspected or confirmed tenant data exposure, cross-tenant access, tenant context confusion, or authorization bypass in Value Fabric.

## Trigger

- Customer reports seeing another tenant's data.
- Logs, alerts, tests, or audit review indicate `cross.tenant`, `tenant.isolation`, `unauthorized.tenant`, `forbidden.tenant`, inconsistent `tenant_id`, or missing tenant filters.
- Auth bypass, dev tenant override, or request-body tenant trust is detected in production-like environments.
- Repository, API route, workflow, export, benchmark, graph, vector, or cache behavior may have exposed data across tenants.

## Severity

- **SEV1:** All suspected tenant data exposure starts here until Security confirms no cross-tenant data was viewed, modified, exported, or deleted.
- **SEV2:** Tenant-boundary regression was caught before exposure but affects production code or customer-critical path.
- **SEV3:** Non-production tenant-isolation test failure or bounded false positive with no production exposure.
- **SEV4:** Documentation/alert-label issue with no security or data impact.

## Preconditions

- Security on-call, incident commander, affected service owner, Legal/Privacy, and Customer Operations escalation paths are available.
- Access exists to API gateway logs, application logs, traces, audit records, database query evidence, deployment history, and config/secret state.
- Evidence can be preserved before endpoint disablement, session revocation, rollback, restore, or credential rotation.

## Immediate Actions

1. Declare **SEV1 security incident** and open the security incident channel.
2. Freeze risky deploys for affected services unless the deploy is a verified containment fix.
3. Preserve evidence: alert payloads, request IDs, trace IDs, audit logs, API gateway logs, repository/query logs, database snapshots if needed, and current deployment/config state.
4. Contain exposure by disabling the affected endpoint, feature flag, workflow, export, integration, or tenant-specific access path.
5. Revoke active sessions, API keys, or tokens for affected users/tenants when token confusion or credential risk is suspected.
6. Escalate to Security, Legal/Privacy, VP Engineering, and Customer Operations for any confirmed cross-tenant access.

## Diagnosis Steps

1. Identify affected tenants, users, endpoints, workflows, layers, request IDs, and first/last suspicious timestamps.
2. Determine whether data was viewed, modified, exported, deleted, cached, indexed, embedded, or sent to an external provider.
3. Confirm authenticated tenant context from identity middleware and compare it to persisted record `tenant_id` values.
4. Audit recent changes to auth middleware, repository filters, API routes, exports, graph/vector queries, and feature flags.
5. Check production-like config for forbidden dev bypass flags and hardcoded/test tenant overrides.
6. Determine whether downstream layers, caches, search indexes, graph projections, or analytics artifacts propagated exposed data.

## Resolution Steps

1. Keep risky paths disabled until the root cause is fixed and validated.
2. Patch the tenant-context propagation or tenant-scoped query/filter bug in the canonical runtime path.
3. Rotate/revoke credentials or sessions if any identity confusion or leaked access token is involved.
4. Purge or rebuild derived stores, caches, exports, embeddings, and graph/vector projections that may contain cross-tenant data.
5. Add hostile tenant-boundary regression coverage before restoring traffic.
6. Coordinate Legal/Privacy notification requirements before external communications.

## Validation

- Run tenant-boundary/security regression tests for affected code paths.
- Confirm authenticated context, repository filters, database rows, cache keys, graph/vector queries, and exports are tenant-scoped.
- Confirm logs and audit events show denied cross-tenant access and no continuing exposure indicators.
- Confirm affected customer-critical paths still work for legitimate same-tenant access.
- Confirm Security signs off before downgrade or closure.

## Rollback / Fallback

- Keep endpoint/feature/workflow disabled if a safe code fix cannot be validated quickly.
- Roll back the deployment only if the previous version is known to preserve tenant isolation and schema compatibility.
- Use tenant-scoped restore/rebuild for corrupted or exposed derived data; do not run unscoped cleanup.

## Customer / Stakeholder Communication

- Security and Legal/Privacy own external notification content and timing.
- Customer Operations may acknowledge investigation status but must not disclose other tenants, raw data, logs, or unconfirmed root cause.
- Provide updates at SEV1 cadence until containment is confirmed.

## Evidence to Preserve

- Alert payloads, gateway/app logs, traces, request IDs, audit events, database query evidence, snapshots, and affected tenant/user IDs.
- Deployment/config/feature-flag history, auth token/session evidence, repository diffs, validation outputs, and containment actions.
- Legal/Privacy decisions, customer communications, and Security sign-off.

## Related Gates

- `pytest -m "tenant_boundary"`
- `pytest tests/security`
- `make contract-tests`
- `make verify`
- Production safety checks for dev auth bypass flags.
- Contract/API type checks when route shapes or auth behavior changed.

## Related Runbooks

- [Incident command](../01-incident-command.md)
- [Respond to secret leak](respond-to-secret-leak.md)
- [Tenant isolation failure troubleshooting](../../troubleshooting/runbooks/incident/tenant-isolation-failure.md)
- [Tenant isolation operations alert](../../operations/runbooks/tenant-isolation-failure.md)
- [Data breach response](../../troubleshooting/runbooks/incident/data-breach-response.md)
- [Investigate data corruption](../data-governance/investigate-data-corruption.md)

## Post-Incident Follow-Up

- Publish security postmortem with root cause, exposed data classes, affected tenants, containment timeline, and notification decisions.
- Add or strengthen tenant-boundary tests, contract checks, audit alerts, and code review rules.
- Track remediation for derived stores, cache cleanup, customer notification, and compliance evidence.
