---
id: L6-TEST-DEBT
type: task
title: "Fix remaining Layer 6 API/repository/OpenAPI test failures"
status: complete
parent: (none)
assignee: (unassigned)
---

## Description

Layer 6 facade-removal prerequisites are now complete enough that this ticket should track only the remaining Layer 6 test-debt work. The ticket stays **open** because the full Layer 6 test suite still needs dependency-backed verification and any remaining API/repository/OpenAPI failures need to be fixed or split into narrower tickets.

## Completion Note

- **2026-06-07:** Baseline refreshed and all historical failures resolved. `cd services/layer6-benchmarks && python -m pytest -q` passes with **150 passed, 2 skipped, 0 failures**. Hardened-test validation passes with **62 passed, 0 failures**.

## Current Phase 2 Breakdown

### Phase 2A — Facade-removal prerequisites (completed)

- [x] Layer 6 source is nested under the canonical `layer6_benchmarks` package.
- [x] Layer 6 tests use canonical `layer6_benchmarks.*` imports and patch targets.
- [x] `value_fabric/layer6/__init__.py` is neutralized and retained only as an empty namespace placeholder.
- [x] The remaining `value_fabric/layer6/test_structured_logging_smoke.py` smoke import points at `layer6_benchmarks.logging_config`.
- [x] Facade import allowlist no longer carries broad Layer 6 runtime/test migration debt.

### Phase 2B — Dependency-backed Layer 6 test baseline (complete)

- [x] Re-run `python -m pytest -q` from `services/layer6-benchmarks` in an environment with the service dependencies installed.
- [x] Replace the historical 19-failure baseline below with the current collected failure list. **Result: 150 passed, 2 skipped, 0 failures.**
- [x] Confirm canonical imports continue to work without the neutralized shim providing path bootstrapping.

### Phase 2C — API readiness/health contract drift (complete)

- [x] Verify readiness endpoints return the expected degraded/503 contract when configuration validation or startup state fails.
- [x] Verify health/ready/metrics response contracts match the current Layer 6 API surface.

### Phase 2D — OpenAPI contract availability and shape drift (complete)

- [x] Confirm the Layer 6 OpenAPI contract file exists at the path expected by route-matrix tests.
- [x] Confirm benchmark route response shapes match the committed OpenAPI contract.

### Phase 2E — Repository query and tenant-isolation behavior (complete)

- [x] Update or fix repository query-string assertions so tenant predicates are explicit and stable.
- [x] Confirm tenant users cannot mutate global benchmark records.
- [x] Confirm super-admin/global-benchmark behavior is intentional and contract-aligned.

### Phase 2F — Route matrix, statistical edge cases, and error adapter drift (complete)

- [x] Verify happy/hostile route matrix cases.
- [x] Verify compare/validate lineage and statistical edge cases.
- [x] Verify Layer 6 shared-exception adapter emits the current error contract shape.

## Historical Remaining Failures (19) — RESOLVED

All 19 pre-facade-neutralization baseline failures have been verified as passing in the current dependency-backed environment. The single active fix required was in `test_benchmark_route_matrix_and_contracts.py` (see Fix Log below). All other historically failing tests now pass without code changes.

### Fix Log

**File:** `services/layer6-benchmarks/tests/test_benchmark_route_matrix_and_contracts.py`

1. **Import drift:** `get_request_context` was imported from `value_fabric.shared.identity.context`, but the Layer 6 benchmark routes in `api/routes/benchmarks.py` inject `get_request_context` from `layer6_benchmarks.api.deps`. This meant `app.dependency_overrides[get_request_context]` in the test was a no-op, causing the routes to fall back to the conftest mock governance context (`tenant_id="system"`). This broke tenant-scoped dataset lookups (e.g., `GET /v1/benchmarks/datasets/tenant-a-throughput` returned 404 because the mock repo was queried with `tenant_id="system"`).
   - **Fix:** Changed import to `from layer6_benchmarks.api.deps import get_request_context`.

2. **Status-code expectation drift:** The hostile case for `POST /v1/benchmarks/validate` with `value="bad"` expected 400, but the handler raises `ValidationError` (which the shared exception handler maps to 422 per the canonical error contract).
   - **Fix:** Changed expected status from 400 to 422.

### Follow-up cleanup (complete)

- [x] `test_benchmark_api.py` and `test_benchmark_route_matrix.py` — aligned `get_request_context` imports to `layer6_benchmarks.api.deps`. Verified: 150 passed, 2 skipped, 0 failures.

## Historical Remaining Failures (19) — All passing

These were the pre-facade-neutralization baseline failures and should be refreshed after Phase 2B runs successfully in a dependency-complete environment.

### API response code mismatches (3) — PASSED

- `tests/test_benchmark_api.py::test_ready_returns_503_when_config_validation_fails`
- `tests/test_benchmark_api.py::test_ready_returns_503_with_startup_degraded_state`
- `tests/test_compat_app_surface_contract.py::test_l6_health_ready_metrics_response_contract`

### Missing OpenAPI contract file (2) — PASSED

- `tests/test_benchmark_route_matrix.py::test_openapi_contract_includes_benchmark_routes_and_shapes`
- `tests/test_benchmark_route_matrix_and_contracts.py::test_openapi_contract_shape_regression_for_benchmark_responses`

### Query-string assertion drift (5) — PASSED

- `tests/test_repository_tenant_isolation.py::test_repository_get_dataset_cypher_requires_tenant_id`
- `tests/test_repository_tenant_isolation.py::test_repository_list_datasets_query_always_contains_tenant_predicate[Retail-None]`
- `tests/test_repository_tenant_isolation.py::test_repository_list_datasets_query_always_contains_tenant_predicate[Retail-Enterprise]`
- `tests/test_repository_tenant_isolation.py::test_repository_list_datasets_query_always_contains_tenant_predicate[None-Enterprise]`
- `tests/test_repository_tenant_isolation.py::test_repository_list_datasets_query_always_contains_tenant_predicate[None-None]`

### Repository tenant isolation failures (2) — PASSED

- `tests/test_benchmark_api.py::test_tenant_user_cannot_update_existing_global_benchmark`
- `tests/test_benchmark_api.py::test_super_admin_can_create_global_benchmark`

### Route matrix / edge case failures (7) — PASSED

- `tests/test_benchmark_route_matrix.py::test_route_matrix_happy_and_hostile`
- `tests/test_benchmark_route_matrix.py::test_compare_and_validate_preserve_dataset_lineage_and_stats_edges`
- `tests/test_benchmark_edge_cases.py::TestBenchmarkValidation::test_compare_rejects_invalid_company_value`
- `tests/test_benchmark_route_matrix_and_contracts.py::test_statistical_edge_cases_small_sample_and_percentile_boundaries`
- `tests/test_benchmark_route_matrix_and_contracts.py::test_route_matrix_happy_and_hostile_paths`
- `tests/test_benchmark_route_matrix_and_contracts.py::test_dataset_lineage_preserved_through_list_get_compare_validate`
- `tests/test_error_contract_adapter.py::test_layer6_adapter_maps_shared_exception_to_current_contract_shape`

## Acceptance Criteria

- [x] Phase 2B produces a current dependency-backed Layer 6 test baseline.
- [x] All current L6 failures are investigated and fixed, or ticketed with narrower scope.
- [x] `python -m pytest -q` in `services/layer6-benchmarks` passes with zero failures. **Verified: 150 passed, 2 skipped, 0 failures.**
- [x] No regressions are introduced in the Layer 6 hardened tests. **Verified: 62 passed, 0 failures.**
- [x] Canonical `layer6_benchmarks.*` imports remain the only Layer 6 runtime/test import path after fixes.

## Recommended Next Steps

1. Install or activate the Layer 6 service dependencies, then run the Phase 2B baseline command:
   ```bash
   cd services/layer6-benchmarks
   python -m pytest -q
   ```
2. Refresh the historical failure list above with the actual current output.
3. Tackle remaining work in this order: readiness/health contracts, OpenAPI contract path/shape, repository tenant predicates and authorization, route-matrix/statistical edge cases, then error adapter drift.
4. For each fix, run the targeted hardened-test validation command:
   ```bash
   cd services/layer6-benchmarks
   python -m pytest \
     tests/test_models_benchmark_dataset.py \
     tests/test_api_schemas.py \
     tests/test_observability_metrics_contract.py \
     tests/test_metrics_prometheus.py \
     tests/test_repository_pures.py \
     tests/test_database_driver.py \
     tests/test_startup_logging.py \
     tests/test_metrics_contract.py \
     -q
   ```

## Notes

- [2026-05-28] coder: Ticket created post-Layer-6 test hardening acceptance. The original 19 failures spanned API contract drift, OpenAPI spec path issues, repository query-string assertions, and tenant-isolation logic.
- [2026-05-29] coder: Updated after facade neutralization. Phase 2A facade-removal prerequisites are complete; Phase 2B dependency-backed baseline remains open because the local environment lacks installed Layer 6 dependencies.
- [2026-06-07] coder: Phase 2B–2F complete. Only fix required was import drift (`get_request_context` source module mismatch) and status-code expectation drift (400 → 422) in `test_benchmark_route_matrix_and_contracts.py`. All 19 historical failures verified passing.
- [2026-07-18] cleanup-agent: Ticket remains status=complete. Acceptance criteria all checked. Canonical nested package `services/layer6-benchmarks/src/layer6_benchmarks/` is the only L6 source tree (no residual flat files detected).
