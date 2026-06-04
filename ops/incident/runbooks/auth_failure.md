# Auth Failure Runbook

## Purpose

Restore authentication and authorization safely while preserving fail-closed
behavior, tenant isolation, audit logging, and customer trust.

## Trigger

- Login failures, token validation failures, OIDC/SSO outage, auth provider
  errors, unexpected 401/403 spikes, or suspected auth bypass.
- Production startup failure from unsafe auth bypass flags.

## Severity

- SEV-1 when auth fails open, auth bypass is suspected, credentials are exposed,
  cross-tenant access is possible, or most customers cannot authenticate.
- SEV-2 when a major auth path is unavailable but sessions or workarounds remain.
- SEV-3 when impact is isolated to one tenant, identity provider, or non-critical
  admin path with no security risk.

## Preconditions

- Access to identity provider status, auth service logs, audit events, token
  validation metrics, config/secret history, and recent deploy records.
- Security approval before changing auth enforcement, rotating credentials, or
  making security-impacting customer statements.

## Immediate Actions

1. Classify high until evidence proves auth is failing closed and tenant
   isolation is intact.
2. Engage Security immediately for suspected bypass, credential exposure, or
   cross-tenant risk.
3. Capture affected auth flow, tenant/customer reports, token validation errors,
   recent secret/config changes, and audit events.
4. Do not enable dev auth bypass flags or weaken middleware in production.

## Diagnosis Steps

1. Determine whether failures are login, session refresh, token validation,
   OIDC/SSO provider, RBAC, tenant resolution, or middleware startup.
2. Check provider status, JWKS/certificate rotation, clock skew, secret
   versions, redirect URIs, and environment-specific config.
3. Confirm protected routes still reject unauthenticated requests.
4. Confirm tenant context is derived from authenticated claims and propagated to
   repository/service calls.
5. Inspect audit logs for anomalous access, privilege changes, or repeated
   failed attempts.

## Resolution Steps

1. Restore the failing auth dependency or roll back correlated auth config.
2. Rotate credentials only with Security approval and documented blast-radius
   analysis.
3. Revert any deploy that changed token parsing, RBAC, tenant context, or auth
   middleware if correlated with failure.
4. Keep fail-closed behavior even if availability remains degraded.

## Validation

- Successful login and token refresh for representative auth flows.
- Protected routes reject unauthenticated and unauthorized requests.
- Tenant A cannot access Tenant B data.
- Audit logs capture auth and administrative actions.
- Production safety checks reject dev auth bypass flags.

## Rollback / Fallback

- Roll back the last auth config or code change when correlated.
- If the identity provider is unavailable, preserve existing valid sessions only
  if policy allows and no security risk exists.

## Customer / Stakeholder Communication

- Communicate login or SSO symptoms and next update time.
- Do not state breach/no-breach conclusions externally until Security and Legal
  approve.

## Evidence to Preserve

- Auth logs, audit events, token validation metrics, provider status, secret
  version metadata, config diffs, deployment SHA, failed request IDs, and
  validation output.

## Escalation

- Escalate to Identity Platform, Security, SRE, affected service owners,
  Legal/Privacy for potential data impact, and Customer Operations for tenant
  SSO communications.

## Related Runbooks

- [Incident response workflow](../README.md)
- [API outage](api_outage.md)
- [Respond to secret leak](../../../docs/runbooks/security/respond-to-secret-leak.md)
- [Incident command](../../../docs/runbooks/01-incident-command.md)

## Post-Incident Follow-Up

- Add or update auth regression tests, tenant-boundary tests, provider rotation
  runbooks, audit checks, and startup safety gates.
