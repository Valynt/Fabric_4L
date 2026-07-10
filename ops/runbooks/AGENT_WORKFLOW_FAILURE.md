# Runbook: AGENT_WORKFLOW_FAILURE

**Alert:** `WorkflowFailureRateHigh`  
**Severity:** Warning  
**Team:** Agents  
**Slack:** #agents-team  
**Last Updated:** 2024-06-15

---

## 1. Detection

| Signal | Threshold | Source |
|--------|-----------|--------|
| `rate(agent_workflow_failed_total[5m]) / rate(agent_workflow_total[5m])` | > 5% | Prometheus |

**SLO:** 99.5% success rate. Alert fires at 5% failure rate.

---

## 2. Impact Assessment

### Failure classification

```promql
# Failure rate by workflow type
sum by (workflow_type) (rate(agent_workflow_failed_total[5m]))
/
sum by (workflow_type) (rate(agent_workflow_total[5m]))

# Failure rate by error type
sum by (error_type) (rate(agent_workflow_failed_total[5m]))
```

### Common failure types

| Error Type | Cause | Frequency |
|------------|-------|-----------|
| `llm_timeout` | LLM API slow/unresponsive | 40% |
| `llm_rate_limit` | Hit provider rate limit | 25% |
| `validation_error` | Output schema validation failed | 15% |
| `checkpoint_error` | State save/restore failed | 10% |
| `tool_error` | External tool call failed | 10% |

---

## 3. Step-by-Step Recovery

### Step 1: Identify failing workflows (0-3 min)

```bash
# Check L4 logs for workflow failures
kubectl logs -l app=l4-agents -n fabric4l --tail=500 | grep -i "workflow_failed\|error"

# In Loki
{service="l4-agents"} |= "workflow_failed" | json
  | line_format "{{.timestamp}} {{.workflow_type}} {{.error_type}} {{.error_message}}"
  | workflow_type!=""
```

### Step 2: Check LLM provider health (3-6 min)

```bash
# Test direct LLM API call
curl -s https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY" | jq '.data | length'

# Check LLM error metrics
open "https://grafana.fabric4l.io/d/fabric4l-agent-workflows?viewPanel=3"
```

### Step 3: Check LangGraph checkpoint store (6-9 min)

```bash
# Check PostgreSQL checkpoint table size
psql $DATABASE_URL -c "
SELECT
  schemaname,
  tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE tablename LIKE '%checkpoint%'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
"

# Check for checkpoint lock contention
psql $DATABASE_URL -c "
SELECT * FROM pg_locks WHERE relation::regclass::text LIKE '%checkpoint%';
"
```

### Step 4: Mitigation based on cause

| Cause | Fix |
|-------|-----|
| LLM timeout | Increase timeout, switch to faster model, enable fallback |
| LLM rate limit | Enable request queueing, switch provider, reduce concurrency |
| Validation error | Fix output schema, relax validation, add retry with different prompt |
| Checkpoint error | Clear stale checkpoints, increase storage, fix connection pool |
| Tool error | Check tool availability, add circuit breaker, use cached result |

### Emergency workflow bypass

```python
# If a specific workflow type is failing, disable it temporarily
# via the admin API:
import httpx
httpx.post("http://l4-agents:8004/admin/workflows/disable",
           json={"workflow_type": "failing_workflow", "duration_minutes": 30})
```

---

## 4. Verification

- [ ] Workflow failure rate < 1% for 10 minutes
- [ ] All workflow types completing successfully
- [ ] LLM API response times < 5s
- [ ] Checkpoint operations succeeding
- [ ] Queue depth returning to normal

---

## 5. Post-Incident Review

**Within 24 hours:**

1. Classify failure root cause
2. Add specific monitoring for the failure mode
3. Update LangGraph checkpoint configuration if needed
4. Review LLM provider redundancy (multi-provider fallback)
5. Update workflow error handling if needed
