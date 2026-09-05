# Sub-Agent Orchestration Patterns

The standard playbook for splitting work across sub-agents (industry-converged
conventions, not one vendor's). Use this when the agentic layer decides *how to
decompose a task and hand pieces to sub-agents*.

## 1. Choose a topology by task shape

| Topology | Use when | Cost / coordination |
|---|---|---|
| **Single agent + tools** | Task is one coherent shape | Lowest; default |
| **Planner / executor** | Long, heterogeneous task: one planner decomposes, executors carry each step | Medium |
| **Hierarchical / router** | Task spans distinct domains → super-agent routes to specialists | Medium |
| **Fleet (parallel fan-out)** | Many independent units (per file, per area) run concurrently, results merged | Highest |

Rule of thumb: **start at the simplest topology that fits; escalate only when the
single agent demonstrably can't.** Over-engineering the split is a failure mode.

## 2. The parent↔sub-agent contract

A sub-agent cannot see the parent's conversation. Standard contract:

- **Self-contained brief** — the prompt carries all context it needs.
- **Explicit input** (what to do) and **output format** (what to return,
  verbatim — often JSON/structured).
- **Ownership rules** — "this scope is yours; don't touch X," so two sub-agents
  never collide.
- **Statelessness** — isolated run; no shared mutable memory.
- **Result as data** — structured output the parent consumes programmatically,
  not prose.

## 3. Coordination

- **Sync vs. background** — sync when you need the result before the next step;
  background + parallel for independent work you can do while waiting.
- **Refresh, don't respawn** — send follow-up messages to the *same* sub-agent
  (it keeps context) instead of launching a new one for each refinement.
- **Idle agents** — waking an idle agent with a message is cheaper and more
  context-preserving than a fresh spawn.

## 4. Governance (safety levers)

- **Scope tools per sub-agent** — a read-only agent gets only read tools
  (`view`, `grep`, `glob`), never `edit`/`write`. Biggest single safety lever.
- **Confidence-gated delegation** — hand off only when a specialist genuinely
  matches; avoid speculative background launches "just in case."
- **Fail-over** — if a sub-agent returns nothing usable, do the work yourself or
  retry once; don't loop respawning.
- **Evals** — test sub-agent behavior (see `evals/`), not just code.

## Reuse in this repo

Prefer the harness's existing machinery before hand-rolling:

- `task` tool agent types: `explore` (read-only research), `task` (run
  commands/tests), `general-purpose` (full toolset), `code-review`,
  `research`, `security-review`.
- `superpowers` skills (`dispatching-parallel-agents`, `subagent-driven-development`)
  for the methodology.
- SDK custom agents (`.agent/`-equivalent) only if you move off CLI onto the
  Copilot SDK host — CLI-only already covers this via `agents/skills`.
