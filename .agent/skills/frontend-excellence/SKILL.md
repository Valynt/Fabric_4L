---
name: frontend-excellence
version: 2026-08-28
triggers: ["prototype to production", "production frontend", "productionize", "componentize", "frontend production", "agentic ui", "tool schema", "frontend architecture", "pixel fidelity", "responsiveness retrofit", "wire frontend to backend", "frontend evals"]
tools: [bash, git]
preconditions: []
constraints: ["route to existing in-repo skills before authoring new code", "read DESIGN.md when present and apply its tokens and component rules", "contract-first: define schemas before implementation", "tool schemas precise and validated before agent wiring", "verify with typecheck, lint, tests, and build before claiming done", "preserve tenant isolation and existing contracts"]
category: engineering
---

# Frontend Excellence

Orchestrator for taking a prototype through production frontend, backend wiring, and an agentic layer at a top-1% software-engineering bar. This skill routes to the right existing tool or skill for each phase and fills gaps with its reference library.

## When to Use

- Converting prototype markup/CSS into a clean component architecture
- Matching a v1 design pixel-for-pixel (token extraction, not "close enough")
- Wiring a frontend to real backend APIs with typed contracts
- Adding auth, session handling, RBAC, or secure cookie flows
- Building an agentic UI: streaming, tool schemas, guardrails, evals
- Retrofitting responsiveness and accessibility without breaking desktop layout

## Repo Context Gate

Before any work, detect the environment — this changes what "good" means:

| Signal | If present |
|---|---|
| `DESIGN.md` | Load tokens + component rules. Apply them; never invent colors/type/spacing. |
| `.devin/skills/shadcn-fabric/` | Follow its ui usage rules for every new component. |
| `contracts/openapi/` | Contracts are source of truth — schema-first, never drift. |
| `apps/web/src/components/ui/fabric/` | Reuse Fabric domain components (`FabricCard`, `DataTable`, `StatusBadge`). |
| `.agent/skills/design-md/` | Load it when DESIGN.md exists (keeps tokens authoritative). |

## Phase Map — delegate, don't reinvent

| Phase | Route to |
|---|---|
| Audit existing frontend | `.devin/skills/frontend-audit-refactor` |
| Component design | `.windsurf/workflows/react_component_design.md` |
| shadcn/ui usage | `.devin/skills/shadcn-fabric` |
| Wire page to real hook | `.devin/skills/facade-page-connector`, `dil-hook-scaffolder` |
| Auth | `.claude/skills/clerk-*` (setup, custom-ui, webhooks, testing) |
| Agent outputs/schemas | `.devin/skills/structured-outputs` |
| LangGraph orchestration | `.devin/skills/orchestration` |
| Agentic UX patterns | `.devin/skills/agentic-ux` |
| Playwright e2e/visual | `.devin/skills/playwright` |
| Evals for agent behavior | `.devin/skills/evals` |
| Pre-production audit | `.devin/skills/pre-production-audit`, `gate-hardening` |
| Deploy/preview envs | `.devin/skills/bunnyshell`, `.devin/skills/load-testing` |

If no suitable existing skill exists in the current repo, fall back to the references in this package (below).

## Reference Library

| Need | Reference |
|---|---|
| Full prototype→production procedure | `references/prototype-to-production.md` |
| Contract-first API design and drift checks | `references/contract-first-api.md` |
| Precise tool/function schema design (#1 failure point) | `references/tool-schema-design.md` |
| SSE/WebSocket streaming for agentic UIs | `references/streaming-and-realtime.md` |
| Token flows, RBAC, secure sessions | `references/auth-and-session.md` |
| Splitting work across sub-agents (topologies, contract, governance) | `references/subagent-orchestration.md` |

Templates for component, hook, API adapter, and tool schema live in `templates/`. Definition-of-done and guardrail checklists live in `checklists/`.

## Procedure

1. **Detect context** — run the Repo Context Gate; note tokens, component rules, and contracts.
2. **Reference the phase** — read the matching phase file before writing code.
3. **Plan the contract** — for new endpoints, define OpenAPI/JSON Schema *before* UI work.
4. **Execute with templates** — start from `templates/` when creating components, hooks, adapters, or tools.
5. **Verify** — run typecheck, lint, and the relevant tests/build; record exactly what ran.
6. **Evals for agentic work** — run the eval scenario suite before and after any prompt/tool change.

## Common Mistakes

- Skipping the contract step and letting UI shape the API (causes adapter duct tape)
- Writing a tool schema that is too open-ended for the agent to call reliably — scope inputs and outputs
- Copying prototype inline styles instead of extracting tokens first
- Building new UI primitives when Fabric/shadcn equivalents exist
- Claiming "done" on typecheck alone — run the build and affected tests

## Self-Rewrite Hook

If a repeated frontend failure class appears across runs, add a narrow checklist to `checklists/` and a targeted evaluation scenario to `evals/`. Keep this file under 100 lines; move detail into references.