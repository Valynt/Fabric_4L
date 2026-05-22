# `.windsurf/` — Agent Fleet Runtime

This directory is the **source of truth for agent behavior** in the Value Fabric monorepo. It implements the production-grade architecture blueprint: structured memory, context grounding, rule engines, skill registries, MCP backbone, and explicit workflow orchestration.

> **Agent behavior is code.** Prompts, rules, skills, and workflows are versioned artifacts just like application code.

---

## Directory Structure

```
.windsurf/
├── README.md                 # This file
├── AGENTS.md                 # Fleet registry — all agents, roles, allowed skills
├── MEMORY.md                 # Three-tier memory protocol + distillation pipeline
├── CONTEXT.md                # 40/40/20 context budget + structured grounding protocol
├── config.yaml               # Runtime configuration (circuit breakers, budgets, sync)
│
├── agents/                   # Runtime agent definitions (prompts, configs, constraints)
│   ├── _template/            # Agent authoring template
│   ├── code-reviewer/
│   ├── docs-writer/
│   ├── test-assurance/
│   ├── deprecation-migrator/
│   ├── dead-code-sweeper/
│   └── drift-assessor/
│
├── registry/                 # Centralized manifest registry (skills, tools, rules)
│   ├── skills.json           # 19+ skills with schemas, versions, side-effect declarations
│   ├── tools.json            # 26+ tools with MCP routing, rate limits, idempotency
│   └── rules.json            # Machine-readable rule engine manifest
│
├── skills/                   # Reusable capability modules (behavioral building blocks)
│   ├── SKILL_SCHEMA.md       # Skill authoring specification
│   └── .../SKILL.md          # Individual skill definitions
│
├── rules/                    # Guardrails, policies, constraint definitions
│   ├── RULE_REVIEW.md        # Rule validation audit and gap analysis
│   ├── hard-constraints.yaml # Blocker rules — enforced pre-execution
│   ├── dependency-rules.yaml # Module boundary enforcement
│   ├── safety-rules.yaml     # Security & safety constraints
│   └── style-rules.yaml      # Linter-enforced rules (reference only)
│
├── workflows/                # Orchestration patterns with explicit state machines
│   ├── WORKFLOW.md           # Workflow authoring specification
│   ├── _templates/           # Manager-Worker, Pipeline-DAG, HITL templates
│   └── *.md                  # Operational workflow playbooks
│
├── mcp/                      # MCP Gateway + server manifests
│   ├── gateway.yaml          # Gateway config (auth, discovery, routing)
│   ├── repo-graph-mcp.json   # Monorepo graph tools
│   ├── ci-mcp.json           # CI/CD tools
│   ├── code-mcp.json         # AST-aware code tools
│   └── docs-mcp.json         # Documentation query tools
│
├── context/                  # Context providers for structured grounding
│   ├── project-graph.yaml    # How to fetch monorepo dependency graph
│   ├── diff-context.yaml     # Git diff + commit history protocol
│   └── constraint-context.yaml # Rule loading based on file paths
│
├── memory/                   # Explicit three-tier memory storage
│   ├── working/              # Ephemeral session state (in-context)
│   ├── episodic/             # Task logs & structured execution records
│   └── semantic/             # Persistent distilled rules & patterns
│
├── codemaps/                 # Machine-readable monorepo metadata
│   └── layer_interfaces.json # L1-L4 API contract map
│
├── prompts/                  # Specialized prompt templates
│   └── *.md
│
├── testing/                  # Single source of truth for test audit artifacts
│   └── README.md
│
└── archive/                  # Old execution plans & deduplicated artifacts
    └── README.md
```

---

## Quick Start

### For Agent Operators
1. Check `AGENTS.md` to find the right agent for your task.
2. The agent loads its allowed skills from `registry/skills.json`.
3. Before execution, the policy engine evaluates `registry/rules.json` + `rules/*.yaml`.
4. Context is assembled per `CONTEXT.md` (40% grounding / 40% code / 20% history).

### For Skill Authors
1. Read `skills/SKILL_SCHEMA.md` for the skill contract.
2. Add your skill to `registry/skills.json` with `input_schema`, `output_schema`, `side_effects`.
3. If the skill wraps a tool, add the tool to `registry/tools.json` and `mcp/{server}.json`.

### For Workflow Authors
1. Read `workflows/WORKFLOW.md` for state machine + circuit breaker patterns.
2. Pick a template from `workflows/_templates/`.
3. Register the workflow in `AGENTS.md` if it defines a new agent role.

---

## Critical Safety Rules (P0)

1. **Never commit secrets** in any `.windsurf/` file.
2. **Never modify `agents/` definitions** without updating `AGENTS.md` fleet registry.
3. **Never change a skill** without updating `registry/skills.json`.
4. **Never change a tool manifest** without updating `registry/tools.json` and the corresponding MCP server.
5. **Never remove or weaken existing tests.** If a test blocks you, understand why.

---

## Production Checklist

Before promoting any `.windsurf/` change:

- [ ] **Registry**: `skills.json`, `tools.json`, and `rules.json` are in sync.
- [ ] **Schemas**: All new skills have `input_schema` + `output_schema` declarations.
- [ ] **Side Effects**: All tools declare `side_effects` (`none` | `read` | `write` | `network` | `exec`).
- [ ] **Rules**: YAML rule engine passes validation (`python scripts/ci/validate_rules.py` when available).
- [ ] **Memory**: Episodic logs older than 30 days are distilled or archived.
- [ ] **Context**: Context budget stays within 40/40/20 split.
- [ ] **Circuit Breaker**: Workflows declare `max_retries` and `escalation_path`.
