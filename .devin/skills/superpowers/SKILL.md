---
skill_id: superpowers
name: superpowers
version: 6.1.1
description: Agentic software development methodology for planning, TDD, debugging, code review, and delivery workflows.
side_effects: read, write
timeout_ms: 600000
required_context: [project_graph]
allowed_agents: ["*"]
source_path: ../../.agents/skills/superpowers
---

# Superpowers

Agentic software development methodology covering the full development lifecycle: brainstorming, planning, TDD, debugging, code review, and branch delivery.

## When to Use

- Starting a new feature or multi-step task that needs structured planning
- Writing tests first (TDD) for a new feature or bugfix
- Systematically debugging a test failure or unexpected behavior
- Requesting or receiving code review before merging
- Executing implementation plans with review checkpoints
- Dispatching parallel agents for independent tasks
- Isolating feature work with git worktrees
- Finishing a development branch (merge, squash, or rebase decisions)

## Child Skills

The superpowers package lives at `.agents/skills/superpowers/` and contains 14 child skills:

| Skill | Purpose |
|-------|---------|
| `using-superpowers` | Meta skill: discover and invoke Superpowers skills |
| `brainstorming` | Explore intent, requirements, and design before implementation |
| `writing-plans` | Write implementation plans for multi-step tasks |
| `executing-plans` | Execute a written plan with review checkpoints |
| `test-driven-development` | Implement features and bugfixes test-first |
| `systematic-debugging` | Diagnose bugs, test failures, and unexpected behavior |
| `subagent-driven-development` | Execute implementation plans with independent tasks in the current session |
| `dispatching-parallel-agents` | Handle 2+ independent tasks without shared state |
| `using-git-worktrees` | Isolate feature work with git worktrees |
| `requesting-code-review` | Request review before merging |
| `receiving-code-review` | Evaluate and act on review feedback |
| `verification-before-completion` | Verify before claiming work is done |
| `finishing-a-development-branch` | Decide how to integrate completed work |
| `writing-skills` | Create or edit skills |

## Input Parameters

```json
{
  "type": "object",
  "properties": {
    "action": {
      "type": "string",
      "enum": [
        "brainstorm",
        "write-plan",
        "execute-plan",
        "tdd",
        "debug",
        "subagent-dev",
        "parallel-agents",
        "git-worktree",
        "request-review",
        "receive-review",
        "verify-completion",
        "finish-branch",
        "write-skill"
      ]
    },
    "task_description": {
      "type": "string",
      "description": "Description of the task to apply the superpowers workflow to"
    }
  },
  "required": ["action"]
}
```

## Output

```json
{
  "type": "object",
  "properties": {
    "success": { "type": "boolean" },
    "skill_invoked": { "type": "string" },
    "artifacts": { "type": "array", "items": { "type": "string" } },
    "next_steps": { "type": "array", "items": { "type": "string" } }
  }
}
```

## Steps

1. Identify which child skill matches the current task phase.
2. Invoke the child skill from `.agents/skills/superpowers/<child-skill>/SKILL.md`.
3. Follow the child skill's instructions for the specific workflow.
4. Use the `skill` tool with `SkillName: "superpowers"` to invoke from the Windsurf/Cascade skill system.

## Edge Cases

- **Child skill not found** — Ensure the `.agents/skills/superpowers/` directory is present with all child skill subdirectories.
- **Session start** — The `using-superpowers` child skill is the entry point for discovering available skills.

## Anti-Patterns

- Do NOT skip the brainstorming/planning phase for non-trivial tasks
- Do NOT claim work is complete without running the verification-before-completion skill
- Do NOT bypass code review for changes that affect contracts, tenant isolation, or security

## Related

- [Superpowers GitHub](https://github.com/obra/superpowers)
- Plugin manifest: `.agents/skills/superpowers/superpowers-plugin.json`
