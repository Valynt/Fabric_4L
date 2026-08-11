# Source-of-Truth Ratification — Production Path Certification

> **Status:** Ratified for the production-path certification mission
> **Date:** 2026-07-31
> **Baseline SHA:** `44f547867fcb0c62c7ca9ded363a19da340c2250` (`main`)
> **Scope:** One authority per contract, configuration, schema, data plane, and fixture used by the certified L1–L6 production path. Supersedes conflicting documents for the certified path; conflicts elsewhere are tracked as drift.

## 0. Baseline record

| Item | Value |
|---|---|
| Repository | `bmsull560/Fabric_4L` |
| Local `main` SHA at mission start | `44f547867fcb0c62c7ca9ded363a19da340c2250` (2026-07-31, #1187) |
| GitHub CI state at HEAD (verified 2026-07-31 via `gh`) | **NOT GREEN — the "clean baseline" assumption is false.** Failing on `44f5478`: Build and Deploy, PR Checks, Prod Readiness Gates, Security Gates, OpenAPI Drift Check, SDK Generation, Release Evidence Bundle, Performance Load Tests, Dependabot Updates. Passing: Contract Compliance, Critical Gates, CodeQL, Frontend Route Audit Check, Generated API Freshness, OpenAPI-freshness peers, Supply Chain Integrity, Zero Trust Validation, and others. These pre-existing failures are certification blockers: the consolidated PR cannot merge on a red `main`; each failure must be triaged (fix, or prove environment-only and repair the workflow) as part of this mission's WS8. |
| Open PRs (verified 2026-07-31) | 59 open. Overlap analysis: the large majority are small code-health/dependabot PRs. PRs touching mission-critical files: **#1156** (`GetRelationshipsTool` Cypher direction — `knowledge_tools.py`), **#1152** (knowledge-tools output schemas), **#1133** (knowledge_tools.py comments), **#1160** (tenant-filter comment in Cypher), **#1154** (L3 pickle→msgpack caching), **#1135** (L1 `cleanup_old_content` perf), **#1142** (`test_routing_check.py` hostname bug). Per mission rules these are compared before being closed or superseded; small non-conflicting ones are left to merge independently. |
| Prior architecture review | 2026-07-29 report against SHA `1c95212b`; critical claims re-verified against `44f5478` before this ratification |

## 1. Decisions

### D1 — Canonical public API

**Decision:** The browser talks only to the unified API gateway (`services/api`) over one origin and one prefix: `/api/v1` (browser) → `/v1` (gateway). Layer names (L1–L6) are implementation details and never appear in browser-visible URLs.

- The Vite dev proxy is already gateway-only by default (direct layer proxies are quarantined behind `VITE_PROXY_DEBUG_DIRECT_LAYERS`, which must stay off in app flows) — `apps/web/vite.config.ts`.
- Kubernetes and Compose topologies must converge on the same gateway-only model during this mission; the `/layerN` ingress prefixes are deprecated (see D8).
- The frontend's per-layer route segments (`/agents`, `/graph`, `/truths`, … in `apps/web/src/lib/apiConfig.ts`) are an internal client convention that must resolve to real gateway routes; the gateway route table (WS1 deliverable) is the arbiter.

### D2 — System of record per domain object

| Domain object | System of record | Gateway (`services/api`) role |
|---|---|---|
| Accounts / prospects / CRM | Layer 4 | Delegate |
| Sources, crawl jobs, ingestion runs | Layer 1 | Delegate |
| Extraction jobs, entities, relationships, RDF | Layer 2 | Delegate |
| Knowledge graph, value trees, retrieval | Layer 3 | Delegate |
| Workflows, hypotheses, business cases, value drivers | Layer 4 | Delegate |
| TruthObjects, evidence, maturity | Layer 5 | Delegate |
| Benchmark datasets, comparisons, validation | Layer 6 | Delegate |
| Sessions, quotas/entitlements, aggregation | `services/api` | Owns |
| Read models / projections | `services/api` | Allowed only if labeled, derived, rebuildable |

**Rule:** gateway routes that currently persist their own copies of hypotheses, ROI calculations, evidence, signals, or value cases must delegate to the owning layer or be explicitly reclassified as rebuildable projections with a documented derivation. Record-only endpoints that appear to perform generation are removed or converted to delegation.

### D3 — Canonical Layer 1 intake model

**Decision:** The unified source pipeline (`orchestrator/coordinator.py` + `PipelineStateMachine` + transactional outbox) is the canonical intake and orchestration model. The legacy scraping-job Celery chain is **deprecated** as an orchestration path (owner: layer1-ingestion; removal target: 2026-10-31); its crawler/fetch machinery is reused by the canonical pipeline's `FetchingSourceHandler`.

Rationale: the unified pipeline already has durable state, step artifacts, idempotent stage advancement, and real handlers for the first four stages; the legacy chain duplicates orchestration semantics and terminates at extraction-only.

Required consequence: the six no-op stage handlers (A-05) are replaced with real handlers — EXTRACTION delegates to Layer 2 `extract-and-ingest` (D4), claim building/validation delegate to Layer 5, and no stage may report completion without persisted output artifacts.

### D4 — Layer 2 → Layer 3 boundary

**Decision:** `POST /v1/extract-and-ingest` is the only canonical extraction entry point for production flows. `POST /v1/extract` remains for extraction-only diagnostics and tests, never for pipeline handoff. Layer 1's canonical pipeline calls `extract-and-ingest` idempotently (idempotency key = `source_version_id`).

### D5 — Neo4j ownership

**Decision (interim ratified state):** Neo4j is a **shared internal data plane** under a formal contract, owned by Layer 3 for schema/writes, with Layer 4 granted read-only Cypher access under these rules:

- Layer 4 tools are read-only (enforced by the existing write-keyword guard in `knowledge_tools.py`).
- Every L4 query must be tenant-filtered; cross-tenant reads are defects proven by the certification harness at the persistence boundary.
- All graph **writes** flow through Layer 3's HTTP API only.
- Schema evolution, query policy, and observability conventions are owned by L3 and documented in `docs/architecture/cross-layer-contracts.md`.

**Tracked debt:** migrate L4 graph reads behind L3's HTTP retrieval API (owner: layer4-agents + layer3-knowledge; target: 2026-Q4). This decision is explicitly interim and reversible; it is recorded here so the boundary is governed rather than ambiguous.

### D6 — Claim taxonomy

**Decision:** Layer 5's `ClaimType` enum (`services/layer5-ground-truth/src/layer5_ground_truth/models/truth_object.py`) is the canonical claim taxonomy. A versioned copy is published under `contracts/jsonschema/` (or `packages/platform-contract/`) and Layer 4's Ground Truth client is aligned to it; a contract test fails CI on drift. Layer 4's legacy values (`capability`, `outcome`, `metric`, `benchmark`, `roi_assumption`, `competitive`) are mapped onto canonical values at the client boundary — no second taxonomy is created.

### D7 — Benchmark contract

**Decision:** Layer 6 owns benchmark datasets, comparison, and validation schemas (`/v1/benchmarks/*`). Layer 4's `IBenchmarkClient`/`HTTPBenchmarkClient` aligns to those routes and is composed into L4 workflow runtime; the unified API's existing Layer 6 client is the gateway delegation path. Benchmark datasets used by certification must be pre-existing, governed seed data — never created by the test immediately beforehand.

### D8 — Canonical route table

**Decision:** `docs/reference/service-routing-and-api-version-matrix.md` is the canonical routing reference and is corrected during this mission (its port column is stale per its own audit note). One gateway-route table (WS1) becomes the single mapping from browser paths to internal services, rendered identically by Vite, Compose, K8s ingress, and CI. The `/layerN` K8s ingress scheme and direct browser-to-layer routes are deprecated. Note: `canonical-paths-policy.md` is referenced by `apps/web/vite.config.ts` and `AGENTS.md` but does not exist — the routing matrix absorbs that role (drift A-14).

### D9 — Tenant context & isolation

**Decision:** Unchanged from `docs/contract.md` §2.1/§2.2 — `GovernanceMiddleware` establishes an immutable request context; cross-service propagation via signed headers; persistence isolation via PostgreSQL RLS with `SET LOCAL app.tenant_id`. Certification proves the same authenticated tenant survives every hop and that denied paths fail closed at the persistence boundary (not only in route handlers).

### D10 — LLM dependency in the certified path

**Decision:** The certification harness runs deterministically without live model credentials, using the repository's existing deterministic/stub LLM provider configuration for agent steps. A separate, optional live-provider evidence mode uses `scripts/validation/generate_live_llm_provider_evidence.py` and is not required for certification pass/fail. No business evidence, confidence scores, or benchmark values may be invented by the harness; deterministic means reproducible, not fabricated.

### D11 — Certification scenario

**Decision:** The Meridian Auto scenario is canonical, seeded from `scripts/fixtures/meridian-automotive.ts` / `scripts/db/seed-e2e-data.ts` into two certification tenants (Tenant A under test, Tenant B for isolation denial). If fixture gaps appear, the fixture is extended — the scenario is not swapped.

## 2. Conflict register (documents superseded for the certified path)

| Conflict | Superseded | Authority |
|---|---|---|
| External routing scheme | K8s `/layerN` ingress; direct Vite layer proxies | D1 + routing matrix (D8) |
| Product data ownership | `services/api` persistence facade for domain objects | D2 |
| L1 orchestration | Legacy scraping Celery chain | D3 |
| Extraction entry point | `/v1/extract` pipeline handoff | D4 |
| Graph access | Ungoverned L4 direct Neo4j | D5 |
| Claim types | L4 client-advertised taxonomy | D6 |
| Missing policy doc | `canonical-paths-policy.md` (referenced, nonexistent) | D8 routing matrix |

## 3. What this document does not do

- It does not weaken any gate, threshold, or security control.
- It does not authorize new compatibility shims; D3's deprecation and D5's interim state each carry a named owner and removal target.
- It is revisited if the WS1 execution graph proves a decision unimplementable; changes require editing this file in the same PR.
