---
workflow_id: value-fabric-harness
name: Value Fabric Coding Harness
version: 1.0.0
description: Value Fabric coding harness — layer-scoped context assembly and pre-edit boundary guards for safe, contract-aligned development.
pattern: circuit-breaker
risk_level: high
---

# Value Fabric Coding Harness

## Purpose

This workflow wraps the `.windsurf/harness/` Python modules so that any coding task in the Value Fabric repo starts with the right governance context and boundary checks. It does not replace `.agent/harness/` (portable brain); it complements it with repo-native layer awareness.

## When to Use

Invoke this workflow at the start of **every** coding task in the Fabric_4L monorepo. It is especially important when:

- The task touches backend services (layers 1–6)
- The task changes API routes, schemas, or frontend hooks
- The task spans multiple layers or domains
- You want to prevent contract drift before writing code

## Prerequisites

- Python 3.11+ available on PATH
- Repo root is the working directory
- `.windsurf/harness/` exists and contains `vf_context.py`, `vf_layer_router.py`, `vf_contract_guard.py`

## Workflow

### 1. Detect Target Layer(s)

Use `vf_layer_router.py` to determine which layer(s) the task touches.

```bash
TASK="<task description>" FILES="<comma-separated file paths>" \
  python .windsurf/harness/vf_layer_router.py
```

**Expected output:**
- Detected layer numbers (e.g., `[3]`)
- Frontend flag (`true`/`false`)
- Path classification summary
- Boundary warnings (if any)

**Decision:**
- If `CROSS_LAYER_WARNING` appears, confirm the cross-layer scope with the user before proceeding.
- If `LAYER_UNKNOWN` appears, ask the user to clarify which layer the task targets.

### 2. Run Pre-Edit Contract Guard

Use `vf_contract_guard.py` to catch drift before any file is modified.

```bash
TASK="<task description>" FILES="<comma-separated file paths>" \
  python .windsurf/harness/vf_contract_guard.py
```

**Expected output:**
- `Pre-edit guard passed.` → proceed to step 3
- Warnings / exit code 1 → surface all issues to the user and pause for confirmation

**Blocking issues must not be silently ignored.** If the guard emits `OPENAPI_DRIFT` or `FRONTEND_API_DRIFT_RISK`, resolve or document the risk before editing.

### 3. Assemble Layer-Scoped Context

Use `vf_context.py` to build the system prompt that will guide the agent's work.

```bash
TASK="<task description>" FILES="<comma-separated file paths>" \
  python .windsurf/harness/vf_context.py
```

**What gets injected:**
1. `AGENTS.md` — core operating principles
2. `canonical-paths-policy.md` — source-of-truth paths
3. `contracts/GOVERNANCE.md` — contract-first rules
4. Layer-specific READMEs / entrypoints (only for detected layers)
5. `DESIGN.md` — frontend governance (if frontend is in scope)
6. Frontend contract docs (if API/schema/hook/type work is detected)
7. Recent episodic memory filtered by layer
8. `permissions.md` — safety-critical rules (always last)

**Token budget:** `128000` context max, `40000` reserved for response, remainder distributed across docs with safety-critical items at the end.

### 4. Execute the Coding Task

With the assembled context in memory, proceed with the user's task following all injected governance rules.

**During execution, continuously check:**
- Are you respecting the layer responsibility documented in the context?
- Are you preserving contracts (API shapes, types, hooks) or updating all consumers together?
- Are you reusing existing patterns (shadcn/ui, TanStack Query, Zustand) rather than inventing new ones?

### 5. Log Episodic Memory

After the task completes, record a lightweight episodic entry for future harness runs.

Append to `.agent/memory/episodic/AGENT_LEARNINGS.jsonl`:

```json
{
  "timestamp": "<ISO8601 UTC>",
  "action": "<short task name>",
  "detail": "<what was done>",
  "reflection": "<what worked or what to avoid next time>",
  "layers": [<detected layer numbers>],
  "pain_score": <1-10>,
  "importance": <1-10>,
  "recurrence_count": <1+>
}
```

**Example:**

```json
{"timestamp":"2026-05-15T18:00:00Z","action":"Fix tenant isolation in layer3 graph query","detail":"Added tenant_id filter to Neo4j subgraph query in services/layer3-knowledge/","reflection":"Always check graph queries for tenant scoping; missing it is a silent security bug.","layers":[3],"pain_score":8,"importance":9,"recurrence_count":1}
```

## Makefile Shortcuts

Three targets are available in the root `Makefile`:

```bash
# Inspect the assembled context for a task
make harness-task TASK="fix tenant isolation in layer3" FILES="value_fabric/layer3/"

# Run pre-edit boundary and contract checks
make harness-guard FILES="apps/web/src/pages/intelligence/HypothesesTab.tsx"

# Full harness preflight (context + guards)
make harness-check
```

## Integration with Existing Workflows

This harness is a **pre-task gate**, not a replacement for domain-specific workflows. After the harness runs, invoke the appropriate skill/workflow for the actual work:

| Detected Domain | Next Workflow / Skill |
|-----------------|-----------------------|
| Frontend (`apps/web/`) | `skills/shadcn-fabric/`, `facade-page-connector` |
| API / contract changes | `contract-enforcement-auditor`, `tool-contract-sync` |
| Dead code removal | `dead-code-sweeper` |
| Deprecation fixes | `deprecation-migrator` |
| Test authoring | `autonomous-test-assurance-agent` |
| Documentation | `technical_documentation` |

## Rules

1. **Never skip the guard.** Run `vf_contract_guard.py` before every edit session.
2. **Never ignore CROSS_LAYER_WARNING.** Confirm scope or split the task.
3. **Preserve `.agent/harness/`.** The generic harness is still the portable fallback; do not modify it.
4. **Log episodes.** Without episodic memory, the harness cannot learn cross-session patterns.
5. **Keep `LAYER_DOCS` in sync.** If a layer gets a new canonical README, update `vf_context.py`.
