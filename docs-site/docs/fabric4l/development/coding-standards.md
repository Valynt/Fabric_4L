---
status: active
last_reviewed: 2026-06-07
owner: platform-team
---

# Coding Standards

This document defines the standards that keep the Value Fabric codebase consistent, safe, and maintainable across six backend layers and a React frontend. Follow these rules before opening a PR.

## Python Standards

### Linting and Formatting

All Python code is linted with **ruff** and formatted with **black**. Type checking is enforced with **mypy**.

```bash
# Lint all layers
make lint

# Typecheck all layers
make typecheck

# Single layer
make lint-layer4
make typecheck-layer4
```

Ruff is run with comprehensive selectors in CI:

| Selector | Rule Set |
|----------|----------|
| `E,W,F` | Errors, warnings, Pyflakes |
| `I` | Import sorting |
| `N` | Naming conventions (PEP 8) |
| `D` | Docstring conventions |
| `B` | Bugbear (likely bugs) |
| `C4` | Comprehension optimizations |
| `SIM` | Simplification suggestions |
| `UP` | Pyupgrade (modern Python idioms) |

!!! tip "Run black via pre-commit"
    Use `pre-commit run black --all-files` to format before CI catches it.

### Type Checking

- Run `mypy src/ --ignore-missing-imports` per layer.
- Do not add `# type: ignore` to suppress legitimate type errors in API packages.
- CI explicitly guards against `type: ignore` on `layer2_extraction` imports inside the API package.

### Docstring Requirements

Use docstrings for public modules, classes, and functions. ruff's `D` selector enforces this in CI. Docstrings should explain *what* the function does and *why* it matters, not just restate the function name.

## TypeScript and React Standards

### Linting and Formatting

| Tool | Command | Purpose |
|------|---------|---------|
| ESLint | `pnpm --dir apps/web run lint` | Hygiene + legacy import checks |
| Prettier | `pnpm --dir apps/web run format` | Consistent formatting |
| TypeScript | `pnpm --dir apps/web run typecheck` | Static type checking |

### Frontend Technology Stack

The frontend uses a fixed stack. Do not introduce new UI libraries or frameworks without explicit justification.

- **React** — UI framework
- **Vite** — Build tool
- **TypeScript** — Type safety
- **Tailwind CSS** — Styling
- **shadcn/ui** — Component primitives
- **TanStack Query** — Server state management
- **Zustand** — Client state where existing patterns require it

!!! warning "Read DESIGN.md first"
    Before modifying `apps/web/`, read `DESIGN.md` in the repo root. It governs shell patterns, tabs, right-rail layout, and shared primitives.

### Preferred UI Patterns

Reuse existing shared components rather than creating one-off abstractions:

- `PageShell`
- `PageHeader`
- Shared card primitives
- Existing loading, empty, and error states
- Horizontal tabs (not vertical navigation)
- Right-rail detail panels for agent streams

## Layer Boundary Rules

Value Fabric is a six-layer pipeline. Preserve each layer's responsibility. Do not move logic across layers unless explicitly instructed.

| Layer | Port | Responsibility |
|-------|------|----------------|
| Layer 1 — Ingestion | 8001 | Playwright crawling, Celery jobs, Redis queues, compliance-aware ingestion |
| Layer 2 — Extraction | 8002 | Pydantic v2 extraction, LLM extraction, RDF/OWL, provenance |
| Layer 3 — Knowledge | 8003 | Neo4j, GraphRAG, hybrid retrieval, pgvector, subgraph APIs |
| Layer 4 — Agents | 8004 | LangGraph workflows, ROI calculator, checkpoints, agent orchestration |
| Layer 5 — Ground Truth | 8005 | TruthObject validation, maturity ladder, evidence-backed claims |
| Layer 6 — Benchmarks | 8006 | Peer comparison, statistical validation, datasets, benchmark policies |

!!! danger "Never hardcode pack logic into core"
    Manufacturing value drivers, SaaS ROI formulas, and healthcare benchmarks belong in **packs**, not in core platform orchestration. Core should provide capabilities; packs provide configuration.

## Contract-First Development

Contracts are the source of truth. Before changing API behavior, data structures, tool schemas, agent outputs, or frontend expectations:

1. Check `contracts/openapi/` and `contracts/jsonschema/`.
2. Check generated frontend API types.
3. Check tests that assert contract behavior.

If a backend response changes, update **all** of the following:

- OpenAPI contract
- JSON schema if applicable
- TypeScript types
- TanStack Query hooks
- UI consumers
- Tests
- Documentation if public-facing

!!! note "Never silently change a response shape"
    Architectural drift between agent logic and UI expectations is one of the hardest bug classes in this system. Fix the alignment, not just the symptom.

## Error Handling Standards

Errors must be explicit, safe, and contract-aligned.

**Do not expose:**

- Secrets or tokens
- Stack traces in production responses
- Raw LLM provider responses
- Cross-tenant data
- Sensitive customer content

**Prefer structured errors with stable codes.** Use the existing error envelope convention so the frontend can handle failures consistently.

## Naming Conventions

### Python

- Modules and packages: `snake_case`
- Classes: `PascalCase`
- Functions and variables: `snake_case`
- Constants: `SCREAMING_SNAKE_CASE`

### TypeScript / React

- Components: `PascalCase`
- Hooks: `camelCase` prefixed with `use`
- Utilities: `camelCase`
- Files containing components: match the component name

## Tenant Isolation in Code

Tenant isolation is a first-class invariant. Any data read or write must be scoped by tenant context.

**Preferred pattern:**

```python
tenant_id = ctx.tenant_id
repo.method(..., tenant_id=tenant_id)
```

**Avoid:**

```python
tenant_id = request.tenant_id  # unless explicitly validated against auth context
```

When touching backend code, confirm:

- `tenant_id` is extracted from authenticated context.
- `tenant_id` is passed to repository/service methods.
- Queries filter by `tenant_id`.
- Writes persist tenant ownership.
- Tests cover hostile cross-tenant access.

## Provider-Agnostic Agent Code

Layer 4 agent orchestration must remain provider-agnostic. Do not hardcode OpenAI-only, Anthropic-only, or Together-only logic into core workflows.

- Provider-specific code belongs in **adapters**.
- Agents should produce structured, versioned outputs.
- Treat prompts, tools, skills, and workflow state as versioned architecture.

## Security and Governance Rules

Do not weaken:

- Auth and RBAC
- Tenant isolation
- Rate limiting
- Audit logging
- Governance middleware
- Contract validation
- Production gates

When adding a new endpoint, workflow, or agent action, ask:

- Who can call this?
- Which tenant owns the data?
- Is the action auditable?
- Is the response safe to expose?
- Does this need contract tests?
- Does this need monitoring or metrics?

## Validation

Run these commands to verify your changes meet coding standards:

```bash
# Python
make lint-layer4
make typecheck-layer4

# Frontend
pnpm --dir apps/web run lint
pnpm --dir apps/web run typecheck

# Full pre-PR gate
make verify
```
