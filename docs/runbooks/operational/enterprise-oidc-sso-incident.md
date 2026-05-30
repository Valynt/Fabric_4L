# Enterprise OIDC / SSO Incident Runbook

## Purpose

Diagnose and remediate enterprise OIDC/SSO failures while keeping authentication fail-closed and tenant mappings safe.

## Trigger

Enterprise login outage, callback validation failure, JWKS/issuer/audience mismatch, tenant claim drift, or SSO security alert.

## Severity

SEV-1 for broad production login outage or auth bypass risk; SEV-2 for one tenant/provider affected; SEV-3 for staging or metadata drift.

## Preconditions

Provider metadata, JWKS URI, callback logs, tenant mapping records, audit logs, and security owner approval are available.

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

Tenant-isolation/security gates: enterprise SSO contract tests, production auth-bypass gate, tenant boundary tests, audit emission checks, deployment gates for auth config changes, and observability alert gates for auth failures.

## Related Runbooks

- [Abuse Emergency Controls Runbook](abuse-emergency-controls.md)
- [CI Infisical OIDC Recovery and Secret Rotation](ci-infisical-oidc-recovery.md)

## Post-Incident Follow-Up

- Attach validation evidence and gate results to the incident record.
- File corrective actions for missing alerts, missing tests, stale documentation, or slow recovery steps.
- Update this runbook and related gates if the incident exposed drift or an undocumented dependency.

---

## Procedure Details

This runbook covers enterprise identity-provider incidents affecting Fabric_4L user login, tenant mapping, token validation, and session lifecycle behavior. It assumes local password fallback is disabled for production enterprise tenants unless an explicitly approved break-glass procedure is active.

### Severity Classification

| Severity | Condition | Expected response |
|---|---|---|
| SEV-1 | All enterprise users cannot authenticate, callback validation fails globally, or token signature validation is broken. | Page on-call immediately, freeze identity-related deployments, and keep authentication fail-closed. |
| SEV-2 | One tenant or provider integration is degraded, tenant mapping fails, or logout/session expiry is inconsistent. | Notify tenant owner, route incident to identity steward, and preserve audit evidence. |
| SEV-3 | Non-production provider metadata, documentation, or configuration drift is detected. | Open a tracked remediation ticket and validate before next release. |

### Immediate Checks

Confirm whether the provider discovery document, JWKS endpoint, authorization endpoint, token endpoint, and callback route are reachable from the deployment network. Do not paste provider secrets into logs or tickets. Capture only sanitized provider URL, HTTP status, request ID, tenant ID, and timestamp.

Canonical runtime auth boundaries and integration points:
- Shared identity boundary: `packages/shared/src/value_fabric/shared/identity/` (JWT decode, JWKS resolution, auth context, middleware, dependency gates).
- Service middleware entrypoints: each service `api/main.py` (or equivalent) where `GovernanceMiddleware` is mounted.
- Layer 4 OAuth callback boundary: `services/layer4-agents/src/api/routes/integrations.py` (`/v1/integrations/salesforce/oauth/callback`).

Configuration and secret-management guardrail:
- Keep `OIDC_ISSUER`, `OIDC_AUDIENCE`, `OIDC_JWKS_URL`/`OIDC_JWKS_JSON`, and callback state-signing secrets in Infisical/Vault (or ExternalSecrets-backed injection), not in repo-tracked environment files.
- `.env.example` documents contract keys only; production values must come from secret manager paths.

| Check | Command or evidence | Pass criterion |
|---|---|---|
| Discovery metadata | Fetch configured issuer metadata from the deployment environment. | HTTP 200 and issuer matches configured issuer exactly. |
| JWKS | Fetch configured JWKS URI. | HTTP 200 and active key ID matches token header. |
| Callback route | Exercise authorization-code callback in staging or break-glass diagnostic flow. | State, nonce, PKCE, signature, audience, expiry, and tenant mapping pass. |
| Audit emission | Query audit events for login success/failure. | Auth events include tenant, subject hash, provider, and outcome. |

### Remediation Procedure

Keep authentication fail-closed while diagnosing signature, issuer, audience, or tenant-claim mismatches. If a provider key rotation caused the incident, refresh JWKS cache and confirm the old and new key IDs are handled according to provider policy. If tenant mapping fails, disable only the affected tenant mapping and require explicit allow-list review before re-enabling fallback claims such as `org_id` or `hd`.

### Closure Evidence

The incident can close only after the affected tenant can complete login and logout, the callback route validates claims with the current provider keys, audit events exist for success and failure paths, and the post-incident review links the root cause to a preventive control.
