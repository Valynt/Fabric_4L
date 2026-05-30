# Respond to Secret Leak Runbook

## Scope

Use this runbook for suspected or confirmed exposure of API keys, service tokens, database credentials, signing keys, Infisical secrets, cloud credentials, Kubernetes secrets, or customer-provided secrets.

## Severity

- **SEV1:** Production secret, signing key, database credential, cloud credential, customer secret, or broadly privileged token is exposed or may have been accessed.
- **SEV2:** Non-production secret with limited blast radius is exposed and no production access is possible.
- **SEV3:** False positive or test credential with no access after Security validation.

## Immediate Actions

1. Declare SEV1 for any production or unknown-scope secret and open the security incident channel.
2. Preserve evidence before deleting or rewriting history: file path, commit SHA, CI logs, secret scanner alert, access logs, and where the secret may have propagated.
3. Revoke or disable the exposed credential at the provider; do not rely only on deleting it from the repository or logs.
4. Rotate dependent credentials and redeploy workloads that consume the rotated secret.
5. Search logs and provider audit trails for use of the exposed credential before and after suspected exposure.
6. If repository history or artifacts exposed the secret, coordinate purge with Security while retaining forensic evidence in approved storage.
7. Assess whether the secret exposure enabled tenant data access; if so, activate tenant data exposure response.

## Diagnosis

```bash
# Identify where the secret appears in tracked files without printing secret values in the incident channel.
git log --all --oneline --decorate -- <path-containing-secret>

# Search for secret-like indicators in recent changes using approved scanners/gates where available.
pre-commit run gitleaks --all-files

# Review recent Kubernetes events and affected workload restarts.
kubectl get events -A --sort-by=.lastTimestamp | tail -100
kubectl rollout status deployment/<service> -n prod --timeout=300s
```

When documenting evidence, redact secret values. Store raw values only in approved security evidence storage if Security explicitly requires them.

## Validation

- Exposed credential is revoked at the authoritative provider and can no longer authenticate.
- Replacement credential is stored in Infisical or the approved secrets manager, not committed to source control.
- All affected workloads are restarted/redeployed and confirmed to use the new secret.
- Logs and provider audit trails are reviewed for unauthorized use.
- Secret scanners/gates pass after remediation.
- Tenant/customer impact assessment is complete and linked to the incident record.

## Evidence to Preserve

- Secret scanner alert, file path, commit SHA, pull request, artifact, or log location where exposure occurred.
- Provider audit logs showing credential creation, use, revocation, and rotation.
- Rotation commands, deployment restart evidence, and validation output.
- Blast-radius analysis: systems, tenants, scopes, permissions, and time window.
- Communication and notification decisions approved by Security and Legal/Privacy.

## Related Gates

- `pre-commit run gitleaks --all-files`
- `make verify`
- `make check-conflict-markers`
- `pnpm --dir apps/web run test:prod-auth-bypass`
- `python3 scripts/ci/k8s_preflight.py`

## Related Runbooks

- [Incident Command](../01-incident-command.md)
- [Respond to Tenant Data Exposure](respond-to-tenant-data-exposure.md)
- [Rollback Production Release](../deployment/rollback-production-release.md)
- [Failed Deployment](../deployment/failed-deployment.md)
- [Auth Provider Outage](../auth/auth-provider-outage.md)
