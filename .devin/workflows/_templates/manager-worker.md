---
workflow_id: template-manager-worker
name: Manager-Worker Refactoring
version: 1.0.0
description: Decompose large refactoring by project graph; workers execute in parallel; manager validates
pattern: manager-worker
risk_level: medium
category: orchestration
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
## Required State JSON

Every workflow MUST maintain and update an explicit state object. Agents read this state at the start of every turn.

```json
{
  "stage": "inspection|analysis|execution|validation|reporting",
  "agent_id": "template-manager-worker-001",
  "files_touched": [],
  "tests_run": [],
  "decisions_made": [],
  "blocked_by": null,
  "retry_count": 0,
  "circuit_breaker": {
    "tripped": false,
    "reason": null,
    "escalation_path": null
  }
}
```

## Circuit Breaker Configuration

```yaml
circuit_breaker:
  max_tool_errors: 3
  max_self_correction_loops: 2
  action_on_trip: halt_and_escalate
  escalation_path: "log_and_notify"
```

## Completion Checklist

- [ ] State JSON updated with current stage, touched files, tests, and decisions.
- [ ] Circuit breaker evaluated before retrying after tool errors or self-correction loops.
- [ ] Relevant validation commands run and recorded in the workflow state.
- [ ] No security, tenant-isolation, contract, governance, or frontend-design assertions weakened.
