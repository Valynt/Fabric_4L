---
workflow_id: template-human-in-the-loop
name: Human-in-the-Loop
version: 1.0.0
description: Agent generates diff, stops, notifies human, resumes only after approval
pattern: human-in-the-loop
risk_level: high
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
