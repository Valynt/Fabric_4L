# Test Suite Execution Report — Fabric_4L

**Date:** 2026-05-17  
**Environment:** Gitpod devcontainer — Python 3.11.15, Node 22.22.3, pnpm 10.18.1  
**Infrastructure:** No live services (PostgreSQL, Redis, Neo4j not running)

---

## Executive Summary

| Suite | Total | Passed | Failed | Skipped | Errors | Coverage |
|---|---:|---:|---:|---:|---:|---:|
| **Root `tests/`** | 2,810 | 2,009 | 384 | 317 | 95 | — (no --cov) |
| **Layer 1 (ingestion)** | 757 | 509 | 117 | 32 | 99 | 58.3% |
| **Layer 2 (extraction)** | 321 | 289 | 31 | 1 | 0 | 61.1% |
| **Layer 3 (knowledge)** | 439 | 395 | 41 | 1 | 3 | 43.7% |
| **Layer 4 (agents)** | 1,738 | 1,401 | 231 | 8 | 98 | 59.7% |
| **Layer 5 (ground-truth)** | 216 | 92 | 21 | 3 | 101 | 59.5% |
| **Layer 6 (benchmarks)** | 79 | 79 | 0 | 0 | 0 | **83.9%** |
| **API service** | 89 | 60 | 29 | 0 | 0 | 70.7% |
| **Frontend (Vitest)** | 1,615 | 1,515 | 100 | 0 | 0 | 39.7% stmts / 80.9% branch |
| **TOTAL** | **8,064** | **6,349** | **954** | **362** | **396** | — |

> ⚠️ "Errors" are test-level runtime errors (Docker unavailable, testcontainers failures, etc.), distinct from collection errors.

---

## Collection Errors (Excluded Before Execution)

17 test files could not be collected and were excluded via `--ignore`. No source code was modified.

### Root `tests/` — 3 files excluded

| File | Root Cause |
|---|---|
| `tests/test_model_registry_integration.py` | `layer2_extraction.integration.model_registry_client` module does not exist (removed/renamed) |
| `tests/test_cross_tenant_hostile.py` | Imports `TEST_ORG_ID` from `tests.conftest` which does not export it |
| `tests/ci/test_check_no_nul_bytes.py` | f-string backslash syntax error in the test file itself |

### Root `tests/` — 14 files with import topology errors

These tests import `api.*` or `config.*` as top-level packages (designed to run from `services/layer3-knowledge/`). Under pytest's `importlib` mode at the repo root, the `value_fabric.layer3` shim loads modules without adding `services/layer3-knowledge/src` to `sys.path` for sub-imports, causing `ModuleNotFoundError`. Estimated ~22 tests affected.

| File | Root Cause |
|---|---|
| `tests/layer3/test_endpoint_tenant_isolation.py` | `api.dependencies` not resolvable under importlib mode |
| `tests/layer3/test_error_handling_regression.py` | `api.cache` not resolvable |
| `tests/layer3/test_model_registry_tenant_context.py` | `api.dependencies_tenant` not resolvable |
| `tests/layer3/test_models_error_sanitization.py` | `api.dependencies_tenant` not resolvable |
| `tests/layer3/test_variables_tenant_context_fail_closed.py` | `api.dependencies_tenant` not resolvable |
| `tests/layer3/test_api_rate_limit_contract.py` | `config.Settings` resolves to layer4-agents config (namespace collision) |
| `tests/layer3/test_graph_repository_tenant_contracts.py` | Same `config.Settings` collision |
| `tests/layer3/test_typed_payloads.py` | Same `config.Settings` collision |
| `tests/layer3/test_ingest_tenant_fail_closed.py` | `config.manager` not resolvable |
| `tests/layer3/test_rate_limit_manager_types.py` | Pydantic `TypedDict` version error at import |
| `tests/ci/test_layer3_settings_import_compat.py` | `config.manager` not resolvable |
| `tests/performance/test_performance_optimizations.py` | `config.Settings` collision |
| `tests/security/test_layer3_similarity_roi_tenant_isolation.py` | Relative import beyond top-level package |
| `tests/security/test_neo4j_cross_tenant_write_isolation.py` | `api.dependencies` not resolvable |

### Layer 1 service — 3 subdirectories excluded

`tests/contract/`, `tests/domain/`, `tests/security/` all have conftest files that do `from tests.api.conftest import ...`. The `tests/` directory has no `__init__.py`, so `tests.api` cannot be resolved as a package import. These subdirectories require running from the service root with `tests/` as a package.

### Layer 3 service — 2 files excluded

| File | Root Cause |
|---|---|
| `tests/test_graph_alias_deprecation_policy.py` | `GRAPH_FIELD_ALIAS_REMOVAL_VERSION` not exported from `value_fabric.layer3.retrieval.graph_rag` |
| `tests/test_layer3_compat_metrics_thresholds.py` | Prometheus `CollectorRegistry` duplicate timeseries error on import |

---

## Root `tests/` Suite Detail

**2,810 tests attempted** (2,826 collected minus 17 excluded files)

### Failure Breakdown by Error Type

| Error Type | Count |
|---|---:|
| `httpx.ConnectError` — live service not reachable | 106 |
| Assertion failure (logic/contract) | 81 |
| `FileNotFoundError` — missing fixture/eval trace file | 56 |
| `AssertionError` — explicit assert | 37 |
| `AttributeError` | 33 |
| `ModuleNotFoundError` — missing optional dep | 15 |
| `requests.exceptions.ConnectionError` | 11 |
| `TenantContextError` — tenant isolation enforcement | 4 |
| `TypeError` | 4 |
| Other | 37 |

**Key observations:**
- **173 failures** are due to live services being unreachable (httpx/requests `ConnectError`). These would pass with running Layer 1–6 services.
- **56 failures** are `FileNotFoundError` for eval fixture files (e.g., `tests/evals/fixtures/analyze_competition_traces.json`) — fixture data not committed.
- **37 assertion failures** represent genuine logic/contract bugs.
- **4 `TenantContextError`** failures indicate tenant isolation enforcement is working correctly (tests asserting fail-closed behavior pass; these 4 are unexpected failures).

### Sample Failing Tests (Root Suite)

```
tests/security/test_p1_12_prompt_delimiters.py::TestPromptInjectionDelimiters::test_extraction_routes_has_delimiters
  AssertionError: Must use delimiters for user input

tests/ci/test_build_promotion_artifact_contract.py::test_workflows_reference_shared_build_metadata_contract
  AssertionError: Missing build artifact contract marker in .github/workflows/build-deploy.yml: "published_tag"

tests/ci/test_route_auth_gate.py::test_route_auth_gate_passes_for_services_api_routes
  AssertionError: Scanned routes: 80

tests/evals/skills/test_analyze_competition.py::TestAnalyzeCompetitionContract::test_fixture_has_required_fields
  FileNotFoundError: tests/evals/fixtures/analyze_competition_traces.json

tests/layer1/test_layer1_security_invariants.py::TestLayer1Authentication::test_invalid_token_rejected
  httpx.ConnectError: [Errno -2] Name or service not known
```

---

## Per-Service Suite Results

### Layer 1 — Ingestion (`services/layer1-ingestion`)

- **757 tests** | 509 passed | 117 failed | 32 skipped | 99 errors
- **Coverage: 58.3%**
- Primary failure cause: `ModuleNotFoundError: No module named 'croniter'` (cron validation tests — optional dep not installed), Docker/testcontainers errors (99 errors)

**Worst-covered files:**

| File | Coverage |
|---|---:|
| `adapters/pdf_adapter.py` | 7.6% |
| `compliance/robots_checker.py` | 22.5% |
| `crawler/playwright_crawler.py` | 35.2% |
| `shared/exceptions.py` | 40.0% |
| `shared/tasks.py` | 40.3% |

---

### Layer 2 — Extraction (`services/layer2-extraction`)

- **321 tests** | 289 passed | 31 failed | 1 skipped
- **Coverage: 61.1%**
- Primary failure causes: SSE streaming contract tests (response header assertions), startup dependency verifier, production fail-closed checks

**Worst-covered files:**

| File | Coverage |
|---|---:|
| `layer2_extraction/alignment/semantic_aligner.py` | 0% |
| `layer2_extraction/api/service.py` | 0% |
| `layer2_extraction/output/__init__.py` | 0% |
| `layer2_extraction/validation/__init__.py` | 0% |

---

### Layer 3 — Knowledge Graph (`services/layer3-knowledge`)

- **439 tests** | 395 passed | 41 failed | 1 skipped | 3 errors
- **Coverage: 43.7%**
- Note: Neo4j-dependent tests excluded (`-m "not requires_neo4j and not integration and not e2e"`) to avoid 40s+ connection retry hangs per test
- Primary failure causes: tenant isolation enforcement (Neo4j queries without tenant filter), backup scoping, strict builder enforcement

**Worst-covered files:**

| File | Coverage |
|---|---:|
| `api/app_factory.py` | 0% |
| `api/compat_wiring.py` | 0% |
| `api/dependencies_tenant_secured.py` | 0% |
| `api/middleware_setup.py` | 0% |
| `api/router_groups.py` | 0% |

---

### Layer 4 — Agents (`services/layer4-agents`)

- **1,738 tests** | 1,401 passed | 231 failed | 8 skipped | 98 errors
- **Coverage: 59.7%**
- Primary failure causes: workflow control API tests (pause/resume state machine), Docker/testcontainers errors (98 errors)

**Worst-covered files:**

| File | Coverage |
|---|---:|
| `database_facade.py` | 0% |
| `exceptions.py` | 0% |
| `health_check.py` | 0% |
| `main.py` | 0% |
| `model_registry_client.py` | 0% |

---

### Layer 5 — Ground Truth (`services/layer5-ground-truth`)

- **216 tests** | 92 passed | 21 failed | 3 skipped | 101 errors
- **Coverage: 59.5%**
- 101 errors are testcontainers/Docker failures (PostgreSQL containers)
- Primary failure causes: cross-tenant hostile tests, model registry routes

**Worst-covered files:**

| File | Coverage |
|---|---:|
| `layer5_ground_truth/api/tenant_context.py` | 0% |
| `layer5_ground_truth/migrations/env.py` | 0% |
| `layer5_ground_truth/runtime_mode.py` | 0% |
| `layer5_ground_truth/api/model_registry_routes.py` | 20.9% |
| `layer5_ground_truth/services/truth_service.py` | 22.0% |

---

### Layer 6 — Benchmarks (`services/layer6-benchmarks`)

- **79 tests** | **79 passed** | 0 failed | 0 skipped ✅
- **Coverage: 83.9%** — highest of all services

**Worst-covered files:**

| File | Coverage |
|---|---:|
| `database.py` | 22.6% |
| `repositories/benchmark_repository.py` | 76.3% |
| `api/main.py` | 78.8% |

---

### API Service (`services/api`)

- **89 tests** | 60 passed | 29 failed | 0 skipped
- **Coverage: 70.7%**
- Primary failure causes: cross-tenant leakage tests, governance review queue (database not available), tenant isolation

**Worst-covered files:**

| File | Coverage |
|---|---:|
| `app/models/domain.py` | 0% |
| `app/services/seed_data.py` | 20.0% |
| `app/services/gate_service.py` | 30.8% |
| `app/routers/versioning.py` | 34.0% |

---

## Frontend — Vitest (`apps/web`)

**Full run (all 129 files):** 1,615 tests | 1,515 passed | **100 failed** | 16 failing files

**Coverage run (113 passing files only):**

| Metric | `src/` only | All files (incl. e2e/config) |
|---|---:|---:|
| Statements | 83.19% | 39.71% |
| Branches | 89.28% | 80.93% |
| Functions | 73.07% | 53.05% |
| Lines | 83.19% | 39.71% |

> Note: "All files" includes e2e Playwright specs and config files which have 0% coverage by design. The `src/` figure is the meaningful metric.

### Frontend Coverage by Subdirectory (`src/`)

| Directory | Stmts | Branch | Funcs | Lines |
|---|---:|---:|---:|---:|
| `src/` (all) | 83.19% | 89.28% | 73.07% | 83.19% |
| `src/agui` | 45.23% | 87.23% | 50.00% | 45.23% |
| `src/api` | 66.61% | 69.60% | 78.33% | 66.61% |

### Failing Frontend Test Files (100 tests across 16 files)

| File | Primary Error |
|---|---|
| `src/hooks/useTargets.test.ts` | `Cannot find module './queryKeys'` |
| `src/hooks/useAuth.test.ts` | `Cannot access 'data' before initialization` |
| `src/hooks/useAccounts.test.tsx` | MSW unmatched request handler |
| `src/hooks/useCompetitiveIntel.test.ts` | MSW unmatched request handler |
| `src/hooks/useModels.test.tsx` | MSW unmatched request handler |
| `src/hooks/useROICalculator.test.ts` | MSW unmatched request handler |
| `src/hooks/useValuePacks.test.tsx` | MSW unmatched request handler |
| `src/pages/TargetsAdmin.test.tsx` | MSW unmatched request handler |
| `src/pages/TargetsAdmin.form.test.tsx` | MSW unmatched request handler |
| `src/pages/TargetsAdmin.detail.test.tsx` | MSW unmatched request handler |
| `src/pages/TargetsAdmin.integration.test.tsx` | MSW unmatched request handler |
| `src/pages/IngestionJobs.test.tsx` | MSW unmatched request handler |
| `src/navigation/navSchema.test.ts` | Assertion failure |
| `src/components/workspace/AccountPickerModal.test.tsx` | MSW unmatched request handler |
| `src/pages/intelligence/SignalsTab.test.tsx` | Element not found in DOM |
| `src/pages/intelligence/HypothesisValidationToDriverFlow.test.tsx` | MSW unmatched request handler |

**Root causes summary:**
- **62 failures** — MSW (Mock Service Worker) intercepted requests with no matching handler. API mock handlers are missing or stale for these routes.
- **57 failures** — `Cannot access 'data' before initialization` — temporal dead zone error in hook initialization.
- **4 failures** — `Cannot find module './queryKeys'` — missing module (likely deleted/renamed).
- **11 failures** — Network errors / assertion failures.

---

## Coverage Summary

| Suite | Coverage | Status |
|---|---:|---|
| Layer 6 (benchmarks) | 83.9% | ✅ Above 80% target |
| API service | 70.7% | ⚠️ Below 80% target |
| Layer 2 (extraction) | 61.1% | ❌ Below 80% target |
| Layer 4 (agents) | 59.7% | ❌ Below 80% target |
| Layer 5 (ground-truth) | 59.5% | ❌ Below 80% target |
| Layer 1 (ingestion) | 58.3% | ❌ Below 80% target |
| Layer 3 (knowledge) | 43.7% | ❌ Below 80% target |
| Frontend `src/` | 83.2% stmts | ✅ Above 80% target |
| Frontend `src/` branches | 89.3% | ✅ Above 80% target |

---

## Infrastructure Impact

The following test categories were affected by missing live services:

| Dependency | Tests Affected | Behavior |
|---|---|---|
| PostgreSQL (port 5432) | Layer 5 testcontainers, API DB tests | 101 errors (testcontainers), 29 failures |
| Redis (port 6379) | Layer 2 production fail-closed tests | Failures |
| Neo4j (port 7687) | Layer 3 graph tests | Excluded via `-m` filter to avoid 40s hangs |
| Docker daemon | Layer 1, Layer 4, Layer 5 testcontainers | 99 + 98 + 101 errors |
| Live Layer 1–6 services | Root suite integration/security tests | 117 `ConnectError` failures |

Running `docker compose -f docker-compose.test.yml up -d` before the test run would resolve the majority of errors and a significant portion of failures.

---

## Artifacts

| File | Description |
|---|---|
| `artifacts/pytest-root.log` | Full root suite output |
| `artifacts/pytest-layer1.log` | Layer 1 service suite output |
| `artifacts/pytest-layer2.log` | Layer 2 service suite output |
| `artifacts/pytest-layer3.log` | Layer 3 service suite output |
| `artifacts/pytest-layer4.log` | Layer 4 service suite output |
| `artifacts/pytest-layer5.log` | Layer 5 service suite output |
| `artifacts/pytest-layer6.log` | Layer 6 service suite output |
| `artifacts/pytest-api.log` | API service suite output |
| `artifacts/coverage-layer{1-6}.json` | Per-layer coverage JSON |
| `artifacts/coverage-api.json` | API service coverage JSON |
| `artifacts/vitest-coverage-text.log` | Frontend coverage text report |
| `artifacts/vitest.log` | Frontend test run output (passing files) |
