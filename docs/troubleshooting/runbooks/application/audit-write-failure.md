# Runbook: Audit Write Failure

## Overview

Audit log writes are failing, potentially causing compliance violations and loss of critical security event records. The audit system (shared/audit/) provides append-only logging for all cross-layer operations.

## Symptoms

- **Alert:** `AuditWriteFailure`
- **Dashboard:** [Audit Overview](../../monitoring/grafana/dashboards/audit-overview.json)
- **Log Query:**
  ```
  {layer=~"layer1|layer2|layer3|layer4|layer5|layer6"} |= "audit_write_failed\|audit_emitter\|append-only"
  or
  {layer=~"layer1|layer2|layer3|layer4|layer5|layer6"} |= "AuditWriteError\|audit_log_failure\|compliance_audit"
  ```
- **User Impact:** Operations may appear successful but audit trail is incomplete, compliance gaps, potential regulatory exposure
- **Metrics:**
  - `increase(value_fabric_audit_write_failures_total[5m]) > 0`
  - `value_fabric_audit_queue_depth > 100`
  - Database connection errors in audit emitter logs

## Diagnosis

### 1. Check Audit Emitter Health

```bash
# Check audit-specific health across all layers
for layer in layer1-ingestion layer2-extraction layer3-knowledge layer4-agents layer5-ground-truth; do
  echo "=== $layer ==="
  kubectl exec -n value-fabric -it deployment/$layer -- \
    curl -s http://localhost:8000/health | jq '.dependencies.audit // .dependencies.postgres // empty'
done
```

### 2. Inspect Audit Logs

```bash
# Check Layer 4 audit emitter logs (primary audit service)
kubectl logs -n value-fabric -l app=layer4-agents --tail=500 | grep -E "audit|AUDIT|emitter"

# Look for specific write failure patterns
kubectl logs -n value-fabric -l app=layer4-agents | grep -E \
  "audit_write_failed|AuditWriteError|append.*failed|DB constraint violation"

# Check shared audit module logs
kubectl logs -n value-fabric -l app=layer4-agents | grep -E \
  "shared.audit|audit_emitter|AuditEntry"
```

### 3. Verify PostgreSQL Audit Database

```bash
# Check audit database connectivity
kubectl exec -n value-fabric -it deployment/postgres -- \
  psql -U postgres -d value_fabric_audit -c "SELECT COUNT(*) FROM audit_log WHERE created_at > NOW() - INTERVAL '5 minutes';"

# Check for locks blocking audit writes
kubectl exec -n value-fabric -it deployment/postgres -- \
  psql -U postgres -d value_fabric_audit -c "
  SELECT pid, state, query_start, query
  FROM pg_stat_activity
  WHERE state = 'active'
  AND query_start < NOW() - INTERVAL '5 minutes'
  AND query LIKE '%audit%';
"

# Check disk space on audit tablespace
kubectl exec -n value-fabric -it deployment/postgres -- \
  psql -U postgres -c "
  SELECT spcname, pg_size_pretty(pg_tablespace_size(spcname))
  FROM pg_tablespace
  WHERE spcname LIKE '%audit%';
"
```

### 4. Check Audit Queue Status

Async audit Redis queues are namespaced by deployment context so environments
and services sharing a Redis instance cannot consume each other's audit events.
The runtime key format is:

```text
audit:<environment>:<service-name>:pending
audit:<environment>:<service-name>:dead-letter
```

- `<environment>` comes from `ENVIRONMENT`, then `APP_ENV`, then the fallback
  `development`.
- `<service-name>` comes from `SERVICE_NAME`, then the fallback `value-fabric`.
- Components are lower-cased and normalized to Redis-key-safe characters.
- `AUDIT_REDIS_KEY_PREFIX` is a temporary compatibility override. Setting it to
  `audit` keeps the legacy keys `audit:pending` and `audit:dead-letter`; setting
  it to another prefix uses `<prefix>:pending` and `<prefix>:dead-letter`.

```bash
# Set these to the values configured on the affected deployment.
ENVIRONMENT=production
SERVICE_NAME=layer4-agents
PENDING_KEY="audit:${ENVIRONMENT}:${SERVICE_NAME}:pending"
DEAD_LETTER_KEY="audit:${ENVIRONMENT}:${SERVICE_NAME}:dead-letter"

# Check Redis audit queue depth (if using async audit)
kubectl exec -n value-fabric -it deployment/redis -- \
  redis-cli LLEN "${PENDING_KEY}"

# Check for stale audit messages
kubectl exec -n value-fabric -it deployment/redis -- \
  redis-cli LRANGE "${PENDING_KEY}" 0 10

# Check dead-letter backlog
kubectl exec -n value-fabric -it deployment/redis -- \
  redis-cli LLEN "${DEAD_LETTER_KEY}"
```

#### Operational migration plan for existing audit Redis queues

Use `AUDIT_REDIS_KEY_PREFIX=audit` only as a short-lived rollback bridge while
old workers still need to drain `audit:pending` and `audit:dead-letter`. For a
normal migration to namespaced queues:

1. Identify each deployment's target `ENVIRONMENT` or `APP_ENV` and
   `SERVICE_NAME`, and calculate the target pending and dead-letter keys using
   the format above.
2. Pause audit queue workers for the deployment, or scale them to zero, so Redis
   lists do not change while messages are copied.
3. Copy any existing legacy backlog from `audit:pending` to the target pending
   key, preserving list order. Copy `audit:dead-letter` to the target
   dead-letter key for operator replay/inspection continuity.
4. Deploy workers without `AUDIT_REDIS_KEY_PREFIX` so they read/write the
   namespaced keys. Keep producers and workers on the same environment/service
   values.
5. Verify `LLEN` on the namespaced pending key decreases as workers drain, and
   verify legacy key lengths remain zero or unchanged after cutover.
6. Remove `AUDIT_REDIS_KEY_PREFIX` from manifests and secret stores after all
   environments have migrated; keep the old legacy keys until the audit
   retention window has elapsed, then delete them during a scheduled
   maintenance window.

### 5. Inspect Audit Table Constraints

```bash
# Verify audit_log table structure and constraints
kubectl exec -n value-fabric -it deployment/postgres -- \
  psql -U postgres -d value_fabric_audit -c "
  SELECT conname, pg_get_constraintdef(oid)
  FROM pg_constraint
  WHERE conrelid = 'audit_log'::regclass;
"

# Check recent failed insert attempts
kubectl exec -n value-fabric -it deployment/postgres -- \
  psql -U postgres -d value_fabric_audit -c "
  SELECT pg_last_error_message();
"
```

## Remediation

### Immediate Actions (P0)

1. **Restart Audit Emitter (if connection pool exhausted)**
   ```bash
   # Restart Layer 4 agents (contains audit emitter)
   kubectl rollout restart deployment/layer4-agents -n value-fabric

   # Wait for rollout
   kubectl rollout status deployment/layer4-agents -n value-fabric --timeout=120s

   # Verify health
   kubectl exec -n value-fabric -it deployment/layer4-agents -- \
     curl -s http://localhost:8000/health | jq '.dependencies.postgres'
   ```

2. **Clear Audit Queue Backlog (if Redis queue overflow)**
   ```bash
   # Check queue depth first
   QUEUE_DEPTH=$(kubectl exec -n value-fabric -it deployment/redis -- redis-cli LLEN audit_queue)

   # If queue > 10000, drain and alert (data may be lost)
   if [ $QUEUE_DEPTH -gt 10000 ]; then
     kubectl exec -n value-fabric -it deployment/redis -- \
       redis-cli LTRIM audit_queue 0 9999
     echo "ALERT: Audit queue truncated, potential data loss"
   fi
   ```

3. **Fix Database Connection Pool**
   ```bash
   # Increase connection pool for audit writes
   kubectl set env deployment/layer4-agents \
     AUDIT_DB_POOL_SIZE=20 \
     AUDIT_DB_MAX_OVERFLOW=10 \
     AUDIT_WRITE_TIMEOUT_MS=5000

   # Restart to apply
   kubectl rollout restart deployment/layer4-agents -n value-fabric
   ```

### Short-Term Mitigation (P1)

4. **Enable Audit Buffer Mode (async writes)**
   ```bash
   # Switch to async audit mode to prevent blocking operations
   kubectl set env deployment/layer4-agents \
     AUDIT_MODE=async \
     AUDIT_BUFFER_SIZE=1000 \
     AUDIT_FLUSH_INTERVAL_MS=1000

   # Restart to apply
   kubectl rollout restart deployment/layer4-agents -n value-fabric
   ```

5. **Scale Audit Database Resources**
   ```bash
   # Check current resource usage
   kubectl top pod -n value-fabric -l app=postgres

   # Scale postgres if needed (requires pod restart)
   kubectl patch deployment postgres -n value-fabric -p '{"spec":{"template":{"spec":{"containers":[{"name":"postgres","resources":{"limits":{"cpu":"2000m","memory":"4Gi"}}}]}}}}'
   ```

### Database-Specific Fixes

**If tablespace full:**
```bash
# Add storage or clean old audit logs (per retention policy)
kubectl exec -n value-fabric -it deployment/postgres -- \
  psql -U postgres -d value_fabric_audit -c "
  DELETE FROM audit_log
  WHERE created_at < NOW() - INTERVAL '90 days';
"

# Vacuum to reclaim space
kubectl exec -n value-fabric -it deployment/postgres -- \
  psql -U postgres -d value_fabric_audit -c "VACUUM FULL audit_log;"
```

**If constraint violations:**
```bash
# Check for duplicate or malformed entries
kubectl exec -n value-fabric -it deployment/postgres -- \
  psql -U postgres -d value_fabric_audit -c "
  SELECT event_type, COUNT(*)
  FROM audit_log
  WHERE created_at > NOW() - INTERVAL '1 hour'
  GROUP BY event_type;
"
```

## Verification

### Confirm Audit Writes Restored

```bash
# Monitor audit write rate for 5 minutes
for i in {1..6}; do
  echo "=== Check $i ==="
  kubectl exec -n value-fabric -it deployment/postgres -- \
    psql -U postgres -d value_fabric_audit -c \
    "SELECT COUNT(*) FROM audit_log WHERE created_at > NOW() - INTERVAL '1 minute';"
  sleep 60
done

# Check audit emitter health endpoint
kubectl exec -n value-fabric -it deployment/layer4-agents -- \
  curl -s http://localhost:8000/health | jq '.dependencies.postgres'

# Verify no new failures in logs
kubectl logs -n value-fabric -l app=layer4-agents --tail=100 | grep -c "audit_write_failed" || echo "0 failures"
```

### Compliance Check

```bash
# Verify audit trail continuity
kubectl exec -n value-fabric -it deployment/postgres -- \
  psql -U postgres -d value_fabric_audit -c "
  SELECT
    date_trunc('hour', created_at) as hour,
    COUNT(*) as events
  FROM audit_log
  WHERE created_at > NOW() - INTERVAL '6 hours'
  GROUP BY hour
  ORDER BY hour;
"
```

## Escalation

- **If audit writes fail for >15 minutes:** Page `vf-platform-oncall` via PagerDuty immediately (compliance risk)
- **If data loss suspected:** Escalate to Security team for compliance impact assessment
- **If PostgreSQL corruption suspected:** Escalate to Database team with priority P0
- **PagerDuty rotation:** `vf-platform-oncall` schedule
- **Slack channel:** `#vf-platform-oncall`

## Post-Incident Actions

1. Document root cause (DB connection pool exhaustion, disk full, constraint violation, code bug)
2. Audit data integrity check: verify no gaps in audit sequence numbers
3. Review and adjust connection pool sizes based on peak load
4. Consider implementing audit queue overflow alerting
5. Review retention policy and archiving procedures

## Prevention

- Monitor `value_fabric_audit_write_failures_total` metric proactively
- Set up connection pool saturation alerts before failures occur
- Implement audit queue depth monitoring (if using async mode)
- Regular database capacity planning for audit log growth
- Automated archival of old audit records per compliance retention
- Circuit breaker pattern for audit writes to prevent cascade failures

## Related Runbooks

- [PostgreSQL Unreachable](./postgres-unreachable.md) - If database connectivity issue
- [Redis Unreachable](./redis-unreachable.md) - If audit queue (async mode) issue
- [High Error Rate](./high-error-rate.md) - If audit failures correlate with service errors

## References

- Audit Emitter: `packages/shared/src/value_fabric/shared/audit/emitter.py`
- Audit Models: `packages/shared/src/value_fabric/shared/audit/models.py`
- Database Schema: `services/layer4-agents/migrations/audit_log.sql`
- Compliance Policy: `docs/compliance/audit-requirements.md`

---

> **Policy reference:** [Incident Severity Matrix and On-Call Escalation Policy](../operations/severity-escalation-policy.md)
