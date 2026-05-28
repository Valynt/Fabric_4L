---
id: L6-TEST-DEBT
type: task
title: "Fix remaining Layer 6 API/repository/OpenAPI test failures"
status: open
parent: (none)
assignee: (unassigned)
---

## Description

After Layer 6 test hardening (53 new tests added and passing), 19 pre-existing test failures remain in the Layer 6 benchmark service. These failures are unrelated to the new test work and are tracked separately here so the test-hardening PR can close without scope creep.

## Remaining Failures (19)

### API response code mismatches
- `tests/test_benchmark_api.py::test_ready_returns_503_when_config_validation_fails`
- `tests/test_benchmark_api.py::test_ready_returns_503_with_startup_degraded_state`
- `tests/test_compat_app_surface_contract.py::test_l6_health_ready_metrics_response_contract`

### Missing OpenAPI contract file
- `tests/test_benchmark_route_matrix.py::test_openapi_contract_includes_benchmark_routes_and_shapes`
- `tests/test_benchmark_route_matrix_and_contracts.py::test_openapi_contract_shape_regression_for_benchmark_responses`

### Query-string assertion drift
- `tests/test_repository_tenant_isolation.py::test_repository_get_dataset_cypher_requires_tenant_id`
- `tests/test_repository_tenant_isolation.py::test_repository_list_datasets_query_always_contains_tenant_predicate[Retail-None]`
- `tests/test_repository_tenant_isolation.py::test_repository_list_datasets_query_always_contains_tenant_predicate[Retail-Enterprise]`
- `tests/test_repository_tenant_isolation.py::test_repository_list_datasets_query_always_contains_tenant_predicate[None-Enterprise]`
- `tests/test_repository_tenant_isolation.py::test_repository_list_datasets_query_always_contains_tenant_predicate[None-None]`

### Repository tenant isolation failures
- `tests/test_benchmark_api.py::test_tenant_user_cannot_update_existing_global_benchmark`
- `tests/test_benchmark_api.py::test_super_admin_can_create_global_benchmark`

### Route matrix / edge case failures
- `tests/test_benchmark_route_matrix.py::test_route_matrix_happy_and_hostile`
- `tests/test_benchmark_route_matrix.py::test_compare_and_validate_preserve_dataset_lineage_and_stats_edges`
- `tests/test_benchmark_edge_cases.py::TestBenchmarkValidation::test_compare_rejects_invalid_company_value`
- `tests/test_benchmark_route_matrix_and_contracts.py::test_statistical_edge_cases_small_sample_and_percentile_boundaries`
- `tests/test_benchmark_route_matrix_and_contracts.py::test_route_matrix_happy_and_hostile_paths`
- `tests/test_benchmark_route_matrix_and_contracts.py::test_dataset_lineage_preserved_through_list_get_compare_validate`
- `tests/test_error_contract_adapter.py::test_layer6_adapter_maps_shared_exception_to_current_contract_shape`

## Acceptance Criteria

- [ ] All 19 pre-existing failures above are investigated and fixed or ticketed with narrower scope
- [ ] `python -m pytest` in `services/layer6-benchmarks` passes with zero failures
- [ ] No regressions introduced in the 53 new hardened tests

## Dependencies

- Layer 6 test hardening PR (completed)

## Notes

- [2026-05-28] coder: Ticket created post-Layer-6 test hardening acceptance. These 19 failures were present before the 53 new tests were added. They span API contract drift, OpenAPI spec path issues, repository query-string assertions, and tenant-isolation logic.
