---
id: L6-TEST-DEBT
type: task
title: "Fix remaining Layer 6 API/repository/OpenAPI test failures"
status: open
parent: (none)
assignee: (unassigned)
---

## Description

After Layer 6 test hardening (53 new tests added and passing), 19 pre-existing test failures remain in the Layer 6 benchmark service. These failures were present before the new tests were added and are unrelated to this PR. They are tracked here so the test-hardening PR can close without scope creep.

## Remaining Failures (19)

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

## Why These Are Unrelated to the Test-Hardening PR

- All 19 failures existed before the 53 new tests were introduced.
- None of the new tests touch API response codes, OpenAPI contract file paths, repository query-string assertions, or tenant-isolation logic.
- Fixing them requires separate investigation into Layer 6 service behavior, contract drift, and repository query construction—not test infrastructure changes.

## Acceptance Criteria

- [ ] All 19 pre-existing failures above are investigated and fixed, or ticketed with narrower scope
- [ ] `python -m pytest` in `services/layer6-benchmarks` passes with zero failures
- [ ] No regressions introduced in the 53 new hardened tests

## Recommended Next Steps

1. Run the full Layer 6 test suite and inspect the exact error output for each failing test.
2. Tackle categories in this order: API response codes (likely fast), OpenAPI contract file paths (may need spec file relocation), query-string assertions (Cypher/query construction drift), tenant isolation (may involve service-level auth fixes).
3. For each fix, run the targeted 53-test validation command to confirm no regression:
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

## Dependencies

- Layer 6 test hardening PR (completed)

## Notes

- [2026-05-28] coder: Ticket created post-Layer-6 test hardening acceptance. These 19 failures span API contract drift, OpenAPI spec path issues, repository query-string assertions, and tenant-isolation logic.
