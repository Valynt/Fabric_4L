# Runbook: DatabasePoolExhaustion

## Overview

Database connection pool exhaustion or fatal connection errors have been detected in service logs. When the pool is saturated, new requests queue, latency spikes, and eventually health checks fail, leading to cascading pod restarts and potential data-loss for in-flight transactions.

## Trigger

- **Alert:** `LogDatabasePoolExhaustion`
- **Dashboard:** [Value Fabric Operational](../../monitoring/grafana/dashboards/value-fabric-operational.json)
- **Detection:**
  - Loki query: `sum by (layer, service) (rate({job="fluent-bit"} |~ "pool.exhausted|connection.timeout|too.many.connections|FATAL:.*connection" [5m])) > 0`
  - Sustained for 3 minutes

## Impact

- **Severity:** P1 - Critical
- **User Impact:** Request timeouts, failed writes, API errors
- **Business Impact:** Data inconsistency if transactions abort mid-flight; queued job backlog
- **Data Impact:** Ingestion or extraction jobs may stall; agent checkpoints may fail to persist

## Diagnosis

### 1. Confirm Pool State

```bash
# Check active connections from the database side
kubectl exec -n value-fabric deployment/postgres -- psql -U $DB_USER -d $DB_NAME -c "SELECT state, count(*) FROM pg_stat_activity GROUP BY state;"

# Look for idle-in-transaction connections
kubectl exec -n value-fabric deployment/postgres -- psql -U $DB_USER -d $DB_NAME -c "SELECT pid, usename, application_name, state, now() - query_start AS duration, left(query, 80) FROM pg_stat_activity WHERE state != 'idle' ORDER BY duration DESC LIMIT 20;"
```

### 2. Identify the Consuming Service

```bash
# Extract the service name from Loki alert labels and tail its logs
kubectl logs -n value-fabric -l app=<service> --since=10m | grep -iE "pool|connection|timeout"

# Check if the service has a connection leak (unclosed sessions)
kubectl logs -n value-fabric -l app=<service> --since=30m | grep -c "connection pool"
```

### 3. Check for Lock Contention or Slow Queries

```bash
# Blocking queries
kubectl exec -n value-fabric deployment/postgres -- psql -U $DB_USER -d $DB_NAME -c "SELECT blocked_locks.pid AS blocked_pid, blocked_activity.usename AS blocked_user, blocking_locks.pid AS blocking_pid, blocking_activity.usename AS blocking_user, blocked_activity.query AS blocked_statement, blocking_activity.query AS blocking_statement FROM pg_catalog.pg_locks blocked_locks JOIN pg_catalog.pg_stat_activity blocked_activity ON blocked_activity.pid = blocked_locks.pid JOIN pg_catalog.pg_locks blocking_locks ON blocking_locks.locktype = blocked_locks.locktype AND blocking_locks.relation = blocked_locks.relation AND blocking_locks.pid != blocked_locks.pid JOIN pg_catalog.pg_stat_activity blocking_activity ON blocking_activity.pid = blocking_locks.pid WHERE NOT blocked_locks.granted;"
```

### 4. Verify Application Configuration

```bash
# Inspect the service DB pool size settings
kubectl get configmap -n value-fabric <service>-config -o yaml | grep -iE "pool|max_connections|timeout"

# Check Prometheus for connection-pool metrics if exposed
kubectl exec -n value-fabric deployment/prometheus -- \
  curl -s 'http://localhost:9090/api/v1/query?query=db_pool_available_connections'
```

## Resolution

| Scenario | Action |
|---|---|
| Slow query holding connections | Kill the offending query (`SELECT pg_terminate_backend(<pid>)`) and optimize the query/index |
| Idle-in-transaction timeout too high | Lower `idle_in_transaction_session_timeout` temporarily; fix transaction scope in code |
| Legitimate traffic spike | Scale the DB read replicas or connection pooler (PgBouncer) if available |
| Connection leak in code | Restart the affected pods as a temporary mitigation; deploy the fix immediately |
| DB max_connections reached | Increase `max_connections` (with caution) or add a pooler; review per-service allocation |

## Escalation

1. **On-call engineer** acknowledges within 5 minutes
2. **If write-path is blocked for >10 minutes**, page database/platform lead
3. **If data loss is suspected**, freeze deploys and open an incident

## Post-Incident

- Tune connection pool sizes per service based on peak observed usage
- Add `pg_stat_activity` dashboard panel to the operational Grafana dashboard
- Consider introducing PgBouncer if not already in place
