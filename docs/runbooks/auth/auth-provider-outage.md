# Auth Provider Outage Runbook

## Purpose

Maintain safe access control and customer communication during identity provider, OIDC/JWKS, token verification, session, or RBAC dependency outages without enabling insecure dev bypasses or weakening tenant isolation.

## Trigger

- Auth provider status page reports outage or degraded token/JWKS/session service.
- Spikes in `InvalidToken`, `SignatureVerification`, `TokenExpired`, `AccessDenied`, `RBAC.denied`, login failures, or refresh failures.
- API gateway or services cannot fetch/validate JWKS, introspect tokens, or enforce RBAC.
- Customers report widespread inability to log in or use authenticated APIs.

## Severity

- **SEV1:** Platform-wide auth unavailable, token verification cannot fail closed safely, suspected auth bypass, or tenant-isolation/security impact.
- **SEV2:** Major subset of customers cannot authenticate or tokens fail due to provider degradation with safe fail-closed behavior.
- **SEV3:** Single tenant/client misconfiguration or degraded non-critical auth workflow with workaround.
- **SEV4:** Auth dashboard/alert noise with no customer or security impact.

## Preconditions

- Identity platform owner, Security on-call, incident commander, and Customer Operations are available for production impact.
- Access exists to provider status, gateway logs, auth service logs, JWKS/cache metrics, rate-limit/WAF controls, and customer support reports.
- Approved emergency controls are known; dev auth bypass flags remain forbidden in production.

## Immediate Actions

1. Confirm severity, affected tenants/customers, and whether failures are login-only, token refresh, API authorization, RBAC, or provider connectivity.
2. Freeze auth-related deploys/config changes unless they are verified containment fixes.
3. Preserve provider status, logs, traces, token verification errors, audit events, config diffs, and rate-limit/WAF changes.
4. Verify services fail closed: no unauthenticated access, no hardcoded tenant, no request-body tenant trust, and no dev auth bypass flags.
5. Notify Security immediately if any auth bypass, token confusion, or cross-tenant access is suspected.

## Diagnosis Steps

1. Check provider status page, JWKS endpoint, token issuer/audience configuration, client secret/certificate validity, DNS/network reachability, and clock skew.
2. Compare auth failure rates by tenant, client, region, endpoint, and error type.
3. Review recent IdP configuration changes, key rotation, client secret rotation, deploys, ingress/WAF changes, and rate-limit changes.
4. Determine whether cached JWKS/session validation is operating within approved TTLs and still fail-closed.
5. Distinguish provider outage from credential stuffing, brute force, customer tenant misconfiguration, expired certificates, or platform regression.

## Resolution Steps

1. If provider outage is confirmed, keep authentication enforcement enabled and communicate impact; do not enable insecure bypass.
2. Use approved cached JWKS/session validation only within documented TTL and only if it preserves signature/audience/issuer checks.
3. For platform config regression, roll back the auth config/deployment or restore prior client/JWKS settings.
4. For expired or rotated client credentials, rotate through approved secret-management paths and restart/redeploy affected services.
5. For attack traffic, enable WAF/rate-limit controls and coordinate with Security.
6. For single-tenant IdP misconfiguration, isolate and coordinate with that tenant without changing global auth policy.

## Validation

- Confirm login, token refresh, and authenticated API calls work for affected tenants and at least one unaffected tenant.
- Confirm invalid/expired tokens are rejected and RBAC denies unauthorized actions.
- Confirm no dev auth bypass flags are set in production-like environments.
- Confirm audit events are written for auth success/failure and RBAC decisions.
- Confirm auth failure rates, latency, and provider health return to baseline.

## Rollback / Fallback

- Roll back auth-related deployments/config only to known-safe settings that preserve fail-closed behavior.
- If provider remains down, keep protected APIs unavailable rather than bypassing auth; communicate outage and offer approved operational workarounds only.
- Disable risky integrations or tenant-specific SSO connections if they generate unsafe token confusion.

## Customer / Stakeholder Communication

- Customer Operations should share confirmed auth symptoms, impacted tenants/regions, workaround if any, and next update time.
- Security/Legal must review messaging if auth bypass, tenant exposure, or credential compromise is suspected.
- Do not disclose signing keys, token contents, client secrets, or other tenants' configurations.

## Evidence to Preserve

- Provider status, auth error logs, gateway logs, traces, audit events, config/secret diffs, JWKS cache status, tenant/client impact analysis, and rate-limit/WAF changes.
- Commands run, rotations performed, validation outputs, and customer communications.

## Related Gates

- Production safety validator for dev auth bypass flags.
- Auth/RBAC regression tests and tenant-boundary tests.
- `make verify`
- `make contract-tests`
- Service health/readiness and audit-write validation.

## Related Runbooks

- [Incident command](../01-incident-command.md)
- [Respond to tenant data exposure](../security/respond-to-tenant-data-exposure.md)
- [Respond to secret leak](../security/respond-to-secret-leak.md)
- [Auth anomaly operations runbook](../../operations/runbooks/auth-anomaly.md)
- [Alert triage](../observability/alert-triage.md)

## Post-Incident Follow-Up

- Review IdP SLAs, JWKS cache TTLs, token verification alerting, customer SSO runbooks, and auth dependency dashboards.
- Add regression tests for the failure mode and update customer support macros.
- Track any required provider escalation or tenant configuration remediation.
