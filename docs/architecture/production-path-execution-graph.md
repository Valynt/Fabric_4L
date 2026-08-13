# Production-Path Execution Graph — Meridian Certification Journey

> **Status:** WS1 deliverable of the production-path certification mission
> **Date:** 2026-07-31 · **SHA:** `44f547867fcb0c62c7ca9ded363a19da340c2250`
> **Companion:** `source-of-truth-ratification.md` (decisions D1–D11 referenced below)
> **Method:** static, read-only inspection. Edge statuses: CONFIRMED (code-verified at SHA), BROKEN (code-verified mismatch), AMBIGUOUS (compensation possible but unratified), UNWIRED (implementation exists, no runtime composition).

## 1. Journey definition

Meridian Auto scenario (D11), two tenants. One pass:

1. Authenticate tenant + user (Clerk/session → `GovernanceMiddleware`)
2. Create account (Meridian Auto) via frontend → gateway → L4
3. Submit source via frontend → gateway → L1 unified source pipeline (D3)
4. L1 fetches + normalizes content; outbox advances stages
5. L1 EXTRACTING stage → L2 `POST /v1/extract-and-ingest` (D4)
6. L2 extracts entities/relationships/claims, posts RDF → L3 `POST /v1/ingest`
7. L3 persists graph, tenant-scoped
8. Frontend triggers hypothesis generation → gateway → L4 `POST /v1/hypotheses/generate`
9. L4 workflow executes: knowledge tools (graph reads, D5), claim promotion → L5, benchmark evaluation → L6 (D7)
10. L5 validates TruthObjects; approved truths sync → L3
11. L6 comparison results attach to value case; trust state persisted (A-12 fix)
12. Frontend retrieves final value case through gateway
13. Tenant B denial sweep across every store touched

## 2. Edge register (journey order)

### E1 — Browser → Gateway (entry/auth/tenant)

- **Producer:** `apps/web/src/api/client.ts` (+ `typedClient.ts`), request ID, Clerk JWT or cookie, CSRF on mutations, no browser-derived tenant ID
- **Consumer:** `services/api` `add_gateway_governance_middleware` → typed `RequestContext`, fail-closed
- **Schema:** HTTP + auth headers; **Persistence:** none; **Idempotency:** external boundary TODO
- **Status:** CONFIRMED (controls strong; per-route consistency proven by harness)

### E2 — Frontend → Gateway route resolution (journey paths)

Default proxy: `/api/v1{segment}{path}` → gateway `/v1{segment}{path}` (`apps/web/vite.config.ts:399-403`, gateway-only by default).

| Frontend call (hook) | Gateway path | Gateway handler | Owning layer route | Status |
|---|---|---|---|---|
| `l4 /accounts*` (`useAccounts`) | `/v1/agents/accounts*` | none (gateway accounts router is `/v1/accounts`) | L4 `/v1/accounts` | **BROKEN (A-03)** |
| `l4 /hypotheses/*` (`useHypotheses`) | `/v1/agents/hypotheses/*` | none | L4 `/v1/hypotheses/*` | **BROKEN (A-03)** |
| `l4 /workflows*` (`useWorkflows`) | `/v1/agents/workflows*` | yes — record-only facade over gateway `db.agent_runs` + broken L4 `execute-step` client | L4 `/v1/workflows` | **AMBIGUOUS → must delegate (A-02, A-11)** |
| `l1 /jobs/*` (`useIngestion`) | `/v1/ingest/jobs/*` | none (gateway `jobs.router` is `/v1/jobs`) | L1 `/api/v1/ingestion/*` | **BROKEN** |
| `l3 /v1/evidence/*`, `l3 /v1/calculators/*` (`useEvidence`, `useCalculators`) | `/v1/graph/v1/*` | none; **double-`/v1` defect**: hook embeds `/v1/` inside the layer path | L3 `/v1/evidence/*`, `/v1/calculators/*` | **BROKEN (new mismatch class)** |
| `l5 /academy/*` (`useAcademy`) | `/v1/truths/academy/*` | none | L5 `/api/v1/*` | **BROKEN** |
| `l6 /datasets` etc. (`useBenchmarks`) | `/v1/benchmarks/*` | yes — `clients/layer6_client.py` with tenant + service-auth headers | L6 `/v1/benchmarks/*` | **CONFIRMED** |

**Required convergence (WS3.2):** gateway gains thin delegation routers that strip the layer segment and forward to the owning layer (`/v1/agents/* → L4 /v1/*`, `/v1/ingest/* → L1`, `/v1/graph/* → L3`, `/v1/truths/* → L5`), while record-only duplicates (D2) are removed or converted to delegation. Hooks embedding `/v1/` inside paths are fixed at the hook (upstream) — never compensated in the proxy.

### E3 — Account creation: Gateway → L4

- **Producer:** gateway delegation router (to be added, E2) · **Consumer:** L4 `accounts.router` (`/v1/accounts`)
- **Schema:** L4 account schema; **Persistence:** L4 PostgreSQL (RLS); **Status:** BROKEN today (E2), path defined

### E4 — Source intake: Frontend → Gateway → L1 unified pipeline

- **Consumer:** L1 `source_routes.py` → immutable source/version + normalized document + ingestion run + `fabric.source.normalized.v1` outbox event + coordinator `start_run`
- **Persistence:** L1 PostgreSQL (RLS) + transactional outbox
- **Idempotency:** dedupe at intake; run IDs per source version
- **Status:** CONFIRMED at intake; **downstream BROKEN (A-05)**: NORMALIZING/CHUNKING/EXTRACTING/BUILDING_CLAIMS/VALIDATING_CLAIMS/PROJECTING_SUMMARY = `NoopStageHandler` (`stage_handlers/__init__.py:25-33`)
- **Note:** initial normalized-source event carries no `stage_name`; outbox relay polls stage-transition rows — producer-only event (report §6.3)

### E5 — L1 → L2 extraction handoff

- **Canonical (D4):** EXTRACTING stage handler → L2 `POST /v1/extract-and-ingest`, idempotency key = `source_version_id`, service auth + tenant headers
- **Legacy (deprecated, D3):** Celery chain → `POST /v1/extract` only (`shared/tasks.py:990`) — extraction without graph ingestion
- **Status:** UNWIRED (canonical handler is a no-op today); legacy path CONFIRMED but non-canonical

### E6 — L2 → L3 graph ingestion

- **Producer:** L2 `Layer3KnowledgeClient` via `extract-and-ingest` · **Consumer:** L3 `ingestion.router` `POST /v1/ingest`
- **Schema:** RDF payload; **Persistence:** Neo4j tenant-scoped; **Status:** CONFIRMED — the clearest cross-layer boundary in the repo

### E7 — L4 knowledge reads (graph)

- **Producer:** L4 `tools/knowledge_tools.py` → direct `AsyncGraphDatabase.driver` Cypher, tenant-filtered, write-keywords blocked
- **Boundary:** bypasses L3 HTTP API — governed as interim shared data plane per **D5** (read-only, mandatory tenant filter, writes only via L3)
- **Status:** CONFIRMED behavior, boundary AMBIGUOUS → governed by D5 contract; migration to L3 HTTP tracked as debt

### E8 — L4 → L5 Ground Truth

- **Producer:** L4 `ground_truth_proxy` routes + `integration/layer5_client.py` (non-blocking on failure, structured error dicts)
- **Consumer:** L5 `/api/v1/truths*` · **Persistence:** L5 PostgreSQL (TruthObject, immutable validation history)
- **Schema defect (A-09):** L4 client advertises `capability|outcome|metric|benchmark|roi_assumption|competitive`; L5 `ClaimType` accepts `cost_savings_baseline|revenue_impact|efficiency_gain|risk_reduction|compliance_requirement|customer_outcome|technical_capability|market_benchmark|persona_pain_point|value_driver_metric|other` → current 422s
- **Trust defect (A-12):** L5 outage never blocks business case; no persisted grounding state
- **Status:** BROKEN (schema) + UNGROUNDED-BY-DESIGN (trust) → fixes D6 + trust-state model

### E9 — L5 → L3 truth sync

- **Producer:** L5 `integration/layer3_client.py` → `POST {L3}/api/v1/nodes`
- **Consumer:** **none** — no matching L3 route (L3 mounts `/v1/*`; compat_aliases has no nodes route)
- **Status:** BROKEN (A-08) → repoint to contracted L3 ingestion (`/v1/ingest` with Ground Truth RDF contract) or dedicated ratified route

### E10 — L4 → L6 benchmarks

- **Exists:** `interfaces/benchmark_client.py` (`IBenchmarkClient`) + `adapters/benchmark_client.py` (`HTTPBenchmarkClient`, targets L6 `/v1/benchmarks/*`)
- **Composition:** none found — adapter referenced only by interface-export tests
- **Status:** UNWIRED (A-10) → compose into L4 workflow runtime (D7)

### E11 — Gateway → L4 orchestration

- **Producer:** `services/api/app/services/agent_orchestrator.py` → `POST {L4}/internal/orchestrator/execute-step`
- **Consumer:** **none** — no matching L4 route
- **Status:** BROKEN (A-11) → align client to L4 `/v1/workflows` API (preferred, per D2 delegation) or implement + contract the internal route

### E12 — Value case retrieval → Frontend

- **Path:** L4 workflow output + L5 grounding state + L6 benchmark evidence → value case record → gateway delegation → frontend (`useBusinessCases`/`useCalculators` — currently hitting the broken `l3 /v1/calculators/*` path)
- **Status:** BROKEN (route) + MISSING (trust-state field) → fixed by E2 convergence + A-12

### E13 — Tenant B denial (cross-cutting)

- **Enforcement points:** gateway governance middleware, per-layer governance middleware, RLS `SET LOCAL app.tenant_id`, L4 Cypher tenant filters, L5/L6 tenant-scoped stores, queue/outbox tenant payloads
- **Status:** controls CONFIRMED individually; end-to-end same-tenant continuity and denied-path proof at the persistence boundary is the WS4 harness deliverable

## 3. First broken boundary (mission gate)

The first broken production boundary in journey order is **E2 (frontend → gateway route resolution)** for account creation (journey step 2), followed immediately by **E4/E5 (L1 downstream no-ops)**. Repair order follows WS3: contracts (E8 schema, E11) → routing/delegation (E2, E3) → ingestion chain (E4, E5) → reasoning/trust/benchmark (E7–E10, E12) → harness certification (E13).

## 4. Telemetry & idempotency gaps to close in WS7

- End-to-end trace continuity (one `trace_id` from browser through outbox/Celery hops) — verify, not assumed
- External-boundary idempotency keys on account/source creation
- Stage-level retry budgets in L1 coordinator (exists via `FAILED_RETRYABLE`; budget config to verify)
- Trust/grounding metrics on L4→L5 calls; benchmark participation metrics on L4→L6
