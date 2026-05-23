# Runbook: TenantIsolationFailure

## Overview

Cross-tenant access patterns or unauthorized tenant context mutations have been detected in application logs. This is a **security-critical** alert because it indicates a potential breach of the platform’s primary isolation boundary. Every read or write in Value Fabric must be scoped by an authenticated `tenant_id`.

## Trigger

- **Alert:** `LogTenantIsolationFailure` (Loki ruler) / `AuthBruteforcePattern` (Prometheus, related)
- **Dashboard:** [Value Fabric Security](../../monitoring/grafana/dashboards/value-fabric-security.json) (if available)
- **Detection:**
  - Loki query: `sum by (layer, service) (rate({job="fluent-bit"} |~ "cross.tenant|tenant.isolation|unauthorized.tenant|forbidden.tenant" [5m])) > 0`
  - Sustained for 2 minutes

## Impact

- **Severity:** P0 - Critical (security)
- **User Impact:** Potential data leakage between tenants
- **Business Impact:** Compliance violation (SOC 2, GDPR), contractual breach, reputational damage
- **Data Impact:** Unknown; assume compromise until proven otherwise

## Diagnosis

### 1. Identify the Source Immediately

```bash
# Extract the exact log lines triggering the alert
logcli query '{job="fluent-bit"} |~ "cross.tenant|tenant.isolation|unauthorized.tenant|forbidden.tenant"' --since=15m --limit=500

# In Grafana Loki, run with extracted fields:
# {job="fluent-bit"} |~ "cross.tenant|tenant.isolation|unauthorized.tenant|forbidden.tenant" | json | line_format "{{.layer}} / {{.service}} / {{.trace_id}}"
```

### 2. Determine Scope

```bash
# Count unique tenant pairs involved
kubectl logs -n value-fabric -l app=<service> --since=15m | grep -iE "cross.tenant|unauthorized.tenant" | awk '{print $NF}' | sort | uniq -c | sort -rn

# Check auth middleware logs for the same trace IDs
kubectl logs -n value-fabric -l app=api-gateway --since=15m | grep <trace_id>
```

### 3. Verify Repository Layer Filters

```bash
# Quick code audit: confirm tenant_id is passed to the query
kubectl exec -n value-fabric deployment/<service> -- grep -rn "tenant_id" src/repositories/ | head -20

# Check if any recent commit touched auth or repository filtering
git log --oneline -10 -- services/<service>/src/repositories/ services/<service>/src/auth/
```

### 4. Check for Known Test Overrides

```bash
# Ensure no TEST_ORG_ID or hardcoded tenant is active in production
kubectl get configmaps -n value-fabric -o yaml | grep -iE "test_org|hardcoded_tenant|bypass"
kubectl get secrets -n value-fabric -o yaml | grep -iE "test_org|hardcoded_tenant|bypass"
```

## Resolution

| Scenario | Action |
|---|---|
| Logged exception (isolation caught the breach) | Verify no data was returned; fix the caller if it’s a code path bug |
| Actual cross-tenant data returned | **Immediate:** revoke affected sessions; rotate API keys for impacted tenants; open security incident |
| Auth override misconfiguration | Remove override; verify `make verify` tenant-boundary tests pass |
| Race condition in middleware | Add request-scoped tenant validation; backfill integration tests |
| False positive (log text match) | Refine LogQL regex to exclude test fixtures and expected log patterns |

## Escalation

1. **On-call engineer** acknowledges within 2 minutes; do not silence without investigation
2. **If any confirmed cross-tenant data access**, immediately page Security Lead and VP Engineering
3. **If tenant count > 1 affected**, declare Security Incident and follow [Incident Response Playbook](../severity-escalation-policy.md)
4. **Compliance notification** may be required within 72 hours if personal data is involved

## Post-Incident

- Add or strengthen `tests/security/test_cross_tenant_hostile.py` regression case
- Update the alert regex if false-positive
- Document root cause in `#security-incidents` with timeline and remediation
