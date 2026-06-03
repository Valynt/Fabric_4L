# Workflow Authoring Specification

Workflows are **structured orchestration patterns** with explicit state machines, circuit breakers, and input/output contracts. Do not let agents freestyle.

---

## File Location

```
workflows/
  _templates/           # Reusable patterns
    manager-worker.md
    pipeline-dag.md
    human-in-the-loop.md
  <workflow-name>.md    # Individual workflow definitions
```

---

## Workflow Frontmatter

```yaml
---
workflow_id: unique-kebab-case-id
name: human-readable-name
version: 1.0.0
description: One-line purpose
pattern: manager-worker | pipeline-dag | human-in-the-loop | circuit-breaker
risk_level: low | medium | high
---
```

---

## Required: Explicit State JSON

Every workflow MUST maintain and update an explicit state object. Agents read this state at the start of every turn, not infer state from conversation history.

### State Schema

```json
{
  "stage": "inspection|analysis|execution|validation|reporting",
  "agent_id": "agent-name-001",
  "files_touched": ["path/to/file.py"],
  "tests_run": ["path/to/test.py"],
  "decisions_made": [
    {"decision": "...", "rationale": "...", "timestamp": "ISO-8601"}
  ],
  "blocked_by": null,
  "retry_count": 0,
  "circuit_breaker": {
    "tripped": false,
    "reason": null,
    "escalation_path": null
  }
}
```

---

## Circuit Breaker Pattern

After 3 consecutive tool errors or 2 self-correction loops, halt and escalate.

```yaml
circuit_breaker:
  max_tool_errors: 3
  max_self_correction_loops: 2
  action_on_trip: halt_and_escalate
  escalation_path: "log_and_notify"
```

---

## Orchestration Patterns

### Manager-Worker
Use for: Large refactoring across packages
- Manager agent decomposes by project graph
- Workers execute in parallel
- Manager validates with `nx affected:test` or `repo-graph-mcp`

### Pipeline (DAG)
Use for: CI/CD generation → test → review
- Each stage is an agent with explicit input/output contracts
- Artifacts pass through shared object store or state JSON
- Failed stage halts pipeline

### Human-in-the-Loop
Use for: High-stakes changes (auth, billing, migrations)
- Agent generates diff → stops → notifies human
- Resumes only after signed approval
- State checkpointed before HITL pause

---

## Checklist Enforcement

For every task, generate a mandatory checklist. The agent cannot mark the task complete until all items are checked and validated by tools.

```markdown
## Completion Checklist
- [ ] All modified files pass linter
- [ ] Affected tests pass
- [ ] No boundary violations introduced
- [ ] Documentation updated (if public API changed)
- [ ] Dead code catalog updated (if deletions)
```

---

## Template Usage

To create a new workflow:
1. Copy the appropriate template from `workflows/_templates/`
2. Fill in frontmatter and stages
3. Define state JSON schema
4. Add circuit breaker configuration
5. Register in `AGENTS.md` if it defines a new agent role
