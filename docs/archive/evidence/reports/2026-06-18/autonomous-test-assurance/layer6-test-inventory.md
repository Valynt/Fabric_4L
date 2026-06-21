# Layer 6 Test Inventory

Generated: 2026-05-28

## Backend Tests
| Layer | Unit Tests | Integration Tests | Security Tests | E2E Tests |
|-------|-----------|-------------------|----------------|-----------|
| Layer 6 Benchmarks | 0 unit tests | 16 integration tests | 4 security tests | 0 E2E tests |

## Test Categories

### Integration Tests (16 files)
- test_api_tenant_propagation.py
- test_api_wrapper_startup_regression.py
- test_benchmark_api.py
- test_benchmark_edge_cases.py
- test_benchmark_route_matrix.py
- test_benchmark_route_matrix_and_contracts.py
- test_compat_app_surface_contract.py
- test_cross_tenant_hostile.py
- test_cross_tenant_hostile_behavioral.py
- test_error_contract_adapter.py
- test_metrics_contract.py
- test_repository_tenant_isolation.py
- test_scope_authorization.py
- test_settings_validation.py
- test_startup_logging.py

### Security Tests (4 files)
- test_cross_tenant_hostile.py
- test_cross_tenant_hostile_behavioral.py
- test_repository_tenant_isolation.py
- test_scope_authorization.py

## Key Invariants Discovered

### Tenant Isolation
- **Rule**: No cross-tenant reads or writes in benchmark datasets
- **Enforcement**: Tenant-scoped Neo4j queries, repository-level isolation
- **Code Path**: `src/repositories/benchmark_repository.py`, `src/database.py`

### Authentication
- **Rule**: No unauthenticated access to protected resources
- **Enforcement**: RequestContext, get_request_context
- **Code Path**: `src/api/main.py`, `src/api/deps.py`

### Authorization
- **Rule**: No authorization bypass via headers, params, body fields
- **Enforcement**: authorize_action, policy registry
- **Code Path**: `src/api/main.py`, shared.identity.policy_registry

### Input Validation
- **Rule**: No unvalidated input reaching Neo4j queries or benchmark persistence
- **Enforcement**: Pydantic schemas, settings validation
- **Code Path**: `src/api/schemas.py`, `src/settings.py`

### Scope Authorization
- **Rule**: Benchmark access must respect tenant and ownership scopes
- **Enforcement**: Scope-based authorization checks
- **Code Path**: `src/api/routes/benchmarks.py`

## Test Markers
- `@pytest.mark.asyncio` - Async test functions
- `@pytest.mark.parametrize` - Parameterized tests

## Discovery Notes
- Layer 6 has minimal test coverage (16 total tests, no unit tests)
- Security test coverage present (4 security tests)
- Good coverage of tenant isolation in repository layer
- Cross-tenant hostile tests present
- Scope authorization tests present
- Settings validation tests present
- Metrics contract tests present
