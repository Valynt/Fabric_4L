# Documentation Refactor — Phase 1: Validation Report

**Date:** 2026-07-15
**Branch:** `docs/refactor-methodology`
**Method:** Each document's claims validated against source code, Makefile, and ADRs. No files modified.

---

## Confidence Score Key

| Score | Meaning |
|-------|---------|
| ✅ **High (90–100%)** | All verifiable claims confirmed against code/config |
| ⚠️ **Medium (60–89%)** | Most claims accurate; one or more stale or unverified claims |
| ❌ **Low (<60%)** | Multiple claims contradict codebase reality |

---

## 1. Root-Level Documents

### `README.md` — Confidence: ⚠️ Medium (70%)

| Claim | Reality | Verdict |
|-------|---------|---------|
| `make setup` installs deps, spins up dev stack, and applies migrations | `make setup` (line 470 of Makefile) only runs `scripts/ci/setup_python_dev_deps.py` — it does **not** start Docker or apply migrations | ❌ Overclaims |
| `make verify` runs full validation | Confirmed: `make verify` aggregates lint, typecheck, tests, contracts, security smoke | ✅ Accurate |
| `make migrate` applies database migrations | Confirmed in Makefile | ✅ Accurate |
| Six-layer architecture | Confirmed by service directories | ✅ Accurate |
| pnpm 10.18.1 | Confirmed in `package.json` `packageManager` field | ✅ Accurate |

**Action required:** Fix `make setup` description (DOC-002 — already in remediation roadmap).

---

### `ARCHITECTURE.md` — Confidence: ✅ High (92%)

| Claim | Reality | Verdict |
|-------|---------|---------|
| FastAPI across all services | 409 FastAPI imports in `services/` | ✅ Accurate |
| Celery/Redis in Layer 1 | 125 Celery references in `services/layer1-ingestion/src/` | ✅ Accurate |
| Six-layer core + adjacent billing/signal | Confirmed by service directory structure | ✅ Accurate |
| Neo4j in Layer 3 | 506 Neo4j references in `services/layer3-knowledge/src/` | ✅ Accurate |
| LangGraph in Layer 4 | 19 LangGraph imports in `services/` | ✅ Accurate |
| pgvector | 366 pgvector/vector references in `services/` | ✅ Accurate |
| Redis Streams | Zero `XADD`/`XREAD` in production code | ⚠️ Not mentioned in `ARCHITECTURE.md` directly — accurate by omission |
| Kafka | Not mentioned in `ARCHITECTURE.md` — accurate by omission | ✅ Accurate |

**Note:** `ARCHITECTURE.md` is a thin index pointing to `docs/architecture/system-overview.md` and `docs/core-concepts/architecture.md`. The index itself is accurate.

---

### `AGENTS.md` — Confidence: ✅ High (88%)

| Claim | Reality | Verdict |
|-------|---------|---------|
| PostgreSQL, Redis, Neo4j, Keycloak in dev stack | Confirmed in `infra/compose/docker-compose.dev.yml` | ✅ Accurate |
| pnpm 10.18.1 | Confirmed in `package.json` | ✅ Accurate |
| `docs/development/BUILD_SYSTEM.md` exists | Confirmed | ✅ Accurate |
| `docs/development/COMMANDS.md` exists | Confirmed | ✅ Accurate |
| `docs/development/DISCOVERY_MAP.md` exists | Confirmed | ✅ Accurate |
| References `.windsurf/AGENTS.md` | File does not exist in repository | ❌ Broken reference |

**Action required:** Create `.windsurf/AGENTS.md` stub or update reference (AGENT-001 — already in remediation roadmap).

---

### `SECURITY.md` — Confidence: ✅ High (95%)

| Claim | Reality | Verdict |
|-------|---------|---------|
| Dev auth bypass documented | Confirmed in `SECURITY.md:39-44` | ✅ Accurate |
| JWT policy documented | Confirmed in `SECURITY.md:89-104` | ✅ Accurate |
| Vulnerability reporting process | Standard GitHub security advisory process | ✅ Accurate |

---

## 2. Architecture Documents

### `docs/architecture/system-overview.md` — Confidence: ⚠️ Medium (80%)

| Claim | Reality | Verdict |
|-------|---------|---------|
| Celery/Redis for Layer 1 async tasks | Confirmed (125 Celery refs in L1 src/) | ✅ Accurate |
| FastAPI across all services | Confirmed (409 imports) | ✅ Accurate |
| Neo4j, pgvector, LangGraph | All confirmed | ✅ Accurate |
| "Event streaming: Redis / RabbitMQ for async Celery tasks" (line 642) | Redis confirmed (38 imports); RabbitMQ has **zero** production imports | ⚠️ RabbitMQ claim is stale/aspirational |
| Temporal (mentioned in L1 orchestrator comment) | Only a comment reference — not implemented | ⚠️ Planned, not implemented |

**Action required:** Annotate Redis/RabbitMQ and Temporal as "planned, not implemented" or remove RabbitMQ reference.

---

### `docs/architecture.md` and `docs/architecture_overview.md` — Confidence: ✅ High (98%)

Both files are correctly self-marked as **redirect stubs** pointing to `docs/core-concepts/architecture.md`. They contain no stale claims — only redirect notices.

---

### `docs/core-concepts/architecture.md` — Confidence: ✅ High (90%)

Freshness marker: `last-reviewed: "2026-06-20"`. Content verified as consistent with `docs/architecture/system-overview.md`. This is the canonical architecture document.

---

## 3. Redirect/Stub Documents (Correctly Marked)

The following documents are correctly marked as redirect stubs and require no changes:

- `docs/architecture.md` — redirects to `docs/core-concepts/architecture.md`
- `docs/architecture_overview.md` — redirects to `docs/core-concepts/architecture.md`

---

## 4. Orphaned Documents (No Inbound Links)

The following `docs/` root files have zero inbound links from `AGENTS.md`, `README.md`, or `ARCHITECTURE.md` and have not been self-marked as archived:

| File | Likely Status | Recommended Action |
|------|--------------|-------------------|
| `docs/CONTRIBUTING-additions.md` | Derived/stale | Merge into `CONTRIBUTING.md` or archive |
| `docs/RELEASE_READINESS.md` | Historical snapshot | Move to `docs/archive/` |
| `docs/WORKFLOW_API_DESIGN.md` | Historical/derived | Move to `docs/archive/` or link from API docs |
| `docs/WORKFLOW_MOCK_DATA_STATUS.md` | Historical snapshot | Move to `docs/archive/` |
| `docs/contract-dashboard.md` | Unknown | Verify and link or archive |
| `docs/health-scorecard.md` | Historical snapshot | Move to `docs/archive/` |
| `docs/how-to-progressive-enforcement-rollout.md` | Derived/how-to | Link from `docs/how-to/` index or archive |
| `docs/layer3_route_ownership.md` | Derived | Link from Layer 3 docs or archive |
| `docs/legacy-table-tabs-followup.md` | Historical | Move to `docs/archive/` |
| `docs/plan-harness-mvp.md` | Historical plan | Move to `docs/archive/` |

---

## 5. Summary Scorecard

| Document | Confidence | Key Issues |
|----------|-----------|-----------|
| `README.md` | ⚠️ 70% | `make setup` overclaims |
| `ARCHITECTURE.md` | ✅ 92% | Accurate thin index |
| `AGENTS.md` | ✅ 88% | Missing `.windsurf/AGENTS.md` |
| `SECURITY.md` | ✅ 95% | No issues |
| `DESIGN.md` | ✅ 90% (unverified deep) | Assumed accurate |
| `docs/architecture/system-overview.md` | ⚠️ 80% | RabbitMQ stale; Temporal unimplemented |
| `docs/core-concepts/architecture.md` | ✅ 90% | Canonical; recently reviewed |
| `docs/architecture.md` | ✅ 98% | Correct redirect stub |
| `docs/architecture_overview.md` | ✅ 98% | Correct redirect stub |

---

*No files were modified during Phase 1.*
