# Value Fabric — Agent Reference

> Practical commands and directory map for AI agents and contributors.
> For full architectural rules and governance, see the sections below.
>
> **Note:** For the autonomous agent fleet registry defining cross-agent coordination, see `.windsurf/AGENTS.md`.

---

## Setup

### Prerequisites

- Python 3.11+ (any patch release; the repo does not require Python 3.11.10 specifically)
- Node.js ≥ 22.12.0 and pnpm 10.34.5
- Docker + Docker Compose
- `make`

### First-time setup

Use the same canonical command map as human contributors: [`docs/development/BUILD_SYSTEM.md`](docs/development/BUILD_SYSTEM.md) defines when to use `make`, `pnpm`, or direct Python CI runners, [`docs/development/COMMANDS.md`](docs/development/COMMANDS.md) lists every public root script and Makefile target, and [`docs/development/DISCOVERY_MAP.md`](docs/development/DISCOVERY_MAP.md) routes issue types to source-of-truth files, drift checks, validation commands, and evidence.

```bash
# 1. Clone and install tooling
#    Install the Infisical CLI: https://infisical.com/docs/cli/overview
#    Then log in:
infisical login

# 2. Select a local Python 3.11 interpreter (optional if python3.11 is already on PATH)
#    pyenv users can install the latest known 3.11 patch and keep .python-version pinned to the 3.11 series.
#    The Makefile resolves python3.11 first and then only accepts python3/python shims that are >=3.11;
#    use `make PYTHON=/path/to/python3.11 ...` if your local shim path is unusual.
pyenv install --skip-existing "$(pyenv latest -k 3.11)"
pyenv local 3.11
#    If your pyenv does not support series aliases, choose any installed 3.11.x patch explicitly.

# 3. Enable pnpm via corepack (do not use npm/yarn)
corepack enable
corepack prepare pnpm@10.34.5 --activate

# 4. Install frontend dependencies
pnpm install --frozen-lockfile

# 5. Install Python service dependencies into the pytest pipx venv
make setup

# 6. Start infrastructure (PostgreSQL, Redis, Neo4j, Keycloak)
#    Using Infisical-generated env (recommended):
pnpm env:dev && docker compose -f infra/compose/docker-compose.dev.yml --env-file .env.generated up -d
#    Or legacy manual .env:
#    cp .env.example .env && docker compose -f infra/compose/docker-compose.dev.yml up -d

# 7. Run database migrations
make migrate

# 8. Verify everything passes
make verify
```

---

## Dev Server

```bash
# Local Docker Compose stack (frontend + supporting backend services defined in infra/compose/docker-compose.dev.yml)
# With Infisical (recommended):
pnpm env:dev && docker compose -f infra/compose/docker-compose.dev.yml --env-file .env.generated up
# Legacy manual .env:
# docker compose -f infra/compose/docker-compose.dev.yml up

# Frontend only (Vite, port 3001, with mock API)
pnpm dev:web
# Or without Infisical:
# pnpm --dir apps/web run dev

# Frontend against live backend services
pnpm --dir apps/web run dev:live
# Requires: VITE_API_BASE_URL, VITE_PROXY_L1_URL … VITE_PROXY_L6_URL

# Individual backend layers (Infisical-injected)
pnpm dev:layer1
pnpm dev:layer2
pnpm dev:layer3
pnpm dev:layer4
pnpm dev:layer5
pnpm dev:layer6
```

---

## Build

```bash
# Frontend production build
pnpm --dir apps/web run build

# Analyze bundle size
pnpm --dir apps/web run build:analyze
```

---

## Testing

### Backend (Python / pytest)

```bash
# All backend layers
make test

# Single layer
make test-layer1
make test-layer2
make test-layer3
make test-layer4
make test-layer5
make test-layer6

# Specific test file or marker
pytest services/layer4-agents/tests/test_*.py
pytest -m unit
pytest -m "contract_static"
pytest -m "tenant_boundary"

# Contract + architecture tests (no live services required)
make contract-tests

# Backend-integrated validation (requires running stack)
make test-backend-integrated-validation

# Release smoke (boots full L1–L6 stack)
make test-backend-integrated-release-smoke
```

**Key pytest markers** (pass via `-m`):

| Marker | Meaning |
|---|---|
| `unit` | Fast, no I/O |
| `integration` | Real DB/cache, no containers |
| `contract_static` | OpenAPI contract checks, no live services |
| `service_required` | Contract tests needing live endpoints |
| `tenant_boundary` | Cross-tenant isolation regression |
| `security` | OWASP Top 10 |
| `slow` | >1 s or heavy deps |
| `backend_integrated` | Full live-stack validation |

### Frontend (Vitest + Playwright)

```bash
# Unit/component tests
pnpm --dir apps/web run test

# Watch mode
pnpm --dir apps/web run test:watch

# Coverage
pnpm --dir apps/web run test:coverage

# Contract tests only
pnpm --dir apps/web run test:contracts

# Security: assert no dev auth bypass in production build
pnpm --dir apps/web run test:prod-auth-bypass

# E2E (mocked, Playwright)
pnpm --dir apps/web run test:e2e

# E2E against live backend
pnpm --dir apps/web run test:e2e:live
# Requires: PLAYWRIGHT_LIVE_MODE=true, PLAYWRIGHT_LIVE_FRONTEND_URL, PLAYWRIGHT_BACKEND_URL

# Specific golden-path journeys
pnpm --dir apps/web run test:e2e:golden:j1:canonical
pnpm --dir apps/web run test:e2e:golden:j11

# Accessibility
pnpm --dir apps/web run test:a11y:components
pnpm --dir apps/web run test:a11y:pages
```

---

## Lint & Format

```bash
# All Python layers (ruff)
make lint

# Single layer
make lint-layer1   # … lint-layer6

# Python type-check (mypy)
make typecheck
make typecheck-layer4   # … per-layer variants

# Frontend lint (hygiene + legacy import checks)
pnpm --dir apps/web run lint

# Frontend type-check
pnpm --dir apps/web run typecheck

# Python formatting (black) — via pre-commit
pre-commit run black --all-files

# Frontend formatting (prettier)
pnpm --dir apps/web run format

# Install pre-commit hooks (run once)
pre-commit install
```

---

## Contract & Governance Checks

```bash
# Full verification gate (required before PR)
make verify

# Contract compliance
pnpm run check:contract-compliance

# Regenerate API types and assert no drift
pnpm run check:api-types

# Check for unresolved merge conflict markers
make check-conflict-markers

# Enforce pytest skip governance
make check-pytest-skip-governance

# Frontend verification suite
pnpm run verify:frontend
```

---

## Migrations

```bash
# All layers
make migrate

# Per-layer
make migrate-layer1
make migrate-layer2
make migrate-layer4
make migrate-layer5

# Validate migration entrypoints (exactly one Alembic head per service)
make check-migration-heads
```

---

## PR Requirements

### Branch naming

No enforced pattern is documented; use descriptive names (e.g., `feat/layer4-checkpoint-resume`, `fix/tenant-isolation-l3`).

### Commit format

Follow conventional commits where possible. Co-author AI-assisted commits:

```
Co-authored-by: Ona <no-reply@ona.com>
```

### Required CI checks (`.github/workflows/pr-checks.yml`)

All PRs targeting `main` must pass the GitHub checks as named in the workflow:

- `structural-preflight` — import topology, Python contract lint, frontend root policy, and pnpm-only/package-manager enforcement
- Per-layer lint, typecheck, and test jobs
- `contract-checks` — OpenAPI drift detection and related contract coverage
- `production-readiness-gate` — canonical production-readiness gate (`make production-readiness-gate`) required by CI
- Any additional required jobs shown in the PR’s Checks tab under `.github/workflows/pr-checks.yml`

### PR body

Fill in the required sections from `.github/pull_request_template.md`:

- **Governance Impact** — contract shape, tenant isolation, compatibility shim impact
- **Release & Policy Checklist** — contracts updated, API versioning, DR runbooks
- **Validation** — confirm `make verify` passed; `make evals` for agent/prompt changes

---

## Key Directories

```
apps/web/                    Frontend (React, Vite, TanStack Query, Tailwind, shadcn/ui)
services/
  layer1-ingestion/          L1: Playwright crawling, Celery jobs, Redis queues (port 8001)
  layer2-extraction/         L2: Pydantic v2 extraction, RDF/OWL, provenance (port 8002)
  layer3-knowledge/          L3: Neo4j, GraphRAG, hybrid retrieval, pgvector (port 8003)
  layer4-agents/             L4: LangGraph workflows, ROI calculator, agent orchestration (port 8004)
  layer5-ground-truth/       L5: TruthObject validation, maturity ladder (port 8005)
  layer6-benchmarks/         L6: Peer comparison, statistical validation (port 8006)
  api/                       Shared API gateway / auth enforcement
packages/
  shared/                    Shared Python library (tenant context, base models; exposes value_fabric.shared.*)
  platform-contract/         Cross-layer contract definitions and test harness
contracts/
  openapi/                   OpenAPI specs (source of truth for API contracts)
  jsonschema/                JSON Schema definitions
tests/
  contract/                  Cross-layer contract and architecture tests
  security/                  OWASP / tenant-boundary security tests
  backend_integrated/        Full-stack integration tests (requires live services)
packs/                       Domain extension packs (ontologies, formulas, benchmarks)
docs/                        Documentation (Diataxis: tutorials, how-to, reference, explanations)
scripts/ci/                  CI gate scripts (contract compliance, structural preflight, etc.)
config/ci/                   CI configuration (skip allowlists, legacy debt baselines)
k8s/                         Kubernetes manifests
monitoring/                  Observability configuration
.github/workflows/           CI/CD pipeline definitions
```

---

## Important Files

| File | Purpose |
|---|---|
| `DESIGN.md` | **Required reading** before modifying `apps/web/` |
| `docs/contract.md` | Canonical platform contract (tenant context, middleware, agent output shape) |
| `docs/development/DISCOVERY_MAP.md` | Issue-to-implementation routing map for source-of-truth files, drift checks, validation, and evidence |
| `docs/governance.md` | Engineering governance entry points |
| `canonical-paths-policy.md` | Runtime path governance matrix |
| `.env.example` | All required environment variables with safe defaults |
| `pytest.ini` | pytest configuration, markers, and test profiles |
| `.pre-commit-config.yaml` | Pre-commit hooks (gitleaks, black, ruff, prettier) |
| `docs/governance/compatibility-debt-registry.md` | Compatibility shim tracking |

---

## Architecture Rules

The sections below define the invariants every agent and contributor must preserve.

---

## 1. Core Operating Principles

### Act like a senior platform engineer

Before changing code:

- Understand the relevant layer, service boundary, and source-of-truth path.
- Prefer small, targeted changes over broad rewrites.
- Preserve existing architecture unless explicitly asked to refactor.
- Do not introduce new frameworks, package managers, UI libraries, or runtime patterns without justification.
- Always check for contract drift, schema drift, tenant-isolation impact, and frontend design-system impact.

### Do not optimize for "it works locally"

A change is not complete unless it respects:

- Multi-tenant isolation
- API contracts
- Layer boundaries
- Runtime source-of-truth paths
- Security and governance expectations
- Testability
- Observability where applicable
- Frontend design governance if touching `apps/web/`

---

## 2. Platform Architecture Context

Value Fabric uses a six-layer pipeline:

```text
Frontend: React / Vite / TanStack Query / Zustand / Tailwind / shadcn/ui

Layer 1: Intelligent Data Ingestion Service
- Port: 8001
- Responsibilities: Playwright crawling, Celery jobs, Redis queues, PostgreSQL state, compliance-aware ingestion

Layer 2: Ontology-Guided Extraction Pipeline
- Port: 8002
- Responsibilities: Pydantic v2 extraction, LLM extraction, RDF/OWL generation, provenance, batch ingest

Layer 3: Knowledge Graph & Semantic Layer
- Port: 8003
- Responsibilities: Neo4j, GraphRAG, hybrid retrieval, pgvector, subgraph APIs

Layer 4: Agentic Workflow Engine
- Port: 8004
- Responsibilities: LangGraph workflows, ROI calculator, business case generation, checkpoints, agent orchestration
- AuditOrchestrator router is mounted at `/v1/repo-audit` (the legacy audit-log router remains at `/v1/audit`)

Layer 5: Ground Truth
- Port: 8005
- Responsibilities: TruthObject validation, maturity ladder, evidence-backed claims

Layer 6: Benchmark Service
- Port: 8006
- Responsibilities: Peer comparison, statistical validation, datasets, benchmark policies
```

When modifying any layer, preserve its responsibility. Do not move logic across layers unless explicitly instructed.

---

## 3. Source-of-Truth Paths

Use these canonical paths first.

### Runtime packages

```text
services/layer1-ingestion/src/layer1_ingestion/
services/layer2-extraction/src/layer2_extraction/
services/layer3-knowledge/src/
services/layer4-agents/src/layer4_agents/
services/layer5-ground-truth/src/layer5_ground_truth/
services/layer6-benchmarks/src/layer6_benchmarks/
packages/shared/src/value_fabric/shared/
```

### Runtime API modules

```text
services/layer1-ingestion/src/layer1_ingestion/api/routes/
services/layer2-extraction/src/layer2_extraction/api/routes/
services/layer3-knowledge/src/api/routes/
services/layer4-agents/src/api/routes/
services/layer5-ground-truth/src/layer5_ground_truth/api/
services/layer6-benchmarks/src/layer6_benchmarks/api/routes/
```

### Maintained deployable services

```text
services/layer1-ingestion/
services/layer2-extraction/
services/layer3-knowledge/
services/layer4-agents/
services/layer5-ground-truth/
services/layer6-benchmarks/
services/api/
```

Path governance matrix for canonical vs compatibility locations:
- `docs/reference/layer-runtime-path-governance.md`

---

## 4. Contract-First Development

Contracts are the source of truth.

Before changing API behavior, data structures, tool schemas, agent outputs, or frontend expectations:

- Check `contracts/`
- Check OpenAPI specs
- Check JSON Schemas
- Check frontend API client expectations
- Check tests that assert contract behavior

Never silently change a response shape.

If a backend response changes, also update:

- OpenAPI contract
- JSON schema if applicable
- TypeScript types
- TanStack Query hooks
- UI consumers
- Tests
- Documentation if public-facing

---

## 5. Drift Prevention Rules

The hardest class of bugs in this system is architectural drift.

Always check for drift between:

- Agent logic and UI expectations
- API schemas and frontend types
- Database models and migrations
- OpenAPI specs and route handlers
- Documentation and implementation
- Tenant context and repository methods
- Layer-to-layer payload shapes

When fixing a bug, ask:

```text
Did this fail because one component changed while another still expects the old contract?
```

If yes, fix the alignment, not just the symptom.

---

## 6. Tenant Isolation Rules

Tenant isolation is a first-class invariant.

Any data read or write must be scoped by tenant context.

When touching backend code:

- Confirm `tenant_id` is extracted from authenticated context.
- Confirm `tenant_id` is passed to repository/service methods.
- Confirm queries filter by `tenant_id`.
- Confirm writes persist tenant ownership.
- Confirm tests cover hostile cross-tenant access where applicable.

Do not trust request body tenant IDs over authenticated context.

Preferred pattern:

```python
tenant_id = ctx.tenant_id
repo.method(..., tenant_id=tenant_id)
```

Avoid:

```python
tenant_id = request.tenant_id
```

unless explicitly validated against authenticated context.

---

## 7. Security and Governance Rules

Never commit secrets.

Do not weaken:

- Auth
- RBAC
- Tenant isolation
- Rate limiting
- Audit logging
- Governance middleware
- Contract validation
- Production gates

If adding a new endpoint, workflow, or agent action, consider:

- Who can call this?
- Which tenant owns the data?
- Is the action auditable?
- Is the response safe to expose?
- Does this need governance middleware?
- Does this need contract tests?
- Does this need monitoring or metrics?

---

## 8. Package Manager Rules

This monorepo is pnpm-only.

Use:

```bash
corepack enable
corepack prepare pnpm@10.34.5 --activate
pnpm install --frozen-lockfile
```

Do not use:

```bash
npm install
npm ci
yarn install
```

Frontend work must also use pnpm:

```bash
pnpm --dir apps/web install
pnpm --dir apps/web test
pnpm --dir apps/web build
```

Do not modify lockfiles casually.

---

## 9. Frontend Governance Rules

Before modifying `apps/web/`, read and follow:

```text
DESIGN.md
```

Frontend changes must reuse existing patterns:

- React
- Vite
- TypeScript
- Tailwind
- shadcn/ui
- TanStack Query
- Zustand where existing state patterns require it

Do not create one-off UI abstractions when shared components exist.

Prefer:

- `PageShell`
- `PageHeader`
- Shared card primitives
- Existing loading, empty, and error states
- Existing shell/tab/right-rail conventions

Avoid:

- New component libraries
- Unapproved icon systems
- Inconsistent spacing
- Custom card wrappers
- One-off colors
- One-off layouts
- Vertical navigation when the established pattern is horizontal tabs

---

## 10. Frontend UX Structure

Preserve the system's preferred UX model:

- Top-level domains in the sidebar
- Horizontal tabs inside major workspaces
- Right rail for detail panels and agent streams
- Drilldowns through overlays, drawers, or right-side panels
- Clear status states
- Traceability from insight to evidence to value model

When building UI for agentic workflows, favor:

```text
Main workspace + right rail detail/agent panel
```

rather than scattered pages or modal-heavy flows.

---

## 11. Layer-Specific Rules

### Layer 1: Ingestion

When changing ingestion:

- Preserve job lifecycle semantics.
- Keep crawling, extraction preparation, compliance, and source tracking separate.
- Ensure ingestion jobs are tenant-scoped.
- Do not bypass queue/state management.
- Preserve provenance metadata for downstream layers.

### Layer 2: Extraction

When changing extraction:

- Preserve ontology-guided extraction.
- Use Pydantic v2 patterns.
- Preserve provenance.
- Maintain RDF/OWL compatibility where applicable.
- Do not emit unstructured blobs where structured entities are expected.

### Layer 3: Knowledge Graph

When changing graph or retrieval:

- Preserve Neo4j entity relationships.
- Preserve hybrid retrieval behavior.
- Keep graph query APIs contract-aligned.
- Confirm tenant filters exist in graph queries.
- Avoid breaking GraphRAG, subgraph, and entity context consumers.

### Layer 4: Agents

When changing agents:

- Treat prompts, tools, skills, and workflow state as versioned architecture.
- Preserve checkpoint/resume behavior.
- Keep provider-specific logic out of core orchestration.
- Do not couple LangGraph workflows directly to one LLM vendor.
- Ensure agent outputs match contracts consumed by the UI and downstream services.

### Layer 5: Ground Truth

When changing validation:

- Preserve TruthObject semantics.
- Claims must remain evidence-backed.
- Maturity ladder logic must be auditable.
- Do not weaken validation to make tests pass.
- Ensure tenant context is propagated into repository calls.

### Layer 6: Benchmarks

When changing benchmarks:

- Preserve benchmark dataset lineage.
- Keep peer comparison and statistical validation explicit.
- Ensure all dataset, compare, validate, and industry-list operations are tenant-scoped where required.
- Do not mix benchmark definitions with tenant-specific benchmark usage unless the model explicitly supports it.

---

## 12. Agent and Provider Rules

Core orchestration must remain provider-agnostic.

Provider-specific code belongs in adapters.

Do not hardcode:

- OpenAI-only logic
- Anthropic-only logic
- Together-only logic
- Model-specific assumptions
- Vendor-specific response structures in core workflows

Use adapter boundaries.

Agents should produce structured, versioned outputs.

---

## 13. Packs and Ontology Rules

Packs are domain extensions.

They may include:

- Ontologies
- Formulas
- Variables
- Benchmarks
- Personas
- Industry-specific value drivers

Do not modify core platform logic to hardcode a pack-specific assumption.

Instead, prefer:

```text
core platform capability + pack-provided configuration
```

A manufacturing value driver, SaaS ROI formula, healthcare benchmark, or public-sector maturity model should usually live in a pack, not in core orchestration.

---

## 14. Testing Rules

### Operating Principle

> **No critical behavior exists unless it is tested.**

### Enforcement Rule

- **Intended behavior passes.**
- **Unintended behavior fails.**
- **Untested behavior is not production-ready.**

Every meaningful change should include or preserve tests. The test suite is the executable contract for intended behavior. Troubleshooting should not be the primary mechanism for discovering security, configuration, or runtime gaps.

For the canonical governance statement, see [`docs/governance/behavior-first-testing.md`](docs/governance/behavior-first-testing.md).

### Priorities

- Unit tests for pure logic
- Integration tests for service boundaries
- Contract tests for API shapes **and failure modes**
- Tenant-isolation tests for data access
- Regression tests for drift fixes
- Frontend behavior tests over brittle CSS tests
- E2E tests only where workflow coverage matters

### Behavior-First Requirements

For every production-critical workflow, encode:

1. **The intended allowed behavior** — a passing test.
2. **The intended denied behavior** — a passing test that asserts denial.
3. **The expected failure mode** — explicit error codes, safe defaults, or structured rejections.
4. **The test or gate that proves the behavior before release** — pytest marker, CI job, or Makefile target.

If behavior is not explicitly intended, it **fails closed by default**.

### Readiness Ladder (do not claim "ready" from static resolution alone)

"Ready" is a four-stage ladder; no stage may be skipped:

1. **Static contract resolved** — `make check-behavior-contract` (capabilities map to allowed + denied tests; static only).
2. **Behavior tests executed** — `pnpm run test:critical-behaviors` (the tests actually run and pass).
3. **Readiness audit passed** — `make check-behavior-readiness-audit` (executes the suites, enforces skip discipline, emits GREEN/YELLOW/RED to `artifacts/readiness/behavior-readiness-audit.json`).
4. **Production ready** — `make production-readiness-gate` (canonical gate; the `behavior-readiness` gate is wired into the `mainline-full`, `release-candidate`, `production-core`, and `tier0-production-safety` profiles).

A passing static contract (Stage 1) does **not** authorize a "ready" claim. Skips/xfails are only tolerated if benign + not-applicable or covered by an active, time-boxed waiver in `config/ci/behavior_readiness_waivers.yaml`; anything else is **RED**. See [`docs/governance/behavior-first-testing.md`](docs/governance/behavior-first-testing.md#readiness-ladder-from-static-resolution-to-production-ready).

### Security-Sensitive Changes

For security-sensitive changes, include hostile tests.

Examples:

```text
Tenant A cannot read Tenant B data.
Tenant A cannot mutate Tenant B data.
Missing tenant context fails closed.
Invalid contract payload is rejected.
Agent output schema mismatch is caught.
Unauthenticated request is rejected with 401.
Cross-tenant read fails with 403.
```

### Naming

Name tests after the behavior they prove, not the method they call:

- Good: `test_authenticated_user_can_read_own_data`
- Bad: `test_get_user_returns_200`

### Maintenance

Do not remove failing tests unless they are demonstrably obsolete and replaced with better coverage.

When a critical behavior is discovered to be untested:

1. File a behavior-debt ticket.
2. Add a `TODO(behavior-debt)` comment in code with the ticket link.
3. Prioritize the test in the next sprint.
4. Do not merge additional logic on top of the untested behavior until the contract is encoded.

---

## 15. Validation Commands

Use the narrowest validation first, then broaden.

Examples:

```bash
# Frontend
pnpm --dir apps/web test
pnpm --dir apps/web build

# Full install
pnpm install --frozen-lockfile

# Python tests
pytest path/to/relevant/tests

# Contract tests
pytest tests/contract

# Security tests
pytest tests/security

# Platform verification
make verify
```

If validation cannot be run, clearly report:

- What was changed
- What validation was attempted
- What could not be validated
- Why
- Residual risk

---

## 16. Documentation Rules

Update documentation when changing:

- Public APIs
- Layer responsibilities
- Setup commands
- Environment variables
- Operational runbooks
- Agent behavior
- Contract shapes
- Governance requirements
- Production-readiness checks

Docs should follow the repository's Diataxis structure:

- Tutorials
- How-to guides
- Reference
- Explanations

Do not create random documentation locations if a canonical docs area exists.

---

## 17. Environment and Secrets Rules

Never commit real secrets.

Use:

```text
.infisical/          # Infisical project config and path docs
.env.example         # Committed reference templates (no real secrets)
.env.generated       # Temporary export from Infisical (gitignored)
infisical run        # Local dev secret injection
GitHub OIDC → Infisical machine identity   # CI/CD
Infisical Kubernetes Operator              # Production K8s
```

When adding environment variables:

- Add them to `.env.example`
- Document them
- Ensure safe defaults
- Avoid insecure production defaults
- Ensure tests and Docker Compose files are aligned

Do not rename environment variables without updating all consumers.

**Dev Auth Bypass Flags:**
The following environment variables are for local development only and MUST NEVER be set in production:
- `DEV_AUTH_BYPASS=true`
- `ALLOW_DEV_AUTH_BYPASS=true`
- `AUTH_BYPASS_ENABLED=true`
- `ALLOW_INSECURE_DEV_AUTH_BYPASS=true`

These flags are validated by `ProductionSafetyValidator` and will cause startup failure in production-like environments. See SECURITY.md for details.

---

## 18. API Change Checklist

Before changing an API route:

- [ ] Identify the canonical route file.
- [ ] Check current OpenAPI contract.
- [ ] Check frontend consumers.
- [ ] Check service-to-service callers.
- [ ] Check tests.
- [ ] Preserve tenant context.
- [ ] Preserve error response shape.
- [ ] Update contracts if behavior changes.
- [ ] Add or update regression tests.
- [ ] Run targeted tests.

---

## 19. Frontend Change Checklist

Before changing `apps/web/`:

- [ ] Read `DESIGN.md`.
- [ ] Reuse existing shell/layout patterns.
- [ ] Use horizontal tabs where appropriate.
- [ ] Preserve right-rail detail/agent UX.
- [ ] Use existing shared UI primitives.
- [ ] Use TanStack Query patterns for server data.
- [ ] Avoid one-off styling.
- [ ] Add loading, empty, and error states.
- [ ] Test behavior, not implementation details.
- [ ] Report validation results.

---

## 20. Backend Change Checklist

Before changing backend code:

- [ ] Identify the layer boundary.
- [ ] Confirm canonical runtime path.
- [ ] Confirm maintained service wrapper path if applicable.
- [ ] Check tenant context propagation.
- [ ] Check repository query filters.
- [ ] Check migrations if persistence changes.
- [ ] Check OpenAPI and schema contracts.
- [ ] Add or update tests.
- [ ] Run targeted pytest.
- [ ] Report residual risks.

---

## 21. Agent Workflow Change Checklist

Before changing Layer 4 agent behavior:

- [ ] Identify affected agent, skill, tool, or workflow.
- [ ] Check versioned artifacts.
- [ ] Check checkpoint/resume state.
- [ ] Check output schemas.
- [ ] Check frontend expectations.
- [ ] Check downstream Layer 5 or Layer 6 dependencies.
- [ ] Preserve provider-agnostic design.
- [ ] Add schema/contract regression tests.
- [ ] Document behavior change if user-facing.

---

## 22. Migration Rules

When modifying database models:

- Do not change models without migrations.
- Do not change migrations without checking existing deployed state.
- Preserve tenant fields.
- Prefer additive migrations where possible.
- Avoid destructive migrations unless explicitly required.
- Include downgrade only if repository convention requires it.
- Check service-specific Alembic setup before assuming a global migration path.

---

## 23. Error Handling Rules

Errors should be explicit, safe, and contract-aligned.

Do not expose:

- Secrets
- Stack traces
- Internal tokens
- Raw provider responses
- Cross-tenant data
- Sensitive customer content

Prefer structured errors with stable codes.

---

## 24. Observability Rules

For production-impacting workflows, preserve or add:

- Request IDs
- Structured logs
- Metrics
- Audit events
- Runbook links where applicable
- Clear failure modes

Do not remove existing observability to simplify code.

---

## 25. Pull Request / Final Response Format

When finishing work, report:

```markdown
## Summary

- What changed
- Why it changed
- Which files were touched

## Validation

- Commands run
- Tests passed
- Tests not run and why

## Risk / Follow-up

- Any residual risk
- Any contract or migration concern
- Any manual verification needed
```

Do not claim tests passed unless they were actually run.

---

## 26. Non-Negotiables

Never:

- Use `npm install` or `yarn install`
- Bypass tenant isolation
- Silently change API response shapes
- Hardcode provider-specific logic into core orchestration
- Ignore `DESIGN.md` when editing frontend
- Introduce a new UI library casually
- Remove tests just to pass CI
- Commit secrets
- Weaken governance middleware
- Mix pack-specific logic into core platform
- Treat documentation as separate from implementation
- Make broad rewrites when a targeted fix is sufficient

---

## 27. Default Reasoning Loop

For every task, follow this loop:

```text
1. Locate the canonical source-of-truth files.
2. Understand the layer and contract boundary.
3. Identify likely drift points.
4. Make the smallest safe change.
5. Update contracts/types/tests/docs if needed.
6. Validate with targeted commands.
7. Report what changed, what passed, and what risk remains.
```

---

## AuditOrchestrator Agent

The `AuditOrchestrator` is a Layer 4 LangGraph agent that performs autonomous, read-only repository health audits. It analyzes git history, source code, and governance documentation; produces a ten-area scorecard; plans remediation sprints; and persists findings for trend tracking.

### Purpose

- Run repository health audits on schedule, on demand, or via webhook.
- Generate a weighted scorecard across ten audit areas (A–J).
- Track findings across runs and plan time-boxed remediation sprints.
- Feed audit results into PostgreSQL, Neo4j, and file-system reports without modifying source.

### Skill package

The portable skill definition lives in `.agent/skills/repo-audit/`:

- `SKILL.md` — skill definition, triggers, inputs, outputs, and permissions.
- `config.yaml` — default configuration matching `AuditConfig` defaults.
- `prompts/system.txt` — system prompt for the audit agent.
- `prompts/analyze_git.txt`, `analyze_code.txt`, `analyze_docs.txt`, `generate_report.txt` — task-specific prompts.

### Skill triggers

| Pattern | Action |
|---|---|
| `audit.*repo` | `run_full_audit` |
| `check.*health`, `health.*check` | `run_full_audit` |
| `score.*card`, `scorecard` | `get_latest_scorecard` |
| `finding.*status`, `update.*finding` | `update_finding` |
| `sprint.*plan`, `roadmap` | `get_sprint_plan` |
| `repo.*status`, `how.*healthy` | `get_quick_status` |

### API endpoints

The AuditOrchestrator router is mounted under `/v1/repo-audit` to avoid collision with the legacy audit-log router at `/v1/audit`:

- `POST /v1/repo-audit/run` — trigger a new audit run (async).
- `GET /v1/repo-audit/runs/{run_id}` — get a single run.
- `GET /v1/repo-audit/runs` — list recent runs.
- `GET /v1/repo-audit/scorecard/latest` — latest scorecard for a repo.
- `GET /v1/repo-audit/scorecard/history` — score history for trend charts.
- `GET /v1/repo-audit/findings` — list findings with filters.
- `PATCH /v1/repo-audit/findings/{finding_id}` — update finding status.
- `GET /v1/repo-audit/sprints` — current sprint plan.
- `GET /v1/repo-audit/report/{run_id}` — download report (Markdown or JSON).
- `POST /v1/repo-audit/webhook/github?tenant_id=<tenant>` — GitHub push/release webhook handler. The URL must include `?tenant_id=<tenant>`; the triggered audit run is scoped to that tenant.

### Configuration sources

Configuration is loaded with this precedence (highest first):

1. Environment variables with the `AUDIT__` prefix (e.g., `AUDIT__REPO_URL`, `AUDIT__AREA_WEIGHTS__ARCHITECTURE`).
2. YAML file at `.agent/skills/repo-audit/config.yaml`.
3. Pydantic defaults in `layer4_agents.agents.audit_orchestrator.models.AuditConfig`.

### Cache and report directories

- `.audit_cache/` — incremental audit cache and JSON fallback storage.
- `audit_reports/` — generated Markdown reports.

Both directories are ignored at the repository root.

---

## 28. North Star

Value Fabric must remain:

- Contract-first
- Tenant-safe
- Layered
- Auditable
- Provider-agnostic
- Pack-extensible
- Frontend-governed
- Production-ready
- Drift-resistant

Optimize for long-term platform integrity over short-term patching.

---

## Project Docs

- [Agent Architecture](docs/AGENTS.md)
- [Development Discovery Map](docs/development/DISCOVERY_MAP.md)
- [Frontend Governance Contract](DESIGN.md) — required reading before modifying `apps/web/`
- [Layer 4 Agents Service](services/layer4-agents/README.md)
- [ADR-002: Six-Layer Architecture](docs/explanations/adr/ADR-002-six-layer-architecture.md)
- [Compatibility Debt Registry](docs/governance/compatibility-debt-registry.md)
