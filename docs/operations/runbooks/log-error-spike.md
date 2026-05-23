# Runbook: LogErrorSpike

## Overview

A sustained spike in ERROR-level log lines has been detected in one or more services. This is an early-warning signal that may precede a service degradation or cascading failure. The alert is driven by Loki log aggregation and evaluates the rate of ERROR logs over a 5-minute window.

## Trigger

- **Alert:** `LogErrorSpike`
- **Dashboard:** [Value Fabric Operational](../../monitoring/grafana/dashboards/value-fabric-operational.json)
- **Detection:**
  - Loki query: `sum by (layer, service) (rate({job="fluent-bit"} |= "ERROR" [5m])) > 0.5`
  - Sustained for 5 minutes

## Impact

- **Severity:** P2 - Warning
- **User Impact:** Potential latent errors; may degrade into user-facing failures
- **Business Impact:** Risk of SLA breach if trend continues
- **Data Impact:** Usually none unless errors are write-path failures

## Diagnosis

### 1. Identify Affected Service and Layer

```bash
# Query Loki directly for the error stream
logcli query '{job="fluent-bit",service=~".*"} |= "ERROR"' --since=10m --limit=100

# In Grafana, open the Loki datasource and run:
# sum by (layer, service) (rate({job="fluent-bit"} |= "ERROR" [5m]))
```

### 2. Correlate with Metrics

```bash
# Check HTTP 5xx rate for the same layer
kubectl exec -n value-fabric deployment/prometheus -- \
  curl -s 'http://localhost:9090/api/v1/query?query=sum(rate(http_requests_total{status=~"5.."}[5m]))'

# Check latency p95
kubectl exec -n value-fabric deployment/prometheus -- \
  curl -s 'http://localhost:9090/api/v1/query?query=histogram_quantile(0.95,sum(rate(http_request_duration_seconds_bucket[5m]))by(le))'
```

### 3. Extract Representative Errors

```bash
# Tail the affected pod logs
kubectl logs -n value-fabric -l app=<service> --tail=200 | grep ERROR

# If using Docker Compose locally:
docker compose -f docker-compose.monitoring.yml logs <service> | grep ERROR
```

### 4. Check Downstream Dependencies

```bash
# Verify DB, cache, and graph connectivity from the affected pod
kubectl exec -n value-fabric deployment/<service> -- curl -s http://localhost:8000/health | jq .
```

## Resolution

| Scenario | Action |
|---|---|
| Transient dependency blip | Monitor for auto-recovery; no action required if rate drops within 10 minutes |
| Bug in recent deployment | Roll back the affected service: `kubectl rollout undo deployment/<service> -n value-fabric` |
| Resource pressure (OOM, CPU throttling) | Scale horizontally or vertically; check HPA status: `kubectl get hpa -n value-fabric` |
| Dependency failure (DB, Redis, Neo4j) | Follow the dedicated dependency runbook (postgres-down, redis-down, neo4j-down) |
| Log verbosity regression | If ERROR lines are benign, open a ticket to downgrade log level and tune the alert threshold |

## Escalation

1. **On-call engineer** acknowledges alert within 5 minutes
2. **If error rate > 5/sec or user-facing impact confirmed**, page platform lead
3. **If cascading to other layers**, declare incident and follow [Incident Response Playbook](../severity-escalation-policy.md)

## Post-Incident

- Update alert threshold if false-positive rate is high
- Add integration test covering the error path if a code bug was root cause
- Link postmortem in `#incidents` channel
