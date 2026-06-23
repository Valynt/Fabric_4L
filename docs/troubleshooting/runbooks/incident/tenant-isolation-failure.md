# Tenant Isolation Failure Runbook

Use this runbook when cross-tenant access, tenant context confusion, authorization bypass, or tenant-scoped repository drift is suspected. This is a **SEV1 security incident** until Security confirms no cross-tenant data exposure occurred.

## Triggers

- Customer reports seeing another tenant's data.
- Logs include `cross.tenant`, `tenant.isolation`, `unauthorized.tenant`, `forbidden.tenant`, or inconsistent `tenant_id` values.
- A service returns records whose persisted tenant does not match authenticated tenant context.
- Tests, monitoring, or audit review finds a missing `tenant_id` filter in production code.
- Auth bypass or development tenant override is detected in a production-like environment.

## Immediate response

1. **Declare SEV1** and open `#security-incidents`.
2. **Freeze risky deploys** for affected services unless the deploy is a verified containment fix.
3. **Preserve evidence:** alert payloads, request IDs, trace IDs, audit logs, API gateway logs, repository query logs, and database snapshots if needed.
4. **Contain exposure:** disable affected endpoint, feature flag, workflow, or tenant integration if cross-tenant reads/writes may be active.
5. **Revoke active sessions** for affected users or tenants when token confusion is suspected.
6. **Escalate to Security, Legal/Privacy, and VP Engineering** for any confirmed cross-tenant data access.

## Diagnosis

```bash
# Search recent logs for tenant isolation indicators.
kubectl logs -n value-fabric --all-containers --since=1h | rg -i "cross.tenant|tenant.isolation|unauthorized.tenant|forbidden.tenant|tenant_id"

# Pull API gateway logs for a known trace or request ID.
kubectl logs -n value-fabric -l app=api-gateway --since=2h | rg "<trace_id>|<request_id>"

# Inspect recent code changes touching auth, middleware, repositories, or API routes.
git log --oneline --since='48 hours ago' -- services packages value_fabric contracts apps/web

# Check production-like config for forbidden dev bypass flags.
kubectl get configmaps,secrets -n value-fabric -o yaml | rg -i "DEV_AUTH_BYPASS|ALLOW_DEV_AUTH_BYPASS|AUTH_BYPASS_ENABLED|ALLOW_INSECURE_DEV_AUTH_BYPASS|TEST_ORG_ID"
```

## Scope assessment

| Question | Evidence source |
|---|---|
| Which tenants were affected? | API gateway logs, audit events, database query logs, application traces. |
| Was data viewed, modified, exported, or deleted? | Audit logs, repository write logs, object access logs, database WAL/query logs. |
| Which endpoint or workflow allowed the mismatch? | Route logs, trace spans, recent deploy diff, feature flag history. |
| Was the authenticated context correct? | Identity middleware logs, token claims, session records, gateway headers. |
| Did downstream layers propagate the wrong tenant? | L1-L6 service logs, queue payloads, workflow checkpoints, tool-call traces. |

## Containment patterns

- Disable the affected route at the gateway or ingress.
- Disable the feature flag, workflow, agent tool, scheduled job, or queue consumer causing leakage.
- Add a temporary deny rule for affected tenants if necessary to prevent further exposure.
- Roll back the deploy only if rollback restores verified tenant filtering.
- If data was written under the wrong tenant, stop dependent consumers before cleanup.

## Remediation checklist

1. Fix the canonical source path for the affected service.
2. Ensure tenant context comes from authenticated context, not request body or client-provided headers.
3. Confirm every repository query and write filters or persists `tenant_id`.
4. Add hostile cross-tenant regression tests for read, write, list, export, and workflow resume paths.
5. Update OpenAPI/contracts/types only if the public API behavior intentionally changes.
6. Run targeted tests and tenant-boundary checks before re-enabling traffic.
7. Validate production logs for absence of new cross-tenant indicators after mitigation.

## Customer and compliance handling

- Follow [data-breach-response.md](data-breach-response.md) if any customer data may have been exposed.
- Use [communication-template.md](communication-template.md) for status updates and customer language.
- Legal/Privacy decides notification obligations after Security documents scope.
- Preserve all evidence until Legal approves deletion or retention transfer.

## Closure criteria

- Affected endpoint or workflow is safely restored or permanently disabled.
- Security confirms no ongoing cross-tenant exposure.
- Impacted tenants and records are identified or explicitly ruled out.
- Regression tests protect the failed path.
- Audit and monitoring coverage are updated for the detected failure mode.
- Post-mortem and corrective actions are complete.
