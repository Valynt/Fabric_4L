---
id: L6-TEST-DEBT
type: task
title: "Fix remaining Layer 6 API/repository/OpenAPI test failures"
status: open
parent: (none)
assignee: (unassigned)
---

## Description

Layer 6 facade-removal prerequisites are now complete enough that this ticket should track only the remaining Layer 6 test-debt work. The ticket stays **open** because the full Layer 6 test suite still needs dependency-backed verification and any remaining API/repository/OpenAPI failures need to be fixed or split into narrower tickets.

## Current Phase 2 Breakdown

### Phase 2A — Facade-removal prerequisites (completed)

- [x] Layer 6 source is nested under the canonical `layer6_benchmarks` package.
- [x] Layer 6 tests use canonical `layer6_benchmarks.*` imports and patch targets.
- [x] `value_fabric/layer6/__init__.py` is neutralized and retained only as an empty namespace placeholder.
- [x] The remaining `value_fabric/layer6/test_structured_logging_smoke.py` smoke import points at `layer6_benchmarks.logging_config`.
- [x] Facade import allowlist no longer carries broad Layer 6 runtime/test migration debt.

### Phase 2B — Dependency-backed Layer 6 test baseline (open)

- [ ] Re-run `python -m pytest -q` from `services/layer6-benchmarks` in an environment with the service dependencies installed.
- [ ] Replace the historical 19-failure baseline below with the current collected failure list.
- [ ] Confirm canonical imports continue to work without the neutralized shim providing path bootstrapping.

### Phase 2C — API readiness/health contract drift (open until verified)

- [ ] Verify readiness endpoints return the expected degraded/503 contract when configuration validation or startup state fails.
- [ ] Verify health/ready/metrics response contracts match the current Layer 6 API surface.

### Phase 2D — OpenAPI contract availability and shape drift (open until verified)

- [ ] Confirm the Layer 6 OpenAPI contract file exists at the path expected by route-matrix tests.
- [ ] Confirm benchmark route response shapes match the committed OpenAPI contract.

### Phase 2E — Repository query and tenant-isolation behavior (open until verified)

- [ ] Update or fix repository query-string assertions so tenant predicates are explicit and stable.
- [ ] Confirm tenant users cannot mutate global benchmark records.
- [ ] Confirm super-admin/global-benchmark behavior is intentional and contract-aligned.

### Phase 2F — Route matrix, statistical edge cases, and error adapter drift (open until verified)

- [ ] Verify happy/hostile route matrix cases.
- [ ] Verify compare/validate lineage and statistical edge cases.
- [ ] Verify Layer 6 shared-exception adapter emits the current error contract shape.

## Historical Remaining Failures (19)

These were the pre-facade-neutralization baseline failures and should be refreshed after Phase 2B runs successfully in a dependency-complete environment.

### API response code mismatches (3)

- `tests/test_benchmark_api.py::test_ready_returns_503_when_config_validation_fails`
- `tests/test_benchmark_api.py::test_ready_returns_503_with_startup_degraded_state`
- `tests/test_compat_app_surface_contract.py::test_l6_health_ready_metrics_response_contract`

### Missing OpenAPI contract file (2)

- `tests/test_benchmark_route_matrix.py::test_openapi_contract_includes_benchmark_routes_and_shapes`
- `tests/test_benchmark_route_matrix_and_contracts.py::test_openapi_contract_shape_regression_for_benchmark_responses`

### Query-string assertion drift (5)

- `tests/test_repository_tenant_isolation.py::test_repository_get_dataset_cypher_requires_tenant_id`
- `tests/test_repository_tenant_isolation.py::test_repository_list_datasets_query_always_contains_tenant_predicate[Retail-None]`
- `tests/test_repository_tenant_isolation.py::test_repository_list_datasets_query_always_contains_tenant_predicate[Retail-Enterprise]`
- `tests/test_repository_tenant_isolation.py::test_repository_list_datasets_query_always_contains_tenant_predicate[None-Enterprise]`
- `tests/test_repository_tenant_isolation.py::test_repository_list_datasets_query_always_contains_tenant_predicate[None-None]`

### Repository tenant isolation failures (2)

- `tests/test_benchmark_api.py::test_tenant_user_cannot_update_existing_global_benchmark`
- `tests/test_benchmark_api.py::test_super_admin_can_create_global_benchmark`

### Route matrix / edge case failures (7)

- `tests/test_benchmark_route_matrix.py::test_route_matrix_happy_and_hostile`
- `tests/test_benchmark_route_matrix.py::test_compare_and_validate_preserve_dataset_lineage_and_stats_edges`
- `tests/test_benchmark_edge_cases.py::TestBenchmarkValidation::test_compare_rejects_invalid_company_value`
- `tests/test_benchmark_route_matrix_and_contracts.py::test_statistical_edge_cases_small_sample_and_percentile_boundaries`
- `tests/test_benchmark_route_matrix_and_contracts.py::test_route_matrix_happy_and_hostile_paths`
- `tests/test_benchmark_route_matrix_and_contracts.py::test_dataset_lineage_preserved_through_list_get_compare_validate`
- `tests/test_error_contract_adapter.py::test_layer6_adapter_maps_shared_exception_to_current_contract_shape`

## Acceptance Criteria

- [ ] Phase 2B produces a current dependency-backed Layer 6 test baseline.
- [ ] All current Layer 6 failures are investigated and fixed, or ticketed with narrower scope.
- [ ] `python -m pytest -q` in `services/layer6-benchmarks` passes with zero failures.
- [ ] No regressions are introduced in the Layer 6 hardened tests.
- [ ] Canonical `layer6_benchmarks.*` imports remain the only Layer 6 runtime/test import path after fixes.

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
