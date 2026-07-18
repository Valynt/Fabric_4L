# Value Fabric — Engineering Quality Baseline Assessment

**Date:** 2026-07-10  
**Status:** Partially stale — audit correction note added 2026-07-18. The Layer 1 type-check failure and `services/layer2-5-signals/` path reference below have been corrected since the baseline was captured.
**Assessor:** Kimi Code CLI (goal mode)  
**Repository:** `/home/ubuntu/Fabric_4L` (ValuePact / Value Fabric)  
**Scope:** Baseline assessment only — no source-code changes were made except installing frontend dependencies (`pnpm install --frozen-lockfile`) so that validation commands could run.

> **Audit correction (2026-07-18):** `make typecheck-layer1` now passes (`Success: no issues found in 15 source files`), and the Layer 2.5 service directory is `services/layer2-5-signal-refinery/`, not `services/layer2-5-signals/`. Treat the type-check finding as resolved; re-run `make typecheck-layer1` before the next baseline update.

---

## 1. Executive Summary

The Value Fabric monorepo is a large, contract-aware, six-layer platform (L1–L6 plus frontend and shared packages) with strong architectural intent: canonical service paths, strict layer boundaries, tenant isolation, OpenAPI-first contracts, and pnpm-only frontend governance. The codebase is **well organized at the structural level** but currently **fails to pass its own validation gate** (`make verify`) because of type-check errors in Layer 1 and a test environment that lacks Redis, causing widespread `503 Service Unavailable` failures in the tenant kill-switch middleware across Layers 2, 2.5, and 5.

Principal risks:

1. **Validation gate is red.** `make verify` fails on `typecheck-layer1`. Many layer test suites are red in this environment, primarily because Redis is not available.
2. **Layer 1 has real static-type and unit-test defects.** `mypy` reports 11 errors in two files, and three unit tests fail for non-environment reasons.
3. **Test suites are not hermetic with respect to tenant governance.** The shared identity/kill-switch middleware returns `503 tenant_status_unavailable` when Redis is absent, which makes hundreds of tests fail even though the business logic under test may be correct.
4. **Frontend has a small set of real regressions.** Six tests fail (out of 1,855) in routing, API-client error handling, session storage, and layout landmarks.
5. **Contract test runner is not runnable without extra dependencies.** `make contract-tests` aborts because `pymupdf4llm` and `pytesseract` are missing from the active Python environment.

Overall quality direction: the project has invested heavily in linting, formatting, contract gates, and documentation. The next phase should harden the *inner loop* so that `make verify` and the per-layer test commands pass in a clean checkout without requiring a full Docker stack.

---

## 2. Inventory

### 2.1 Repository context

- **Languages / frameworks:** Python 3.11+ (FastAPI, Pydantic v2, SQLAlchemy/Alembic, pytest), TypeScript/React (Vite, TanStack Query, Zustand, Tailwind, shadcn/ui), Node.js 22.12.0+, pnpm 10.18.1, Docker Compose.
- **Build entry points:** `Makefile` (per-layer targets), `package.json` / `pnpm-workspace.yaml` (frontend and shared packages).
- **Source-of-truth docs:** `AGENTS.md`, `DESIGN.md`, `docs/development/BUILD_SYSTEM.md`, `docs/development/COMMANDS.md`, `docs/development/DISCOVERY_MAP.md`.
- **CI:** `.github/workflows/pr-checks.yml` — structural-preflight, per-layer lint/typecheck/test, contract checks, production-readiness gate.

### 2.2 Main components

| Component | Path | Responsibility |
|---|---|---|
| Frontend | `apps/web/` | React SPA, API clients, TanStack Query hooks, pages, design system |
| Layer 1 — Ingestion | `services/layer1-ingestion/` | Playwright crawling, Celery jobs, Redis queues, PostgreSQL ingestion state |
| Layer 2 — Extraction | `services/layer2-extraction/` | Pydantic v2 extraction, LLM extraction, RDF/OWL, provenance |
| Layer 2.5 — Signals | `services/layer2-5-signals/` | Signal lifecycle, trust scoring, review/promote flows |
| Layer 3 — Knowledge | `services/layer3-knowledge/` | Neo4j, GraphRAG, hybrid retrieval, pgvector, subgraph APIs |
| Layer 4 — Agents | `services/layer4-agents/` | LangGraph workflows, ROI calculator, business case generation |
| Layer 5 — Ground Truth | `services/layer5-ground-truth/` | TruthObject validation, maturity ladder, value claims, model registry |
| Layer 6 — Benchmarks | `services/layer6-benchmarks/` | Peer comparison, statistical validation, datasets |
| Shared Python | `packages/shared/src/value_fabric/shared/` | Tenant context, base models, FastAPI middleware, identity |
| Shared TS/ESLint | `packages/eslint-plugin-fabric-contracts/` | Cross-layer contract lint rules |
| Contracts | `contracts/openapi/`, `contracts/jsonschema/` | API and schema source of truth |
| Tests | `tests/contract/`, `tests/security/`, `tests/backend_integrated/` | Cross-layer contract, security, and integrated tests |

### 2.3 Dependency directions

- **Frontend → Layer 1–6 REST APIs** via generated/typed API clients (TanStack Query + Zod validation). Layer 7 routing prefixes are compile-time env driven (`VITE_L1_PREFIX` … `VITE_L7_PREFIX`).
- **Layers share Python via `packages/shared/`** imported as `value_fabric.shared.*`. No service imports python files from another service.
- **Inter-service communication is network-based** (REST contracts), not direct imports.
- **Database / stateful dependencies:** PostgreSQL (per-service), Redis (queues/cache/tenant kill switch), Neo4j (Layer 3), Celery workers (Layer 1).

### 2.4 Public interfaces

- REST APIs for each layer under `services/layer{N}-*/src/**/api/routes/`.
- OpenAPI specs in `contracts/openapi/`.
- Frontend public entry points in `apps/web/src/main.tsx` and route definitions under `apps/web/src/routes/`.

### 2.5 Data flows & stateful boundaries

```text
External sources → L1 Ingestion (PostgreSQL + Redis queues)
               → L2 Extraction (Pydantic models, provenance, RDF/OWL)
               → L2.5 Signals (signal lifecycle, trust score)
               → L3 Knowledge Graph (Neo4j + pgvector)
               → L4 Agents (LangGraph state + checkpoints)
               → L5 Ground Truth (TruthObject, value claims, model registry)
               → L6 Benchmarks (datasets, peer comparison)
```

Tenant isolation is enforced by the shared FastAPI middleware using authenticated context and a Redis-backed tenant kill switch.

---

## 3. Validation Results

### 3.1 Environment note

- Python dependencies were already installed; `pytest` runs against the active interpreter (`3.11.15`).
- Frontend dependencies were missing (`node_modules` existed but `vitest` and `@types/node` were absent). A root `pnpm install --frozen-lockfile` was executed so that frontend lint/typecheck/test could run.
- **Redis was not running**, which materially affects Layers 2, 2.5, and 5 because the shared tenant kill-switch middleware checks tenant status in Redis and returns `503 tenant_status_unavailable` when it cannot connect.

### 3.2 Summary table

| Command | Result | Notes |
|---|---|---|
| `make lint-layer1` | ✅ pass |  |
| `make lint-layer2` | ✅ pass |  |
| `make lint-layer2-5` | ✅ pass |  |
| `make lint-layer3` | ✅ pass |  |
| `make lint-layer4` | ✅ pass |  |
| `make lint-layer5` | ✅ pass |  |
| `make lint-layer6` | ✅ pass |  |
| `make typecheck-layer1` | ❌ fail | 11 mypy errors in 2 files |
| `make typecheck-layer2` | ✅ pass |  |
| `make typecheck-layer2-5` | ✅ pass |  |
| `make typecheck-layer3` | ✅ pass |  |
| `make typecheck-layer4` | ✅ pass | informational untyped-function notes only |
| `make typecheck-layer5` | ✅ pass |  |
| `make typecheck-layer6` | ✅ pass |  |
| `make test-layer1` | ❌ fail | 3 failed, 602 passed, 32 skipped |
| `make test-layer2` | ❌ fail | 28 failed, 688 passed, 3 skipped |
| `make test-layer2-5` | ❌ fail | 40 failed, 51 passed |
| `make test-layer3` | ✅ pass | 799 passed, 3 skipped |
| `make test-layer4` | ✅ pass | 2165 passed, 15 skipped |
| `make test-layer5` | ❌ fail | 117 failed, 393 passed, 14 skipped |
| `make test-layer6` | ✅ pass | 152 passed, 2 skipped |
| `pytest tests/security` | ✅ pass | 5 passed, 53 deselected |
| `pnpm --dir apps/web run lint` | ✅ pass | hygiene, explicit-any threshold, legacy imports, shims |
| `pnpm --dir apps/web run typecheck` | ✅ pass | `tsc --noEmit` clean |
| `pnpm --dir apps/web run test` | ❌ fail | 4 failed test files, 6 failed tests, 1849 passed |
| `make verify` | ❌ fail | fails at `typecheck-layer1` |
| `make contract-tests` | ❌ fail | internal error: missing `pymupdf4llm` and `pytesseract` |
| `make check-conflict-markers` | ✅ pass | no unresolved markers |
| `make check-migration-heads` | ✅ pass | one Alembic head per maintained service |
| `make check-pytest-skip-governance` | ⚠️ partial | 3 skipped entries tracked; pytest collection exited non-zero |

### 3.3 Detailed command output

#### Python lint (all layers)

All seven per-layer lint targets reported `All checks passed!`.

#### Layer 1 type check (`make typecheck-layer1`)

```text
src/layer1_ingestion/orchestrator/stage_handlers/resolving_connector.py:84: error: "object" has no attribute "mark_step_running"  [attr-defined]
src/layer1_ingestion/orchestrator/stage_handlers/resolving_connector.py:86: error: "object" has no attribute "tenant_id"  [attr-defined]
src/layer1_ingestion/orchestrator/stage_handlers/resolving_connector.py:87: error: "object" has no attribute "source"  [attr-defined]
src/layer1_ingestion/orchestrator/stage_handlers/resolving_connector.py:88: error: "object" has no attribute "source"  [attr-defined]
src/layer1_ingestion/orchestrator/stage_handlers/resolving_connector.py:89: error: "object" has no attribute "version"  [attr-defined]
src/layer1_ingestion/orchestrator/stage_handlers/resolving_connector.py:94: error: "object" has no attribute "input_artifact_ids"  [attr-defined]
src/layer1_ingestion/orchestrator/connector_resolution.py:281: error: Argument "custody_mode" to "ConnectorResolution" has incompatible type "str"; expected "CustodyMode"  [arg-type]
src/layer1_ingestion/orchestrator/connector_resolution.py:302: error: Argument "custody_mode" to "ConnectorResolution" has incompatible type "str"; expected "CustodyMode"  [arg-type]
src/layer1_ingestion/orchestrator/connector_resolution.py:320: error: Argument "custody_mode" to "ConnectorResolution" has incompatible type "str"; expected "CustodyMode"  [arg-type]
src/layer1_ingestion/orchestrator/connector_resolution.py:340: error: Argument "custody_mode" to "ConnectorResolution" has incompatible type "str"; expected "CustodyMode"  [arg-type]
src/layer1_ingestion/orchestrator/connector_resolution.py:363: error: Argument "custody_mode" to "ConnectorResolution" has incompatible type "str"; expected "CustodyMode"  [arg-type]
Found 11 errors in 2 files (checked 15 source files)
```

#### Layer 1 tests (`make test-layer1`)

```text
FAILED tests/unit/test_connector_resolution.py::test_resolve_connector_for_audio_requires_storage_ref
FAILED tests/unit/test_connector_resolution.py::test_resolve_connector_for_meeting_requires_storage_ref
FAILED tests/unit/test_orchestrator.py::TestNoopStageHandler::test_handler_reaches_ready
3 failed, 602 passed, 32 skipped
```

- The audio/meeting tests expect `ConnectorResolutionError` to be raised when `storage_ref` is missing; it is not raised.
- The noop test fails with `UUID is not JSON serializable` while persisting `ingestion_run_steps.input_artifact_ids`.

#### Layer 2 tests (`make test-layer2`)

```text
28 failed, 688 passed, 3 skipped
```

Failures are concentrated in:
- `tests/test_sse_streaming.py` — 16 failures (completed/failed/pending SSE contract tests).
- `tests/test_extract_and_ingest_pipeline.py` — 7 failures.
- `tests/test_api_rate_limit_contract.py::test_repeated_authenticated_requests_return_429_with_stable_contract`.

Many SSE/route failures return `503` because the tenant kill switch cannot reach Redis.

#### Layer 2.5 tests (`make test-layer2-5`)

```text
40 failed, 51 passed
```

Almost every route test returns `503 tenant_status_unavailable` from `value_fabric.shared.identity.middleware`. Examples:

```text
FAILED tests/test_signal_routes.py::test_list_signals_returns_created - assert 503 == 201
FAILED tests/test_signal_routes.py::test_create_signal_returns_201 - assert 503 == 201
FAILED tests/test_tenant_isolation.py::test_tenant_a_cannot_read_tenant_b_signal - assert 503 == 404
```

#### Layer 3 tests (`make test-layer3`)

```text
799 passed, 3 skipped
```

#### Layer 4 tests (`make test-layer4`)

```text
2165 passed, 15 skipped
```

#### Layer 5 tests (`make test-layer5`)

```text
117 failed, 393 passed, 14 skipped
```

Failures are dominated by the Redis kill switch returning 503:

```text
FAILED tests/test_model_registry.py::TestModelDeployment::test_promote_model - assert 503 == 200
FAILED tests/test_value_claim_routes.py::test_create_value_claim - assert 503 == 201
AssertionError: {"detail":"Tenant status could not be verified. Please retry.","error":"tenant_status_unavailable","tenant_id":"00000000-0000-0000-0000-000000000001"}
```

#### Layer 6 tests (`make test-layer6`)

```text
152 passed, 2 skipped
```

#### Security tests (`pytest tests/security`)

```text
5 passed, 53 deselected
```

#### Frontend lint (`pnpm --dir apps/web run lint`)

```text
Frontend hygiene checks passed.
[any-threshold] OK: 81 matches (threshold < 100).
Legacy API import gate passed.
Compatibility shim registry check passed (12 marked shim lines across 11 files).
```

#### Frontend type check (`pnpm --dir apps/web run typecheck`)

```text
> tsc --noEmit
(exit 0)
```

#### Frontend tests (`pnpm --dir apps/web run test`)

```text
Test Files  4 failed | 169 passed (173)
Tests       6 failed | 1849 passed (1855)
```

Failed tests:

```text
FAIL src/api/client.test.ts > ApiClient > error handling > redirects to /sign-in on 401
FAIL src/lib/web-vitals.test.ts > sessionId > stores the sessionId in sessionStorage
FAIL src/routes/criticalFlows.smoke.test.tsx > prospect setup interaction smoke > submits after minimum context is provided
FAIL src/routes/criticalFlows.smoke.test.tsx > workflow intelligence route smoke > keeps launch CTA disabled when prompt is unsafe or empty
FAIL src/components/layout/landmarks.test.tsx > layout landmarks > renders a single primary navigation landmark for desktop sidebar
FAIL src/components/layout/landmarks.test.tsx > layout landmarks > resolves tenant-scoped sidebar links from the provided tenant slug
```

The smoke-test failures are accompanied by `Error: No QueryClient set` and `Error: useAuthContext must be used within an AuthProvider`, suggesting a missing provider wrapper in those specific tests.

#### `make verify`

Failed at the first type-check step:

```text
make[1]: *** [Makefile:311: typecheck-layer1] Error 1
make: *** [Makefile:353: typecheck] Error 2
```

#### `make contract-tests`

```text
INTERNALERROR> SystemExit:
Mandatory test dependencies are missing.
  ✗ pymupdf4llm
  ✗ pytesseract
Install all mandatory deps for the full mandatory profile:
  pip install -r tests/requirements-test.txt
```

#### `make check-pytest-skip-governance`

```text
total skipped entries: 3
category counts: {"allowlisted": 2, "code_health": 0, "infrastructure": 1, "unclassified": 0}
- [allowed]/infrastructure x1 :: 101: PostgreSQL not reachable; start DB to run billing contract tests
- [allowlisted]/allowlisted x1 :: 11: value_fabric.layer3 service stack not available
- [allowlisted]/allowlisted x1 :: 16: value_fabric.layer3 service stack not available
pytest collection exited non-zero (2)
```

---

## 4. Prioritized Improvement Plan

### P0 — Correctness, security, or validation-gate blockers

#### P0.1 Fix Layer 1 type-check errors

- **Problem:** `make typecheck-layer1` fails with 11 errors, blocking `make verify`.
- **Evidence:** `resolving_connector.py` uses `object` for `db`, `coordinator`, `run`, and `step`; `connector_resolution.py` passes a `str` for `custody_mode` where `CustodyMode` is expected.
- **Risk:** Type checker cannot verify runtime correctness; passing wrong types can cause `AttributeError` at runtime.
- **Smallest safe fix:**
  1. Replace `object` annotations in `resolving_connector.py:76-82` with concrete types (`Session`, `PipelineCoordinator`, `SourceIngestionRun`, `IngestionRunStep`).
  2. In `connector_resolution.py`, ensure `custody_mode` is a `CustodyMode` enum instance before passing it into `ConnectorResolution` (coerce from string if needed or fix the upstream caller).
- **Affected files:**
  - `services/layer1-ingestion/src/layer1_ingestion/orchestrator/stage_handlers/resolving_connector.py`
  - `services/layer1-ingestion/src/layer1_ingestion/orchestrator/connector_resolution.py`
- **Required tests:** Existing tests already cover these paths; after the fix, `make typecheck-layer1` and `make test-layer1` must pass.
- **Compatibility implications:** No API or data-format changes if only annotations/internal coercion are corrected.
- **Verification:** `make typecheck-layer1 && make test-layer1`

#### P0.2 Fix Layer 1 unit-test failures

- **Problem:** Three Layer 1 unit tests fail for non-environment reasons.
- **Evidence:**
  - `test_resolve_connector_for_audio_requires_storage_ref` and `test_resolve_connector_for_meeting_requires_storage_ref` — expected exception not raised.
  - `TestNoopStageHandler::test_handler_reaches_ready` — `UUID is not JSON serializable` while persisting `ingestion_run_steps.input_artifact_ids`.
- **Risk:** Either the connector-resolution validation is silently wrong or the tests are out of sync with the implementation; the JSON serialization error can corrupt persisted step artifacts.
- **Smallest safe fix:**
  - For audio/meeting: confirm the test fixture sets `source_type` correctly and that `_pick_storage_ref` returns `None` as expected; restore the guard that raises `ConnectorResolutionError`.
  - For UUID serialization: ensure `ConnectorResolution.to_artifact()` returns JSON-serializable values (e.g., `str(uuid)` instead of `UUID` objects) or add a JSON encoder for the step model.
- **Affected files:**
  - `services/layer1-ingestion/src/layer1_ingestion/orchestrator/connector_resolution.py`
  - `services/layer1-ingestion/src/layer1_ingestion/orchestrator/stage_handlers/noop.py` (or artifact model)
- **Required tests:** The failing tests themselves; add a regression test for UUID serialization if none exists.
- **Compatibility implications:** Changing artifact serialization may affect downstream readers if they expect `UUID` objects; prefer string conversion for persisted JSON.
- **Verification:** `make test-layer1`

#### P0.3 Make tenant governance tests pass without a live Redis

- **Problem:** Layers 2, 2.5, and 5 return hundreds of `503 tenant_status_unavailable` failures because Redis is unavailable in this environment.
- **Evidence:** 28 + 40 + 117 failures, all returning `"error":"tenant_status_unavailable"`.
- **Risk:** The validation gate is effectively unusable without Docker/Redis; developers cannot get fast feedback, and CI becomes flaky if the Redis fixture is not guaranteed.
- **Smallest safe fix:** Provide a test-scoped override/fixture for the kill-switch middleware that:
  1. Mocks the Redis client to a known state, or
  2. Short-circuits tenant status checks for the test tenant in test mode.
  Do not change production middleware behavior.
- **Affected files:**
  - `packages/shared/src/value_fabric/shared/identity/middleware.py`
  - Shared test fixtures (e.g., `conftest.py` files in affected layers)
- **Required tests:** Existing route tests; add a dedicated test that kill switch fails closed when Redis is down.
- **Compatibility implications:** Production behavior unchanged; only test harness changes.
- **Verification:** `make test-layer2 && make test-layer2-5 && make test-layer5`

### P1 — Architectural problems that materially increase change risk

#### P1.1 Fix the six failing frontend tests

- **Problem:** Frontend test suite is not green (`4 failed test files, 6 failed tests`).
- **Evidence:**
  - `src/api/client.test.ts` — 401 redirect assertion fails.
  - `src/lib/web-vitals.test.ts` — `sessionStorage` returns `null`.
  - `src/routes/criticalFlows.smoke.test.tsx` — missing `QueryClientProvider` / `AuthProvider`.
  - `src/components/layout/landmarks.test.tsx` — same missing-provider error.
- **Risk:** These tests guard critical UX paths (auth redirect, session tracking, prospect setup, navigation landmarks). Regressions here directly affect users.
- **Smallest safe fix:** Wrap smoke/landmark tests in the appropriate providers; fix the API-client redirect assertion and the sessionStorage mock/setup.
- **Affected files:**
  - `apps/web/src/api/client.test.ts`
  - `apps/web/src/lib/web-vitals.test.ts`
  - `apps/web/src/routes/criticalFlows.smoke.test.tsx`
  - `apps/web/src/components/layout/landmarks.test.tsx`
- **Required tests:** The failing tests themselves.
- **Compatibility implications:** Test-only changes, no production contract changes.
- **Verification:** `pnpm --dir apps/web run test`

#### P1.2 Restore `make contract-tests`

- **Problem:** The contract test runner cannot start because `pymupdf4llm` and `pytesseract` are missing.
- **Evidence:** `INTERNALERROR> Mandatory test dependencies are missing.`
- **Risk:** Contract drift detection is offline; OpenAPI/schema drift can reach `main`.
- **Smallest safe fix:** Install missing dependencies from `tests/requirements-test.txt` (or update the environment setup script).
- **Affected files:** `tests/requirements-test.txt`, setup documentation.
- **Required tests:** `make contract-tests` itself.
- **Compatibility implications:** None.
- **Verification:** `make contract-tests`

#### P1.3 Resolve `make check-pytest-skip-governance` collection error

- **Problem:** Skip-governance check reports `pytest collection exited non-zero (2)`.
- **Evidence:** 3 allowlisted/infrastructure skips counted, but collection still fails.
- **Risk:** Skip governance gate cannot reliably distinguish acceptable skips from hidden failures.
- **Smallest safe fix:** Investigate the collection failure (likely the same missing deps as `contract-tests` or a Layer 2 import issue) and fix it independently.
- **Affected files:** `tests/support/root_pytest_policy.py`, relevant `conftest.py`.
- **Required tests:** `make check-pytest-skip-governance`.
- **Verification:** `make check-pytest-skip-governance`

### P2 — Maintainability, testing, performance, and developer-experience improvements

#### P2.1 Harden Layer 2 SSE streaming tests

- **Problem:** 16 SSE streaming tests fail.
- **Evidence:** `tests/test_sse_streaming.py` failures include completed/failed/pending event contract tests and header checks.
- **Risk:** Streaming contract for job progress may be silently broken.
- **Smallest safe fix:** After P0.3 (Redis fixture), re-run and fix any remaining SSE logic issues (event formatting, headers, progress reporting).
- **Affected files:** `services/layer2-extraction/src/layer2_extraction/api/routes/sse.py` and related tests.
- **Verification:** `make test-layer2`

#### P2.2 Harden Layer 2 extract/ingest pipeline tests

- **Problem:** 7 pipeline tests fail (`test_extract_and_ingest_pipeline.py`).
- **Evidence:** Retry, cross-layer status flow, and queue persistence tests fail.
- **Risk:** Cross-layer retry and idempotency logic may have drifted.
- **Smallest safe fix:** Re-run after P0.3; characterize whether failures are queue/Redis-related or real contract drift.
- **Affected files:** Pipeline route handlers and Celery task code in `services/layer2-extraction/`.
- **Verification:** `make test-layer2`

#### P2.3 Expand security test coverage

- **Problem:** Only 5 security tests ran; 53 were deselected.
- **Evidence:** `pytest tests/security` → `5 passed, 53 deselected`.
- **Risk:** Tenant isolation and OWASP regressions may not be caught.
- **Smallest safe fix:** Review deselection criteria and run the full security profile in CI, or split mandatory security tests from optional ones.
- **Affected files:** `tests/security/`, `pytest.ini` markers.
- **Verification:** `pytest tests/security` with all relevant markers enabled.

#### P2.4 Replace deprecated FastAPI `on_event` with lifespan handlers

- **Problem:** Deprecation warning: `on_event is deprecated, use lifespan event handlers instead.`
- **Evidence:** `packages/shared/src/value_fabric/shared/fastapi_framework/middleware.py:114`.
- **Risk:** Future FastAPI upgrade will break startup hooks.
- **Smallest safe fix:** Migrate to `asynccontextmanager` lifespan handlers while preserving existing startup behavior.
- **Affected files:** `packages/shared/src/value_fabric/shared/fastapi_framework/middleware.py`.
- **Verification:** `make typecheck` and per-layer tests.

### P3 — Minor consistency and cleanup items

#### P3.1 Address pnpm configuration warning

- **Problem:** `pnpm` warns that `pnpm.overrides` and `pnpm.onlyBuiltDependencies` in `package.json` are ignored.
- **Evidence:** Every pnpm command emits the warning.
- **Smallest safe fix:** Move those keys to `pnpm-workspace.yaml` as documented by pnpm.
- **Affected files:** `package.json`, `pnpm-workspace.yaml`.
- **Verification:** Run any pnpm command and confirm warning is gone.

#### P3.2 Document dependency-install requirement for frontend validation

- **Problem:** A clean checkout cannot run frontend tests until `pnpm install` is executed.
- **Smallest safe fix:** Ensure `docs/development/BUILD_SYSTEM.md` and `README.md` explicitly list `pnpm install --frozen-lockfile` before running frontend validation.
- **Verification:** Follow documented steps in a fresh checkout.

---

## 5. Unresolved Risks

1. **Redis dependency in unit tests.** Until P0.3 is resolved, local validation of Layers 2, 2.5, and 5 requires a running Redis instance or a Docker Compose stack, which increases developer friction and CI cost.
2. **Layer 1 connector-resolution / artifact serialization.** P0.1 and P0.2 may reveal deeper contract drift between `ConnectorResolution`, `IngestionRunStep.input_artifact_ids`, and downstream consumers.
3. **Frontend provider topology.** The smoke/landmark test failures suggest some test trees are missing `QueryClientProvider`/`AuthProvider`; there may be other unguarded paths.
4. **Contract-test dependencies not in the default environment.** P1.2 must be completed before OpenAPI drift can be enforced in the local loop.
5. **Production-readiness gate not exercised.** `make production-readiness-gate` could not be run because `make verify` fails earlier.
6. **Limited security test execution.** 53 deselected security tests represent a coverage gap until they are re-enabled and pass.

---

## 6. Method Notes

- No source files were modified for this assessment.
- The only environment change was `pnpm install --frozen-lockfile`, performed because `apps/web/node_modules` existed but was missing `vitest` and `@types/node`.
- Commands were executed on the Linux host in `/home/ubuntu/Fabric_4L` using Python 3.11.15, pnpm 10.18.1, and the repository’s own `Makefile`.
- Failures were classified as *environment-induced* when the error was a `503 tenant_status_unavailable` from the shared kill-switch middleware; these were not treated as logic defects without further evidence.
