# AI Context — Value Fabric (Fabric_4L)

> **This file summarises existing documentation. It does not replace it.**
> Always read the canonical sources linked below before making changes.
> Sources: `AGENTS.md`, `ARCHITECTURE.md`, `docs/core-concepts/architecture.md`, `docs/architecture/system-overview.md`, `packages/platform-contract/CONTRACT.md`.

---

## What This Repository Is

Value Fabric is an AI-powered value-selling platform. It transforms unstructured customer and competitor data into structured business intelligence (ROI calculations, benchmarks, business cases) for enterprise B2B sales teams.

**Repository type:** Hybrid monorepo — six Python microservices, one React frontend, shared packages, and a contracts layer.

---

## Technology Stack (Verified Against Codebase)

| Layer | Technology | Verified |
|-------|-----------|---------|
| Backend services | Python 3.11+, FastAPI, Pydantic v2 | ✅ 409 FastAPI imports |
| Async task queue | Celery + Redis | ✅ 125 Celery refs in L1 |
| Knowledge graph | Neo4j + pgvector | ✅ 506 Neo4j refs in L3 |
| Agentic workflows | LangGraph | ✅ 19 imports |
| Database | PostgreSQL with RLS | ✅ |
| Frontend | React + Vite + TailwindCSS + shadcn/ui | ✅ |
| Package manager | pnpm 10.18.1 (never npm/yarn) | ✅ |
| Container orchestration | Docker Compose (dev), Kubernetes (prod) | ✅ |
| Auth | Keycloak + JWT | ✅ |
| Event streaming | Redis (Celery broker) | ✅ (RabbitMQ was planned, not implemented) |

---

## Six-Layer Architecture

```
Layer 1 — Ingestion      (port 8001)  Playwright crawling, Celery jobs, compliance
Layer 2 — Extraction     (port 8002)  LLM extraction, RDF/OWL, Pydantic v2
Layer 3 — Knowledge      (port 8003)  Neo4j, GraphRAG, pgvector, hybrid retrieval
Layer 4 — Agents         (port 8004)  LangGraph workflows, ROI calculator, checkpoints
Layer 5 — Ground Truth   (port 8005)  TruthObject validation, maturity ladder
Layer 6 — Benchmarks     (port 8006)  Peer comparison, statistical validation
Adjacent: Signal Refinery (port 8007), Billing/layer7 (port 8008)
Frontend: apps/web       (port 3001 dev / 5173 Vite)
```

---

## Non-Negotiable Rules (from AGENTS.md)

1. **pnpm only** — never `npm install` or `yarn`. Use `pnpm install --frozen-lockfile`.
2. **Tenant isolation** — every data read/write must be scoped by `tenant_id` via `RequestContext`. Never extract `tenant_id` from raw payloads.
3. **Contract-first** — tool schemas, agent outputs, and API response shapes are declared in `contracts/` and enforced by CI. Update contracts before code.
4. **No broad rewrites** — make the smallest safe change. Preserve unrelated local changes.
5. **No secrets in commits** — use Infisical or local uncommitted `.env` files.
6. **Read DESIGN.md before touching `apps/web`** — frontend has strict component and layout conventions.
7. **Conventional commits** — `feat|fix|docs|test|chore|refactor|perf|ci(scope): message`.

---

## Canonical Command Map

| Task | Command |
|------|---------|
| Full validation | `make verify` |
| Setup Python dev deps | `make setup` |
| Start dev infrastructure | `pnpm env:dev && docker compose -f infra/compose/docker-compose.dev.yml --env-file .env.generated up -d` |
| Apply migrations | `make migrate` |
| Run all tests | `make test` |
| Type check | `make typecheck` |
| Lint | `make lint` |
| Contract tests | `make contract-tests` |
| Frontend dev | `pnpm dev:web` |
| Layer-specific test | `make test-layer{1..6}` |

Full command reference: [`docs/development/COMMANDS.md`](../docs/development/COMMANDS.md)
Build system decisions: [`docs/development/BUILD_SYSTEM.md`](../docs/development/BUILD_SYSTEM.md)
Issue routing: [`docs/development/DISCOVERY_MAP.md`](../docs/development/DISCOVERY_MAP.md)

---

## Key Source Paths

| Concern | Path |
|---------|------|
| Runtime Python packages | `services/layer{1–6}-*/src/` |
| Shared runtime modules | `packages/shared/src/value_fabric/shared/` |
| Frontend | `apps/web/src/` |
| API contracts | `contracts/` |
| Platform contract | `packages/platform-contract/CONTRACT.md` |
| Kubernetes manifests | `k8s/` |
| Monitoring | `monitoring/` |
| Agent instructions | `AGENTS.md` (root) → `.devin/AGENTS.md` → `.agent/AGENTS.md` |

---

## Documentation Navigation

| Need | Go To |
|------|-------|
| Architecture overview | `ARCHITECTURE.md` → `docs/core-concepts/architecture.md` |
| Detailed system diagrams | `docs/architecture/system-overview.md` |
| Security policy | `SECURITY.md` |
| Runbooks / incident response | `RUNBOOK.md` → `docs/runbooks/00-runbook-index.md` |
| ADRs / decisions | `docs/explanations/adr/` |
| Contributing | `CONTRIBUTING.md` |
| CI gate map | `docs/development/CI_GATES.md` (to be created — CICD-001) |
| Threat model | `THREAT_MODEL.md` (to be created — DOC-THREAT) |
