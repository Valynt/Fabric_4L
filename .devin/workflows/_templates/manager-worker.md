---
workflow_id: template-manager-worker
name: Manager-Worker Refactoring
version: 1.0.0
description: Decompose large refactoring by project graph; workers execute in parallel; manager validates
pattern: manager-worker
risk_level: medium
---

# Manager-Worker Workflow Template

## Stage 1: Manager — Decomposition

1. Fetch project graph for target modules (`repo-graph-mcp.get_project_dependencies`)
2. Identify independent work packages
3. Spawn worker agents with explicit input/output contracts
4. Write shared state:
   ```json
   {
     "stage": "dispatching",
     "work_packages": [
       {"id": "wp-1", "agent": "worker-1", "files": [...], "status": "pending"}
     ]
   }
   ```

## Stage 2: Workers — Execution

Each worker:
1. Reads its work package from shared state
2. Executes changes
3. Runs local validation (linter, type check)
4. Updates work package status: `completed` or `failed`

## Stage 3: Manager — Validation

1. Poll all work packages until all `completed` or `failed`
2. Run broader gate: `nx affected:test` or `ci-mcp.trigger_build`
3. If failures:
   - If retry_count < 2: retry failed packages
   - Else: trip circuit breaker, produce failure report

## Stage 4: Reporting

1. Consolidate changes into single commit description
2. Update `memory/episodic/` with execution log
3. Produce completion report

## Circuit Breaker

```yaml
max_worker_failures: 2
max_total_retries: 3
action_on_trip: halt_and_produce_partial_report
```
