# Respond to Secret Leak Runbook

## Purpose

Contain and remediate suspected or confirmed exposure of credentials, API keys, signing keys, database passwords, provider tokens, Infisical material, Kubernetes secrets, or CI/CD tokens.

## Trigger

- Secret scanning alert, customer or employee report, suspicious repository diff, leaked CI log, exposed environment file, compromised pod/secret, or provider abuse signal.
- Detection of production credentials in Git history, issue/PR comments, logs, telemetry, screenshots, artifacts, or third-party systems.
- Unexpected auth/provider activity indicating credential compromise.

## Severity

- **SEV1:** Production secret, signing key, database credential, tenant data access credential, CI/CD deploy credential, or active provider token exposed or suspected compromised.
- **SEV2:** Non-production secret exposed with path to production, broad internal credential, or inactive production credential with uncertain use.
- **SEV3:** Revoked/non-sensitive test secret or false positive requiring cleanup.
- **SEV4:** Documentation-only scanner noise with no credential material.

## Preconditions

- Security on-call and secret owner are available.
- Access exists to secret manager, provider consoles, CI/CD settings, Kubernetes namespaces, audit logs, and affected repositories/artifacts.
- Rotation plan and dependent service restart/redeploy plan are known.

## Immediate Actions

1. Declare security incident at the appropriate severity; default to SEV1 for production or unknown secrets.
2. Preserve evidence without amplifying exposure: alert metadata, file path, commit SHA, artifact/log URL, timestamp, suspected secret type, and access logs. Do not paste the secret into incident channels.
3. Revoke or disable the exposed credential immediately if it can grant production, customer data, deploy, or provider access.
4. Rotate replacement credentials through approved secret-management paths.
5. Purge or restrict public/internal exposure surfaces where possible: logs, artifacts, comments, caches, package registries, and repository history handling coordinated by Security.
6. Check for active misuse using provider, audit, API gateway, and database logs.

## Diagnosis Steps

1. Classify the secret type, scope, privileges, environment, owner, creation time, and last rotation time.
2. Determine exposure window and locations: Git history, CI logs, artifacts, observability backend, screenshots, support tickets, or external leak.
3. Identify all consumers and dependent services that need updated secret references or restarts.
4. Review audit/provider logs for usage from unknown IPs, unusual tenants, failed/successful auth, deploy actions, data export, or privilege escalation.
5. Determine whether tenant data exposure, auth compromise, or malicious deployment occurred.

## Resolution Steps

1. Revoke the leaked credential and verify revocation in the provider/secret manager.
2. Create and store replacement secrets only in approved secret-management systems.
3. Redeploy/restart affected services to consume rotated values, using a controlled release or emergency change.
4. Rotate downstream credentials if the leaked secret could access other secrets or signing material.
5. Remove or restrict leaked artifacts according to Security guidance; do not rewrite shared history without approval.
6. If misuse is detected, branch into tenant data exposure or incident command runbooks.

## Validation

- Confirm old credential no longer authenticates.
- Confirm new credential is active only for intended services and permissions.
- Confirm affected services are healthy after rotation and no secret value appears in logs/artifacts.
- Confirm audit/provider logs show no continuing misuse.
- Confirm scanners pass for the affected repository/artifact scope.

## Rollback / Fallback

- Do not roll back to a deployment/configuration containing the leaked secret.
- If rotation breaks service, keep the old secret revoked and fix dependent configuration or temporarily disable affected functionality.
- Use least-privilege temporary credentials only with Security approval and a documented expiry.

## Customer / Stakeholder Communication

- Security and Legal/Privacy determine external notification when customer data, tenant isolation, regulated data, or provider abuse is implicated.
- Internal updates should include scope, revocation status, service impact, and next update time without revealing secret values.

## Evidence to Preserve

- Secret scanner alert ID, commit SHA/file path/artifact URL, timestamps, credential owner, provider audit logs, access logs, rotation actions, and revocation confirmation.
- List of affected services, redeploy/restart evidence, validation output, and Security/Legal decisions.

## Related Gates

- Secret scanning/pre-commit hooks.
- `make verify`
- Production safety validation for forbidden dev auth bypass flags.
- CI/CD deploy credential and Infisical/OIDC validation.
- Service health and smoke checks after rotation.

## Related Runbooks

- [Incident command](../01-incident-command.md)
- [Respond to tenant data exposure](respond-to-tenant-data-exposure.md)
- [CI Infisical OIDC recovery and secret rotation](../operational/ci-infisical-oidc-recovery.md)
- [Auth provider outage](../auth/auth-provider-outage.md)
- [Failed deployment](../deployment/failed-deployment.md)

## Post-Incident Follow-Up

- Reduce credential scope, add expiry/rotation automation, strengthen scanners, and remove secret logging paths.
- Add regression tests or CI policy if a code path emitted secrets.
- Document final exposure window, misuse assessment, rotated credentials, and remaining customer/compliance actions.
