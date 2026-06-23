# Runbook: Agent Workflow Stall

## Overview

Long-running LangGraph workflows are stalled or making no progress, potentially blocking background jobs and user requests.

## Symptoms

- **Alert:** `WorkflowStalled`
- **Dashboard:** [Layer 4 Agents](../../monitoring/grafana/dashboards/layer4-agents.json)
- **Log Query:**
  ```
  {layer="layer4"} |= "workflow_stalled\|checkpoint save failed\|graph node timeout"
  or
  {layer="layer4"} |= "AgentStoppedError\|NodeInterrupt\|graph execution stalled"
  ```
- **User Impact:** Background jobs not completing, agent requests timing out, workflow queue backing up
- **Metrics:**
  - `increase(layer4_workflow_executions_total{status="running"}[30m]) == 0`
  - `layer4_workflow_executions_total{status="running"} > 0`
  - Workflow step completion rate at 0 for 30+ minutes

## Diagnosis

### 1. List Running Workflows

```bash
# List all running workflows via Layer 4 API
kubectl exec -n value-fabric -it deployment/layer4-agents -- \
  curl -s http://localhost:8000/api/v1/workflows?status=running | jq '.workflows'

# Check workflow count by status
kubectl exec -n value-fabric -it deployment/layer4-agents -- \
  curl -s http://localhost:8000/api/v1/workflows/metrics | jq

# Get specific stalled workflow details
kubectl exec -n value-fabric -it deployment/layer4-agents -- \
  curl -s "http://localhost:8000/api/v1/workflows/{workflow_id}/status" | jq
```

### 2. Check Agent and Executor Logs

```bash
# Check for errors, retries, or deadlocks
kubectl logs -n value-fabric -l app=layer4-agents --tail=200

# Look for specific stall patterns
kubectl logs -n value-fabric -l app=layer4-agents | grep -E \
  "stalled|checkpoint|interrupt|retry|deadlock|timeout"

# Check for LangGraph specific errors
kubectl logs -n value-fabric -l app=layer4-agents | grep -E \
  "LangGraphError|NodeError|GraphRecursionError|CheckpointError"

# Check previous container logs if restarted
kubectl logs -n value-fabric -l app=layer4-agents --previous 2>/dev/null | tail -100
```

### 3. Verify External Dependencies

```bash
# Check Neo4j (graph state storage)
kubectl exec -n value-fabric -it deployment/layer4-agents -- \
  curl -s http://localhost:8000/health | jq '.dependencies.neo4j'

# Check PostgreSQL (checkpoint storage)
kubectl exec -n value-fabric -it deployment/layer4-agents -- \
  curl -s http://localhost:8000/health | jq '.dependencies.postgres'

# Check Redis (messaging/cache)
kubectl exec -n value-fabric -it deployment/layer4-agents -- \
  curl -s http://localhost:8000/health | jq '.dependencies.redis'

# Check LLM provider health
kubectl exec -n value-fabric -it deployment/layer2-extraction -- \
  curl -s http://localhost:8000/health/llm 2>/dev/null || echo "LLM health endpoint not available"
```

### 4. Inspect Workflow State

```bash
# Get workflow checkpoint/state
kubectl exec -n value-fabric -it deployment/layer4-agents -- \
  curl -s "http://localhost:8000/api/v1/workflows/{workflow_id}/state" | jq

# Check checkpoint database
kubectl exec -n value-fabric -it deployment/postgres -- \
  psql -U postgres -d layer4 -c "
  SELECT workflow_id, node_name, status, updated_at
  FROM workflow_checkpoints
  WHERE status = 'running'
  AND updated_at < NOW() - INTERVAL '30 minutes'
  ORDER BY updated_at;
  "

# Check for checkpoint locks
kubectl exec -n value-fabric -it deployment/postgres -- \
  psql -U postgres -d layer4 -c "
  SELECT * FROM pg_locks
  WHERE relation IN (SELECT oid FROM pg_class WHERE relname LIKE '%checkpoint%');
  "
```

## Remediation

### Immediate Actions (P0)

1. **Identify and Cancel Stuck Workflows (if safe)**
   ```bash
   # Get stalled workflow IDs
   STALLED_WORKFLOWS=$(kubectl exec -n value-fabric -it deployment/layer4-agents -- \
     curl -s http://localhost:8000/api/v1/workflows?status=running | \
     jq -r '.workflows[] | select(.last_update > "30m") | .id')

   # Cancel specific workflow
   kubectl exec -n value-fabric -it deployment/layer4-agents -- \
     curl -X POST "http://localhost:8000/api/v1/workflows/{workflow_id}/cancel" \
     -H "Content-Type: application/json" \
     -d '{"reason": "stalled_manual_cancel"}'

   # Or cancel all stalled workflows (be careful!)
   for wf_id in $STALLED_WORKFLOWS; do
     kubectl exec -n value-fabric -it deployment/layer4-agents -- \
       curl -X POST "http://localhost:8000/api/v1/workflows/$wf_id/cancel" \
       -H "Content-Type: application/json" \
       -d '{"reason": "stalled_batch_cancel"}'
   done
   ```

2. **Restart Stuck Workflows (after dependency fix)**
   ```bash
   # Re-queue workflow
   kubectl exec -n value-fabric -it deployment/layer4-agents -- \
     curl -X POST "http://localhost:8000/api/v1/workflows/{workflow_id}/restart" \
     -H "Content-Type: application/json" \
     -d '{"from_checkpoint": true, "reason": "stalled_restart"}'

   # Restart with fresh state (ignore checkpoint)
   kubectl exec -n value-fabric -it deployment/layer4-agents -- \
     curl -X POST "http://localhost:8000/api/v1/workflows/{workflow_id}/restart" \
     -H "Content-Type: application/json" \
     -d '{"from_checkpoint": false, "reason": "stalled_fresh_restart"}'
   ```

3. **Scale Agent Executor Pool (if queue depth is high)**
   ```bash
   # Check current replica count
   kubectl get deployment layer4-agents -n value-fabric -o jsonpath='{.spec.replicas}'

   # Scale up executors
   kubectl scale deployment/layer4-agents -n value-fabric --replicas=5

   # Or enable HPA if configured
   kubectl autoscale deployment/layer4-agents -n value-fabric \
     --min=2 --max=10 --cpu-percent=70
   ```

### Short-Term Mitigation (P1)

4. **Clear Checkpoint Database Locks**
   ```bash
   # Identify blocking queries
   kubectl exec -n value-fabric -it deployment/postgres -- \
     psql -U postgres -d layer4 -c "
     SELECT pid, state, query_start, query
     FROM pg_stat_activity
     WHERE state = 'active'
     AND query_start < NOW() - INTERVAL '10 minutes'
     AND query LIKE '%checkpoint%';
     "

   # Terminate blocking query (use with caution)
   kubectl exec -n value-fabric -it deployment/postgres -- \
     psql -U postgres -d layer4 -c \
     "SELECT pg_terminate_backend({blocking_pid});"
   ```

5. **Enable Workflow Pause/Resume (graceful degradation)**
   ```bash
   # Pause non-critical workflows
   kubectl exec -n value-fabric -it deployment/layer4-agents -- \
     curl -X POST http://localhost:8000/api/v1/workflows/pause \
     -H "Content-Type: application/json" \
     -d '{
       "workflow_types": ["batch_processing", "data_sync"],
       "exclude_critical": true,
       "reason": "dependency_outage"
     }'

   # Resume after recovery
   kubectl exec -n value-fabric -it deployment/layer4-agents -- \
     curl -X POST http://localhost:8000/api/v1/workflows/resume \
     -H "Content-Type: application/json" \
     -d '{"workflow_types": ["batch_processing", "data_sync"]}'
   ```

### Root Cause Fixes

6. **Fix LangGraph Node Timeouts**
   ```bash
   # Update node timeout configuration
   kubectl set env deployment/layer4-agents \
     LANGGRAPH_NODE_TIMEOUT_SECONDS=300 \
     LANGGRAPH_MAX_RETRIES=3

   # Restart to apply
   kubectl rollout restart deployment/layer4-agents -n value-fabric
   ```

7. **Fix Checkpoint Save Issues**
   ```bash
   # Increase checkpoint timeout
   kubectl set env deployment/layer4-agents \
     CHECKPOINT_SAVE_TIMEOUT_MS=10000 \
     CHECKPOINT_ASYNC=true

   # Restart to apply
   kubectl rollout restart deployment/layer4-agents -n value-fabric
   ```

## Verification

### Confirm Workflow Recovery

```bash
# Check running workflow count
kubectl exec -n value-fabric -it deployment/layer4-agents -- \
  curl -s http://localhost:8000/api/v1/workflows/metrics | jq

# Monitor workflow progress
watch -n 30 'kubectl exec -n value-fabric -it deployment/layer4-agents -- \
  curl -s http://localhost:8000/api/v1/workflows/metrics | jq ".running, .completed_last_5m"'

# Check specific restarted workflow
kubectl exec -n value-fabric -it deployment/layer4-agents -- \
  curl -s "http://localhost:8000/api/v1/workflows/{workflow_id}/status" | jq

# Verify no new stalls
kubectl logs -n value-fabric -l app=layer4-agents --tail=50 | grep -c "checkpoint_saved\|node_completed"
```

## Escalation

- **If multiple workflows are stalled:** Page `vf-platform-oncall` via PagerDuty
- **If checkpoint database has locks:** Escalate to Database team
- **If LangGraph framework issues suspected:** Contact AI Engineering team
- **PagerDuty rotation:** `vf-platform-oncall` schedule
- **Slack channel:** `#vf-platform-oncall`

## Post-Incident Actions

1. Document root cause (dependency failure, deadlock, infinite loop, resource exhaustion)
2. Add workflow-level timeouts and heartbeat checks
3. Improve idempotency for affected workflow types
4. Review and fix any checkpoint save bottlenecks
5. Consider workflow circuit breakers for external dependencies

## Prevention

- Add workflow step completion rate monitoring
- Enable workflow heartbeats with configurable intervals
- Set per-workflow-type timeouts based on expected duration
- Regular checkpoint database maintenance (vacuum, index optimization)
- Implement workflow circuit breakers for external service calls

## Related Runbooks

- [Neo4j Unreachable](./neo4j-unreachable.md) - If graph state storage issue
- [PostgreSQL Unreachable](./postgres-unreachable.md) - If checkpoint storage issue
- [Redis Unreachable](./redis-unreachable.md) - If messaging/cache issue
- [LLM Provider Outage](./llm-provider-outage.md) - If LLM dependency issue

## References

- LangGraph Documentation: https://langchain-ai.github.io/langgraph/
- Layer 4 Workflow API: `services/layer4-agents/src/layer4_agents/api/workflows.py`
- Checkpoint Implementation: `services/layer4-agents/src/checkpoint/`

---

> **Policy reference:** [Incident Severity Matrix and On-Call Escalation Policy](../operations/severity-escalation-policy.md)
