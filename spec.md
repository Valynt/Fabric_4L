# Value Fabric Platform — Launch & Hardening Roadmap Spec

**Date:** 2026-05-21  
**Status:** Draft — awaiting confirmation  
**Phases:** Phase 1 (GA-blocking), Phase 2 (post-launch hardening), Phase 3 (debt retirement)
**Supersedes:** 24-Hour Hackathon Sprint spec (Sprint 4/5/6)

---

## Problem Statement

Value Fabric has reached ≥85% assurance score with all code-level P0/P1 blockers resolved (Sprint 5, 2026-05-19). The remaining work falls into three categories:

1. **GA-blocking (Phase 1, 1–2 weeks):** Four items must land before production launch — L3 Neo4j tenant scoping hardening with hostile tests and schema migrations, L3 import topology fix unblocking 14 test files (~22 tests), a live cross-layer E2E critical-path smoke, and formal sign-off collection.
2. **Post-launch hardening (Phase 2, first 30 days):** L1 ingestion productionization, observability/alerting, L4 checkpoint/resume hardening, RFC-001 formula scenario endpoint, and per-tenant rate-limit/feature-flag UI.
3. **Debt retirement and feature expansion (Phase 3, Q3 2026):** Backend and frontend shim removal on schedule, auth/SSO closure, L2 reference model integration as a pack, L3 performance tuning, and cross-phase always-on discipline.

---

## Current State Summary

| Area | State |
|---|---|
| Launch readiness | ≥85% assurance score — production-ready threshold met (canonical: `docs/readiness/current.md`) |
| All code-level P0/P1 blockers | Resolved 2026-05-19 (Sprint 5) |
| Frontend Vitest | 1,773/1,773 passing (140 files) |
| Backend arch/cache/contract/unit | 677/677 passing |
| Security P0/P1 suites | 78/78 passing |
| Remaining open blockers | All `REQUIRES_ENVIRONMENT` (infra/live-stack dependent) |
| L3 import topology | 14 test files blocked by `ModuleNotFoundError` under repo-root pytest |
| L3 Neo4j schema | tenant_id indexes/constraints not yet migrated for 7 node labels |
| Hostile cross-tenant tests | Missing for benchmarks, variables, models, formula_governance routes |

---

## Phase 1 — Launch Path (GA-blocking, 1–2 weeks)

### 1.1 L3 Neo4j Tenant Scoping Hardening

**Context:** Code inspection confirms `benchmarks.py`, `variables.py`, `formula_governance.py`, and `models_router.py` already contain `tenant_id` in MATCH/WHERE clauses. `entities.py` was fixed in Sprint 5. The remaining gaps are: (a) no Neo4j schema migrations enforcing `tenant_id` on node labels, and (b) no hostile cross-tenant tests for these four route modules.

**Requirements:**

1. Create a Neo4j schema migration script (Cypher or Python) that adds:
   - `CREATE CONSTRAINT IF NOT EXISTS FOR (n:Benchmark) REQUIRE n.tenant_id IS NOT NULL`
   - `CREATE INDEX IF NOT EXISTS FOR (n:Benchmark) ON (n.tenant_id)`
   - Same pattern for `:BenchmarkPolicy`, `:Variable`, `:SourceBinding`, `:ValueModel`, `:Formula`, `:FormulaVersion`
   - Migration must be idempotent (`IF NOT EXISTS`) and tracked in a migrations manifest.
2. Add hostile cross-tenant tests under `tests/security/`:
   - `test_benchmarks_cross_tenant_isolation.py`
   - `test_variables_cross_tenant_isolation.py`
   - `test_models_cross_tenant_isolation.py`
   - `test_formula_governance_cross_tenant_isolation.py`
   - Each file must cover: Tenant A cannot read Tenant B nodes, Tenant A cannot write/mutate Tenant B nodes, missing tenant context fails closed (401/403).
3. Run `pytest tests/security/ tests/layer3/ -q` and confirm green.

**Acceptance Criteria:**
- [ ] Neo4j migration script exists, is idempotent, covers all 7 node labels.
- [ ] Migration is tracked in a manifest or migration registry file.
- [ ] 4 hostile test files exist under `tests/security/`, each with ≥3 test cases.
- [ ] `pytest tests/security/ tests/layer3/ -q` passes with no failures on tenant isolation suites.
- [ ] No existing passing tests are broken.

---

### 1.2 L3 Import Topology Fix

**Context:** 14 test files fail to collect because bare `api.*` and `config.*` imports don't resolve when pytest runs from the repo root under `importlib` mode. The `value_fabric.layer3` shim correctly appends `services/layer3-knowledge/src` to `__path__`, but pytest's `importlib` mode doesn't propagate that path for sub-imports. There is also a `config.Settings` namespace collision between layer3 and layer4-agents.

**Fix strategy:** pytest.ini rootdir + conftest (do not modify the shim).

**Requirements:**

1. Add or update `conftest.py` at `services/layer3-knowledge/` to insert `services/layer3-knowledge/src` into `sys.path` at collection time.
2. Update `pytest.ini` (or `pyproject.toml` `[tool.pytest.ini_options]`) to include `services/layer3-knowledge` in `testpaths` so the conftest is picked up when running from repo root.
3. Resolve the `config.Settings` namespace collision — layer3 tests must import layer3's `config.Settings`, not layer4's.
4. Do not modify `value_fabric/layer3/__init__.py`.

**Affected files (14):**
`tests/layer3/test_endpoint_tenant_isolation.py`, `test_error_handling_regression.py`, `test_model_registry_tenant_context.py`, `test_models_error_sanitization.py`, `test_variables_tenant_context_fail_closed.py`, `test_api_rate_limit_contract.py`, `test_graph_repository_tenant_contracts.py`, `test_typed_payloads.py`, `test_ingest_tenant_fail_closed.py`, `test_rate_limit_manager_types.py`, `tests/ci/test_layer3_settings_import_compat.py`, `tests/performance/test_performance_optimizations.py`, `tests/security/test_layer3_similarity_roi_tenant_isolation.py`, `tests/security/test_neo4j_cross_tenant_write_isolation.py`

**Acceptance Criteria:**
- [ ] All 14 files collect without `ModuleNotFoundError` or `ImportError`.
- [ ] `pytest tests/layer3/ --collect-only -q` shows 0 collection errors for these files.
- [ ] Layer3 `config.Settings` resolves to `services/layer3-knowledge/src/config/`, not layer4's config.
- [ ] No regression in currently-passing layer3 or layer4 tests.

---

### 1.3 Live Cross-Layer E2E (Critical Path L1→L6)

**Context:** The blocker register requires live E2E evidence. Minimum scope for Phase 1 sign-off is one critical-path smoke: ingest → extract → graph → agent → ground-truth → benchmark. `docker-compose.live.yml` exists and can be used locally; evidence must be committed as an artifact.

**Requirements:**

1. Bring up all six layer services via `docker-compose.live.yml` (or `docker-compose.test.yml`).
2. Execute the critical-path smoke sequence:
   - POST to L1 `/api/v1/ingestion/jobs` → confirm job created
   - Trigger L2 extraction on the ingested content → confirm entity extracted
   - Verify L3 graph node created for the entity (GET `/api/v1/entities`)
   - Trigger L4 agent workflow (ROI or business case) → confirm workflow completes
   - Verify L5 ground-truth validation passes for the workflow output
   - Verify L6 benchmark lookup returns a result
3. Capture evidence as `signoff-evidence/e2e-critical-path-$(date +%Y%m%d).json` with per-layer health status, request/response summaries, and timestamps.
4. Commit the evidence artifact to `signoff-evidence/`.
5. Update `docs/readiness/launch-decision-artifact.md` "Live workflow validation" row to `PASS` with artifact reference.

**Acceptance Criteria:**
- [ ] All six layer health endpoints return 200 during the run.
- [ ] Critical-path sequence completes end-to-end without error.
- [ ] Evidence JSON artifact committed under `signoff-evidence/`.
- [ ] `docs/readiness/launch-decision-artifact.md` updated with artifact reference and PASS status.

---

### 1.4 Sign-off Completion

**Context:** `docs/readiness/launch-decision-artifact.md` is the canonical sign-off document. `docs/LAUNCH_RUNBOOK.md` is the execution runbook. Sign-off happens after 1.1–1.3 land (Option A — no conditional sign-off).

**Requirements:**

1. Verify 1.1, 1.2, and 1.3 acceptance criteria are all met.
2. Update `docs/readiness/launch-decision-artifact.md` with evidence references for 1.1, 1.2, 1.3.
3. Collect countersignatures from Eng, Sec, Product, Ops in the artifact's sign-off table.
4. Execute `docs/LAUNCH_RUNBOOK.md` steps in order.

**Acceptance Criteria:**
- [ ] All four sign-off roles have countersigned `launch-decision-artifact.md`.
- [ ] `docs/LAUNCH_RUNBOOK.md` execution log attached or referenced.
- [ ] `docs/readiness/current.md` reflects final launch state.

---

## Phase 2 — Post-Launch Hardening (first 30 days, parallel workstreams)

### 2.1 L1 Ingestion Productionization (detailed)

**Context:** L1 has Celery/Redis wiring implemented but the scheduler priority queue (`src/scheduler/priority_queue.py`) is an in-memory stub. Proxy rotation is absent. Celery→L2 handoff is not wired.

**Requirements:**

1. **Redis-backed scheduler queue:** Replace the in-memory priority queue with a Redis-backed implementation using `redis-py` async client. Preserve the existing `PriorityQueue` interface so callers are unaffected.
2. **Celery→L2 wiring:** Wire `services/layer1-ingestion/src/shared/tasks.py` Celery tasks to publish extraction jobs to L2's ingestion endpoint on job completion. Use the existing `Layer2Client` or equivalent HTTP client.
3. **Proxy rotation:** Implement a basic proxy rotation pool in `services/layer1-ingestion/src/crawler/` that cycles through proxies from a configurable `PROXY_LIST` env var (comma-separated URLs). Fail open (no proxy) if list is empty or env var is unset.
4. **Postgres job state:** Confirm `IngestionJob` model has `tenant_id`, `status`, `started_at`, `completed_at`, `error_message`. Add any missing fields with an Alembic migration.
5. Add unit tests for the Redis queue and Celery→L2 wiring. Mock Redis and L2 client in tests.
6. Add `PROXY_LIST` to `.env.example` with an empty default and documentation comment.

**Acceptance Criteria:**
- [ ] Redis-backed priority queue passes existing scheduler tests.
- [ ] Celery task publishes to L2 on job completion (verified by unit test with mock L2 client).
- [ ] Proxy rotation cycles through configured proxies; falls back gracefully when list is empty.
- [ ] `IngestionJob` model has all required state fields; Alembic migration exists for any new columns.
- [ ] `pytest services/layer1-ingestion/ -q` passes.
- [ ] `PROXY_LIST` documented in `.env.example`.

---

### 2.2 Observability & Alerting (detailed)

**Context:** Prometheus alert rules exist in `monitoring/alerting/rules-production.yml`. Alertmanager configs exist. Gaps: per-layer SLOs, on-call receiver wiring, request-ID propagation audit.

**Requirements:**

1. **Per-layer SLO alert rules** — extend `monitoring/alerting/rules-production.yml` with rules for each of L1–L6:
   - Error rate > 1% over 5m → `warning`; > 5% over 5m → `critical`
   - P95 latency > 2s over 5m → `warning`; > 5s → `critical`
   - Service down (no scrape) > 1m → `critical`
2. **On-call wiring** — update `monitoring/alertmanager/alertmanager-production.yml` to route `critical` severity alerts to the on-call receiver. Document receiver config in `docs/runbooks/on-call-setup.md` (create if absent).
3. **Request-ID propagation audit** — audit all six layer FastAPI apps for `X-Request-ID` header propagation. Each layer must: accept `X-Request-ID` from upstream or generate one if absent; include it in all structured log entries; forward it to downstream layer calls. Document gaps in `docs/governance/request-id-propagation-audit.md`.
4. **Synthetic alert test** — document a manual test procedure: kill one service in docker-compose, confirm alert fires within 2 minutes. Attach evidence.

**Acceptance Criteria:**
- [ ] Per-layer SLO rules exist in `monitoring/alerting/rules-production.yml` for all 6 layers (error rate, latency, service-down).
- [ ] Alertmanager routes `critical` to on-call receiver; config is documented.
- [ ] Request-ID audit doc exists at `docs/governance/request-id-propagation-audit.md`; all gaps have a remediation ticket or are fixed inline.
- [ ] Synthetic alert test evidence documented.

---

### 2.3 L4 Checkpoint/Resume Hardening (stub)

**Context:** L4 has `state_manager.py`, `executor.py`, `replay.py`, and `workflows/base.py` with checkpoint/resume logic. Gaps: crash-resume reliability, idempotent tool replay, schema-version pinning.

**Requirements (detail in Phase 2 sprint planning):**
1. Workflow must resume from last checkpoint after process restart.
2. Tool calls must be replayable without side effects (idempotency key or deduplication).
3. Checkpoint payloads must include a schema version; mismatches must fail closed with a clear error.
4. Tests using `services/layer4-agents/src/workflows/` fixtures covering crash-resume and idempotent replay.

---

### 2.4 RFC-001 Formula Scenario Endpoint

**Context:** RFC-001 is approved (2026-04-27). `useFormulaScenario` frontend hook exists (Sprint 4, commit `4978c58`). The backend handler and OpenAPI contract entry are missing.

**Requirements:**

1. **OpenAPI contract:** Add `POST /api/v1/formulas/scenario` to `contracts/openapi/layer3-knowledge.json` with `ScenarioRequest` and `ScenarioResponse` schemas per RFC-001:
   - `ScenarioRequest`: `formula_id` (string, required), `adjustments[]` (`variable_id`, `new_value`)
   - `ScenarioResponse`: `formula_id`, `original_value`, `adjusted_value`, `delta_percentage`, `new_roi`, `new_payback_months`, `warnings[]`
2. **Route handler:** Implement in `services/layer3-knowledge/src/api/routes/formulas.py` (or new `scenario.py`):
   - Validate `formula_id` belongs to the authenticated tenant via tenant-scoped Neo4j lookup.
   - Cross-tenant `formula_id` returns 404 (not 403, to avoid enumeration).
   - Missing tenant context returns 401.
   - Compute original values, apply adjustments, return `ScenarioResponse`.
3. **Contract test:** Add `tests/contract/test_formula_scenario_contract.py` asserting response shape matches OpenAPI spec.
4. **Frontend hook alignment:** Verify `useFormulaScenario` calls the correct path and maps the response correctly. Update if needed.
5. Run `python scripts/ci/platform_contract_lint.py` to confirm no drift.

**Acceptance Criteria:**
- [ ] `contracts/openapi/layer3-knowledge.json` contains `POST /formulas/scenario` with correct schemas.
- [ ] Handler returns correct `ScenarioResponse` for valid input.
- [ ] Cross-tenant `formula_id` returns 404; missing tenant context returns 401.
- [ ] Contract test passes.
- [ ] `useFormulaScenario` hook calls the correct endpoint and maps response correctly.
- [ ] `platform_contract_lint.py` passes with no new drift.

---

### 2.5 Per-Tenant Rate Limit + Feature Flag UI (stub)

**Context:** Per-tenant rate limiting and feature flags are fully implemented (Tasks 107/108). Gap: admin surface in `apps/web/src/routes/pages/settings/`.

**Requirements (detail in Phase 2 sprint planning):**
1. Admin settings page at `/settings/rate-limits` showing per-tenant rate limit config (read + write).
2. Admin settings page at `/settings/feature-flags` showing feature flag toggles per tenant.
3. Follow `DESIGN.md` — use `PageShell`, `PageHeader`, horizontal tabs, existing shadcn/ui primitives.
4. TanStack Query hooks for read/write. Mutations must show loading/error/success states.

---

## Phase 3 — Debt Retirement & Feature Expansion (Q3 2026)

### 3.1 Backend Shim Removal

Removal cadence: one shim per sprint (continuous). No big-bang debt-burn week.

| ID | Path | Deadline |
|---|---|---|
| COMPAT-L1-001 | `services/layer1-ingestion/src/api/routes/compatibility.py` | 2026-08-31 |
| COMPAT-L3-001 | `value_fabric/layer3/api/routes/compat_aliases.py` | 2026-08-31 |
| COMPAT-L3-002 | `value_fabric/layer3/api/routes/entity_compat.py` | 2026-08-31 |
| COMPAT-L3-004 | `value_fabric/layer3/api/compat_wiring.py` | 2026-08-31 |
| COMPAT-L4-001 | `services/layer4-agents/src/api/routes/frontend_compat.py` | 2026-08-31 |
| COMPAT-L5-001 | `value_fabric/layer5/` (package shim tree) | 2026-09-30 |
| COMPAT-L3-003 | `services/layer3-knowledge/src/` (mirrored tree) | 2026-10-31 |

**Per-shim removal checklist:**
1. Confirm zero active imports (grep + CI check).
2. Delete the shim file/tree.
3. Delete compatibility tests that only validated shim behavior.
4. Update `compatibility-debt-registry.md` (strikethrough row + removal date).
5. Run `pnpm --dir apps/web run check:compatibility-shims-registered` and `make verify`.

---

### 3.2 Frontend Shim Cleanup (18 items)

Removal order (low-risk first):
1. Type export shims (COMPAT-WEB-006 through WEB-009, WEB-017) — June 2026
2. Hook re-export shims (WEB-003, WEB-005, WEB-013, WEB-015) — July 2026
3. UI primitive shims (WEB-010, WEB-011) — July 2026
4. Auth/session shims (WEB-002, WEB-007) — July 2026
5. AppShell/RightRail controlled-state shims (WEB-012, WEB-013) — August 2026
6. Auth provider/route shims (WEB-014, WEB-016) — September 2026

Same per-shim checklist as 3.1.

---

### 3.3 Auth/SSO Closure (stub)

1. Verify backend OIDC endpoints are reachable and return correct token shapes.
2. Remove legacy Microsoft provider key (COMPAT-WEB-014) after tenant migration confirmed.
3. Add SSO E2E Playwright test: login → callback → protected route.

---

### 3.4 L2 Reference Model Integration — APQC/BIAN/FIBO (stub)

- Ship as a pack under `packs/` per AGENTS.md §13. Do not modify core extraction logic.
- Pack provides ontology mappings from extracted entities to APQC/BIAN/FIBO taxonomy nodes.
- Contract tests verify pack-loaded entities map to reference taxonomy.

---

### 3.5 L3 Performance Tuning (stub)

- Profile under tenant load (k6 or locust).
- Cache where >20% latency gain is measurable.
- Document decisions in an ADR under `docs/explanations/adr/`.

---

## Cross-Phase Always-On Discipline

These apply to every PR across all phases:

1. **Contract-first:** Regenerate generated types after any OpenAPI change. Run `python scripts/ci/platform_contract_lint.py` before merge. `contracts/drift-allowlist.yaml` must not expand without Platform Architecture approval.
2. **Hostile test per new endpoint:** Every new API endpoint must have a cross-tenant hostile test.
3. **Test failure burn-down:** Target the 37 logic/assertion failures and 56 fixture-missing failures from `reports/TEST_REPORT_2026-05-17.md`. Assign 2–3 per sprint.
4. **Diataxis doc parity:** New features must include at least a how-to guide or reference entry per AGENTS.md §16.

---

## Verification Matrix

| Phase | Gate | Command | Pass Condition |
|---|---|---|---|
| 1.1 | Tenant isolation tests | `pytest tests/security/ tests/layer3/ -q` | 0 failures on tenant isolation suites |
| 1.2 | Import topology | `pytest tests/layer3/ --collect-only -q` | 0 collection errors for 14 files |
| 1.3 | E2E critical path | `docker-compose -f docker-compose.live.yml up` + smoke script | All 6 layers 200; artifact committed |
| 1.4 | Sign-off | Manual | 4 countersignatures in launch-decision-artifact.md |
| 2.1 | L1 tests | `pytest services/layer1-ingestion/ -q` | 0 failures |
| 2.2 | Observability | Synthetic alert test | Alert fires within 2 min of service kill |
| 2.4 | RFC-001 contract | `python scripts/ci/platform_contract_lint.py` | No new drift |
| All | Full platform | `make verify` | Green |

---

## Key Decisions

1. **Sign-off ordering:** Sign after 1.1/1.2/1.3 land. No conditional sign-off.
2. **Shim removal cadence:** Continuous (one per sprint), not big-bang August debt-burn.
3. **RFC-001 timing:** Phase 2 (hook already exists; backend is low-risk).
4. **E2E minimum scope:** Critical path L1→L6 only for Phase 1 sign-off.
5. **Import topology fix:** pytest.ini rootdir + conftest approach; do not modify the shim.
6. **Phase 2 spec depth:** L1 productionization and observability in full detail; L4 checkpoint and rate-limit UI as stubs.
7. **Reference models:** Land in `packs/` not core (AGENTS.md §13).
