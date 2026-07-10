# Runbook: TENANT_ISOLATION_BREACH

**Alert:** `TenantIsolationBreached`  
**Severity:** Critical (P0)  
**Team:** Security + SRE  
**Slack:** #security-incidents (NOT #incidents — security channel)  
**PagerDuty:** Security On-Call + SRE Lead  
**Last Updated:** 2024-06-15

---

> **THIS IS A P0 SECURITY INCIDENT.** Any cross-tenant data access attempt
> represents a potential data breach. This runbook takes precedence over
> all other incidents.

---

## 1. Detection

| Signal | Threshold | Source |
|--------|-----------|--------|
| `increase(cross_tenant_access_attempts_total[1m])` | > 0 | Prometheus |

**Notification:** Immediate PagerDuty page (0s `for` clause — no grace period).

---

## 2. Impact Assessment

### Within 60 seconds of alert:

1. **DO NOT PANIC.** Follow this runbook methodically.
2. **Acknowledge the alert** in PagerDuty immediately.
3. **Create a private Slack channel:** `#security-incident-YYYY-MM-DD`

### Key Questions (answer within 3 minutes)

| Question | How to Find Answer |
|----------|-------------------|
| Source tenant? | `$labels.source_tenant` in alert |
| Target tenant? | `$labels.target_tenant` in alert |
| Which layer? | `$labels.layer` in alert |
| What data was accessed? | Check audit logs (see Step 3) |
| Was it a successful read/write? | Check `cross_tenant_access_successful_total` metric |

### Severity Classification

| Level | Criteria | Response |
|-------|----------|----------|
| P0-Critical | Successful data read/write across tenants | Full incident response, legal notified |
| P0-Attempt | Attempted access blocked by RLS | Full incident response, root cause required |

---

## 3. Step-by-Step Recovery

### Phase 1: Immediate Containment (0-5 minutes)

**DO THESE IN ORDER. DO NOT SKIP STEPS.**

#### Step 1.1: Acknowledge and escalate

```bash
# Post in #security-incidents
@channel P0 SECURITY INCIDENT: Tenant isolation breach detected.
Source: ${SOURCE_TENANT} -> Target: ${TARGET_TENANT}
Layer: ${LAYER}
Time: $(date -u +"%Y-%m-%dT%H:%M:%SZ")
On-call: $(whoami)
Status: CONTAINMENT IN PROGRESS
```

#### Step 1.2: Isolate the source

```bash
# Revoke all sessions for the source tenant's users
kubectl exec -it deploy/keycloak -n fabric4l -- \
  /opt/keycloak/bin/kcadm.sh delete sessions \
  --realm fabric4l \
  --query "tenant=${SOURCE_TENANT}"

# If the source is a specific service account, disable it
kubectl exec -it deploy/keycloak -n fabric4l -- \
  /opt/keycloak/bin/kcadm.sh update users/${USER_ID} \
  --realm fabric4l \
  -s enabled=false
```

#### Step 1.3: Enable emergency audit mode

```bash
# Set all affected services to LOGGING_ONLY mode
# (log all queries but do not execute cross-tenant ones)
kubectl patch configmap fabric4l-security-config -n fabric4l --patch '
{
  "data": {
    "TENANT_ISOLATION_MODE": "LOGGING_ONLY",
    "AUDIT_ALL_QUERIES": "true"
  }
}'

# Rollout restart to pick up config
kubectl rollout restart deployment/${LAYER}-service -n fabric4l
```

### Phase 2: Investigation (5-30 minutes)

#### Step 2.1: Extract audit trail

```sql
-- Connect to PostgreSQL audit log
SELECT
    timestamp,
    tenant_id,
    source_ip,
    query,
    table_name,
    row_count,
    session_user
FROM audit_log
WHERE timestamp > NOW() - INTERVAL '1 hour'
  AND (
    tenant_id != session_tenant_id  -- RLS bypass attempt
    OR query ILIKE '%SET ROLE%'      -- Privilege escalation
  )
ORDER BY timestamp DESC;
```

#### Step 2.2: Check for successful data exfiltration

```promql
# Check if any cross-tenant reads succeeded
sum(increase(cross_tenant_access_successful_total[1h]))

# Check which tables were accessed
sum by (table_name) (increase(cross_tenant_access_attempts_total[1h]))
```

#### Step 2.3: Analyze the attack vector

Common vectors to check:

1. **RLS policy bypass:** Was `set_config('app.current_tenant', ...)` used?
2. **SQL injection:** Check for unsanitized user input in queries
3. **JWT tampering:** Was the tenant claim in the token modified?
4. **Service account compromise:** Was a shared service account used?
5. **Code bug:** Recent deployment introducing a tenant context leak?

```bash
# Check for SET ROLE or SET CONFIG in query logs
kubectl logs -l layer=${LAYER} -n fabric4l --since=1h | \
  grep -iE "set (role|config|search_path)" | head -20
```

### Phase 3: Remediation (30-60 minutes)

#### Step 3.1: Fix the root cause

| Root Cause | Fix |
|------------|-----|
| Code bug | Deploy hotfix with proper tenant scoping |
| RLS policy gap | Add missing RLS policy, verify with `EXPLAIN ANALYZE` |
| JWT validation | Rotate signing keys, validate `tid` claim |
| Service account | Create per-tenant service accounts |

#### Step 3.2: Verify isolation is restored

```bash
# Run isolation test suite
pytest tests/security/test_tenant_isolation.py -v

# Verify all RLS policies are active
psql $DATABASE_URL -c "\d+" | grep -i rls
```

#### Step 3.3: Re-enable normal operation

```bash
# Restore from LOGGING_ONLY to ENFORCE
kubectl patch configmap fabric4l-security-config -n fabric4l --patch '
{
  "data": {
    "TENANT_ISOLATION_MODE": "ENFORCE",
    "AUDIT_ALL_QUERIES": "false"
  }
}'

kubectl rollout restart deployment/${LAYER}-service -n fabric4l
```

### Phase 4: Notification (within 1 hour)

**If any data was successfully accessed:**

1. Notify Legal team immediately
2. Prepare customer notification per DPA terms
3. Document all affected records for forensics

---

## 4. Verification

- [ ] `cross_tenant_access_attempts_total` == 0 for 10 consecutive minutes
- [ ] All RLS policies verified active
- [ ] Tenant isolation test suite passes 100%
- [ ] Audit log shows no further anomalies
- [ ] Source tenant access restored (if legitimate)
- [ ] Security incident report filed

---

## 5. Post-Incident Review

**Within 24 hours (mandatory for ALL tenant isolation incidents):**

1. **Security incident report** filed in Jira (SEC- prefix)
2. **Root cause analysis** with 5 Whys methodology
3. **Preventive measures:**
   - Code review checklist updated
   - RLS policy tests added to CI/CD
   - Additional monitoring implemented
4. **Legal review** if data was accessed
5. **Customer notification** if required by DPA

**Required metrics:**
- Time to containment (target: < 5 min)
- Time to root cause (target: < 30 min)
- Records potentially accessed
- Whether access was blocked by RLS
