---
agent_id: <kebab-case-agent-id>
name: <Human Readable Name>
version: 1.0.0
description: One-line purpose
risk_level: low | medium | high
side_effect_policy: read-only | read-write | read-write-test | write-docs-only
---

# <Agent Name>

## Role

What this agent does and when to invoke it.

## Allowed Skills

List skills from `registry/skills.json` that this agent may invoke:

- `skill-id-1`
- `skill-id-2`

## Forbidden Paths

Files or directories this agent must NOT touch:

- `packages/shared/src/value_fabric/shared/identity/` (security-sensitive)
- `services/layer4-agents/migrations/` (Alembic-managed)

## Context Requirements

What context must be loaded before this agent operates:

- Project graph of affected modules
- Git diff of current branch
- Applicable rules from `registry/rules.json`

## Side-Effect Policy

| Action | Allowed? | Notes |
|--------|----------|-------|
| Read files | Yes | Any file |
| Write source code | No | Unless explicitly allowed |
| Write tests | Yes | Only test files |
| Write docs | Yes | Only docs/ and *.md |
| Execute tests | Yes | Via CI MCP only |
| Delete files | No | Unless dead-code-sweeper |

## Circuit Breaker

```yaml
max_consecutive_tool_errors: 3
max_self_correction_loops: 2
action_on_trip: halt_and_escalate
escalation_path: log_and_notify
```

## Workflow Integration

If this agent participates in a workflow, document:
- Which workflow(s)
- Its role (manager, worker, reviewer)
- Input/output contracts

## Human-in-the-Loop

When is human approval required?

- [ ] Never
- [ ] For high-risk changes (auth, billing, schema)
- [ ] For all changes

## State JSON Schema

```json
{
  "stage": "...",
  "agent_id": "<agent-id>-001",
  "files_touched": [],
  "tests_run": [],
  "decisions_made": [],
  "blocked_by": null
}
```
