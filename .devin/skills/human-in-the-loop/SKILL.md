---
description: Agent generates diff, stops, notifies human, resumes only after approval
---

# Human-in-the-Loop Workflow Template

## Use Cases
- Auth/billing changes
- Database schema migrations
- API contract breaking changes
- Security policy modifications

## Workflow

### Stage 1: Preparation
1. Agent analyzes target files
2. Generates proposed diff
3. Identifies risk level and blast radius
4. Checkpoint state to `memory/working/`

### Stage 2: HITL Pause
1. Agent saves state with:
   ```json
   {
     "stage": "awaiting_human_approval",
     "proposed_diff": "...",
     "risk_level": "high",
     "affected_projects": [...],
     "approval_deadline": "2026-04-28T18:00:00Z"
   }
   ```
2. Notify human via configured channel
3. HALT. Do not proceed.

### Stage 3: Human Review
Human evaluates:
- [ ] Diff correctness
- [ ] Test coverage adequacy
- [ ] Blast radius acceptable
- [ ] Rollback plan exists (for schema changes)

Human responds: `approve`, `reject`, or `request_changes`

### Stage 4: Resume or Abort

**On approve:**
1. Load checkpointed state
2. Apply diff
3. Run verification
4. Mark complete

**On reject:**
1. Log rejection reason
2. Archive state
3. Report failure

**On request_changes:**
1. Load checkpointed state
2. Apply requested modifications
3. Go to Stage 2 (new checkpoint)

## Circuit Breaker

```yaml
max_approval_wait_hours: 24
action_on_timeout: auto_reject_and_notify
max_revision_rounds: 3
action_on_excess_revisions: escalate_to_tech_lead
```
## Required State JSON

Every workflow MUST maintain and update an explicit state object. Agents read this state at the start of every turn.

```json
{
  "stage": "inspection|analysis|execution|validation|reporting",
  "agent_id": "template-human-in-the-loop-001",
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
