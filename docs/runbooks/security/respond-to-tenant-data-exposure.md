# Respond to Tenant Data Exposure Runbook

## Scope

Use this runbook for suspected or confirmed cross-tenant access, tenant context confusion, authorization bypass, missing tenant filters, or exposure of one tenant's data to another tenant. It consolidates the existing tenant-isolation and data-breach response guidance.

## Severity

Tenant data exposure is **SEV1** until Security confirms in writing that no cross-tenant data was exposed. Downgrades require documented evidence, decision maker, and timestamp.

## Immediate Actions

1. Declare SEV1 and open the security incident channel.
2. Assign Incident Commander, Security Lead, Forensics Lead, Communications Lead, Legal/Privacy contact, and service Technical Lead.
3. Freeze risky deploys for affected services unless the deploy is a verified containment fix.
4. Preserve alert payloads, request IDs, trace IDs, audit logs, API gateway logs, repository query logs, queue payloads, and database snapshots if needed.
5. Contain exposure by disabling the affected endpoint, feature flag, workflow, scheduled job, agent tool, queue consumer, or tenant integration.
6. Revoke active sessions or API keys for affected users/tenants when token confusion or credential misuse is possible.
7. Start legal/privacy notification assessment as soon as customer or personal data may have been exposed.

## Diagnosis

```bash
# Search recent logs for tenant isolation indicators.
kubectl logs -n value-fabric --all-containers --since=1h | rg -i "cross.tenant|tenant.isolation|unauthorized.tenant|forbidden.tenant|tenant_id"

# Pull gateway logs for a known trace or request ID.
kubectl logs -n value-fabric -l app=api-gateway --since=2h | rg "<trace_id>|<request_id>"

# Inspect recent changes touching auth, middleware, repositories, routes, contracts, or frontend consumers.
git log --oneline --since='48 hours ago' -- services packages value_fabric contracts apps/web

# Check production-like config for forbidden development bypass flags.
kubectl get configmaps,secrets -n value-fabric -o yaml | rg -i "DEV_AUTH_BYPASS|ALLOW_DEV_AUTH_BYPASS|AUTH_BYPASS_ENABLED|ALLOW_INSECURE_DEV_AUTH_BYPASS|TEST_ORG_ID"
```

## Validation

- Active exposure path is disabled, rolled back, or fixed and verified.
- Affected tenants, users, records, endpoints, workflows, and time window are identified or explicitly ruled out.
- Authenticated tenant context is the only source of trusted `tenant_id`; request bodies and client-provided headers are not trusted.
- Repository reads/writes filter or persist `tenant_id` correctly.
- Hostile cross-tenant regression tests cover read, write, list, export, and workflow resume paths where applicable.
- Security and Legal/Privacy approve scope, notification decisions, and closure.

## Evidence to Preserve

- Alert payloads, log excerpts, request IDs, trace IDs, session IDs, and user IDs.
- API gateway, identity middleware, repository, database, audit, and object access logs.
- Feature flag/config history and release SHAs for affected services.
- Database snapshots or query exports needed for scope assessment.
- Customer reports, communication approvals, and notification decision records.

## Related Gates

- `pytest -m "tenant_boundary"`
- `pytest tests/security`
- `make contract-tests`
- `make verify`
- `pnpm run check:contract-compliance`
- `pnpm run check:api-types`
- `pnpm --dir apps/web run test:prod-auth-bypass`

## Related Runbooks

- [Incident Command](../01-incident-command.md)
- [Respond to Secret Leak](respond-to-secret-leak.md)
- [Rollback Production Release](../deployment/rollback-production-release.md)
- [Failed Migration](../database/failed-migration.md)
- [Restore Postgres From Backup](../database/restore-postgres-from-backup.md)
- [Alert Triage](../observability/alert-triage.md)
