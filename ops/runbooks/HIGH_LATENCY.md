# Runbook: HIGH_LATENCY

**Alert:** `HighLatency`  
**Severity:** Warning  
**Team:** SRE  
**Slack:** #sre-alerts  
**Last Updated:** 2024-06-15

---

## 1. Detection

| Signal | Threshold | Source |
|--------|-----------|--------|
| `histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))` | > 500ms | Prometheus |

**SLO:** p95 < 200ms over 7d. Alert fires at 500ms to provide headroom before SLO breach.

---

## 2. Impact Assessment

### Latency Tiers

| Latency | User Impact | Classification |
|---------|-------------|----------------|
| 200-500ms | Slightly sluggish | Within SLO |
| 500ms-1s | Noticeable delay | Warning threshold |
| 1-3s | Frustrating | SLO breach imminent |
| >3s | Unusable | Critical degradation |

### Identify the slow component

```promql
# Slowest endpoints
topk(10,
  histogram_quantile(0.95,
    sum by (le, path, service) (
      rate(http_request_duration_seconds_bucket[5m])
    )
  )
)

# Latency by layer
histogram_quantile(0.95,
  sum by (le, layer) (
    rate(http_request_duration_seconds_bucket[5m])
  )
)
```

---

## 3. Step-by-Step Recovery

### Step 1: Check for infrastructure issues (0-3 min)

```bash
# CPU usage
kubectl top pods -l app=${SERVICE} -n fabric4l

# Memory usage
kubectl top nodes

# Node conditions
kubectl get nodes -o wide
```

### Step 2: Check database query performance (3-8 min)

```sql
-- Slow queries on PostgreSQL
SELECT
  pid,
  now() - query_start AS duration,
  state,
  left(query, 100) AS query_snippet
FROM pg_stat_activity
WHERE state = 'active'
  AND now() - query_start > interval '1 second'
ORDER BY duration DESC;

-- Long-running transactions
SELECT
  pid,
  now() - xact_start AS xact_duration,
  left(query, 100)
FROM pg_stat_activity
WHERE xact_start IS NOT NULL
  AND now() - xact_start > interval '30 seconds'
ORDER BY xact_duration DESC;
```

### Step 3: Check Redis and cache hit rate (8-12 min)

```bash
# Cache hit rate
redis-cli info stats | grep keyspace

# If hit rate < 80%, cache may be cold
# Check for eviction
redis-cli info memory | grep evicted
```

### Step 4: Check downstream service latency (12-15 min)

```bash
# Time calls to downstream services
kubectl exec -it deploy/${SERVICE} -n fabric4l -- \
  time curl -s http://l3-knowledge:8003/health

# Check for network latency between pods
kubectl exec -it deploy/${SERVICE} -n fabric4l -- \
  ping -c 5 l3-knowledge
```

### Step 5: Mitigation options

| Cause | Mitigation |
|-------|------------|
| Expensive query | Add query timeout, kill query, add index |
| Missing index | `CREATE INDEX CONCURRENTLY` on hot column |
| Cold cache | Warm cache, check eviction policy |
| GC pressure | Tune garbage collection, increase memory |
| Network latency | Check CNI plugin, node placement |
| Lock contention | Reduce transaction scope, use advisory locks |
| Traffic spike | Enable rate limiting, scale horizontally |

### Emergency query kill

```sql
-- Find and kill the slowest queries
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE state = 'active'
  AND now() - query_start > interval '30 seconds'
  AND usename NOT IN ('postgres', 'replicator');
```

---

## 4. Verification

- [ ] p95 latency < 200ms for 10 consecutive minutes
- [ ] No active queries > 1 second
- [ ] Cache hit rate > 80%
- [ ] CPU and memory usage normal
- [ ] No user complaints in #support

---

## 5. Post-Incident Review

**Within 24 hours:**

1. Identify the query or code path causing latency
2. Add monitoring for that specific path
3. Consider query optimization or caching strategy
4. Review load test results vs. production load
5. Document learnings in team wiki
