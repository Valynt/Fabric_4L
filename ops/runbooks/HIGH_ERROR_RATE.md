# Runbook: HIGH_ERROR_RATE

**Alert:** `HighErrorRate`  
**Severity:** Critical  
**Team:** SRE  
**Slack:** #incidents  
**Last Updated:** 2024-06-15

---

## 1. Detection

| Signal | Threshold | Source |
|--------|-----------|--------|
| `rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m])` | > 1% | Prometheus |

**Notification:** PagerDuty page to on-call SRE. Slack alert in #incidents.

---

## 2. Impact Assessment

### Immediate Questions

1. **Which layer?** Check `$labels.layer` and `$labels.service` in the alert.
2. **Scope:** Is it one service or multiple? Is it one tenant or all?
3. **Trend:** Is the error rate increasing or plateauing?

### Quick Checks (within 2 minutes)

```bash
# Check error rate by status code
grpcurl -plaintext l${LAYER}-${SERVICE}:800${LAYER} grpc.health.v1.Health/Check

# Query Prometheus for error breakdown
open "https://grafana.fabric4l.io/d/fabric4l-platform-overview?var-layer=${LAYER}"
```

### Impact Matrix

| Error Rate | User Impact | Action |
|------------|-------------|--------|
| 1-5% | Degraded experience | Investigate immediately |
| 5-20% | Significant disruption | Consider traffic shift |
| >20% | Service largely unavailable | Initiate incident response, consider failover |

---

## 3. Step-by-Step Recovery

### Step 1: Identify the failing endpoint (0-3 min)

```promql
# Top failing endpoints
topk(10,
  sum by (path, status) (rate(http_requests_total{status=~"5..", layer="${LAYER}"}[5m]))
)
```

### Step 2: Check recent deployments (0-3 min)

```bash
# Check if a deployment coincided with the alert onset
kubectl rollout history deployment/${SERVICE} -n fabric4l

# If deployment happened within 15 min of alert, consider rollback
kubectl rollout undo deployment/${SERVICE} -n fabric4l
```

### Step 3: Check downstream dependencies (3-5 min)

```bash
# Check DB connectivity
kubectl exec -it deploy/${SERVICE} -n fabric4l -- \
  python -c "import psycopg2; psycopg2.connect(\$DATABASE_URL).cursor().execute('SELECT 1')"

# Check Redis
kubectl exec -it deploy/${SERVICE} -n fabric4l -- \
  redis-cli -h redis ping

# Check Neo4j (L3 only)
kubectl exec -it deploy/l3-knowledge -n fabric4l -- \
  curl -s http://neo4j:7474/dbms/health
```

### Step 4: Check logs for stack traces (5-10 min)

```bash
# Get recent errors
kubectl logs -l app=${SERVICE} -n fabric4l --tail=500 | grep -i error

# In Loki
{service="${SERVICE}"} |= "ERROR" | json | line_format "{{.timestamp}} {{.level}} {{.message}}"
```

### Step 5: Mitigation options

| Scenario | Action | Rollback |
|----------|--------|----------|
| Bad deployment | `kubectl rollout undo` | Automatic via ArgoCD |
| DB connection pool exhausted | Restart service pods | N/A |
| Downstream service down | Enable circuit breaker | Disable circuit breaker |
| Resource exhaustion | Horizontal pod autoscaler scale | HPA will auto-scale down |
| Code bug | Deploy hotfix from feature branch | Revert merge commit |

### Step 6: Verify recovery

```promql
# Confirm error rate is back below threshold
rate(http_requests_total{service="${SERVICE}", status=~"5.."}[5m])
/
rate(http_requests_total{service="${SERVICE}"}[5m]) < 0.001
```

---

## 4. Verification

- [ ] Error rate < 0.1% for 10 consecutive minutes
- [ ] All health checks passing: `grpc.health.v1.Health/Check`
- [ ] No new error spikes in logs
- [ ] Key user flows tested (document upload, query, workflow)
- [ ] Post-incident note posted in #incidents

---

## 5. Post-Incident Review

**Within 24 hours:**

1. Create a post-mortem document in `docs/incidents/YYYY-MM-DD-high-error-rate.md`
2. Include: Timeline, root cause, detection time, mitigation time, lessons learned
3. Identify preventive actions (code fixes, monitoring gaps, process changes)
4. Schedule review meeting with affected teams

**Required fields:**
- MTTD (Mean Time To Detect)
- MTTR (Mean Time To Recover)
- Error budget consumed
- Customer impact (requests failed, tenants affected)
