# Auth Provider Outage Runbook

## Scope

Use this runbook when Keycloak, enterprise OIDC, identity middleware, token validation, JWKS retrieval, session issuance, or login/logout flows are degraded or unavailable.

## Severity

- **SEV1:** Authentication outage blocks most production users, token validation fails across services, or auth degradation creates a security/tenant-isolation risk.
- **SEV2:** One auth integration or tenant SSO provider is unavailable with limited workaround.
- **SEV3:** Intermittent login failures or degraded non-critical auth feature with no security risk.

## Immediate Actions

1. Declare incident severity based on customer impact and security risk.
2. Confirm whether existing authenticated sessions continue to work or whether token validation is failing globally.
3. Preserve gateway, identity middleware, Keycloak/OIDC provider, JWKS, and audit logs before restarts.
4. Do not enable development auth bypass flags in production or production-like environments.
5. If a third-party identity provider is down, communicate workaround and expected provider status cadence.
6. If token validation is unsafe or tenant claims are inconsistent, fail closed and activate tenant data exposure response.
7. Coordinate rollback only if a recent release changed auth, middleware, secrets, JWKS, redirects, or OIDC configuration.

## Diagnosis

```bash
# Check API gateway/auth middleware logs for auth failures.
kubectl logs -n value-fabric -l app=api-gateway --since=30m | rg -i "oidc|jwks|token|session|unauthorized|forbidden|keycloak|tenant"

# Check Keycloak or auth provider pods if self-hosted.
kubectl get pods -n value-fabric -l app=keycloak -o wide
kubectl logs -n value-fabric -l app=keycloak --since=30m --tail=200

# Verify forbidden dev bypass flags are not present.
kubectl get configmaps,secrets -n value-fabric -o yaml | rg -i "DEV_AUTH_BYPASS|ALLOW_DEV_AUTH_BYPASS|AUTH_BYPASS_ENABLED|ALLOW_INSECURE_DEV_AUTH_BYPASS"

# Inspect recent auth-related changes.
git log --oneline --since='72 hours ago' -- services packages value_fabric apps/web k8s .env.example
```

## Validation

- Login, token refresh, logout, and existing-session validation behavior are understood and documented.
- Services fail closed when token validation cannot establish authenticated tenant context.
- No production bypass flags are enabled.
- Affected tenants/providers are identified and workaround/status messaging is approved.
- Auth logs show recovery, and API gateway error rate returns to normal.
- Tenant-boundary tests or targeted auth regression tests pass before closure when code/config changed.

## Evidence to Preserve

- Gateway and identity middleware logs with request IDs and trace IDs.
- Keycloak/OIDC provider logs, status page entries, JWKS fetch errors, and token validation errors.
- Config/secret change history with secret values redacted.
- Recent release SHA or rollback evidence if auth code/config changed.
- Customer impact list and communication approvals.

## Related Gates

- `pnpm --dir apps/web run test:prod-auth-bypass`
- `pytest -m "tenant_boundary"`
- `pytest tests/security`
- `make contract-tests`
- `make verify`
- `python3 scripts/ci/k8s_preflight.py`

## Related Runbooks

- [Incident Command](../01-incident-command.md)
- [Respond to Tenant Data Exposure](../security/respond-to-tenant-data-exposure.md)
- [Respond to Secret Leak](../security/respond-to-secret-leak.md)
- [Rollback Production Release](../deployment/rollback-production-release.md)
- [Failed Deployment](../deployment/failed-deployment.md)
- [Alert Triage](../observability/alert-triage.md)
