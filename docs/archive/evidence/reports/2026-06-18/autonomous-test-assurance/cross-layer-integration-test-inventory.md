# Cross-Layer Integration Test Inventory

Generated: 2026-05-28

## Cross-Layer Integration Tests
| Category | Tests | Security Tests | Contract Tests | Chaos Tests |
|----------|-------|---------------|---------------|------------|
| Backend Integrated | 11 tests | 2 tests | 2 tests | 1 test |
| Integration | 18 tests | 0 tests | 0 tests | 0 tests |
| Contract | 59 tests | 0 tests | 59 tests | 0 tests |
| Security | 104 tests | 104 tests | 0 tests | 0 tests |
| Chaos | 5 tests | 0 tests | 0 tests | 5 tests |
| Cache | 2 tests | 1 test | 0 tests | 0 tests |
| Architecture | 10 tests | 0 tests | 0 tests | 0 tests |
| CI | 55 tests | 0 tests | 0 tests | 0 tests |

## Test Categories

### Backend Integrated Tests (11 files)
- test_agent_grounding_real_tool_contracts.py
- test_approval_export_crm_governance.py
- test_backend_integrated_golden_path.py
- test_calculation_evidence_provenance_integrity.py
- test_chaos_smoke_validation.py
- test_cross_layer_data_flow_validation.py
- test_cross_tenant_hostile_layers.py
- test_operational_resilience_real_services.py
- test_release_environment_smoke_validation.py
- test_tenant_isolation_security_persistence.py

### Integration Tests (18 files)
- Integration tests across various services and components

### Contract Tests (59 files)
- Contract compliance tests for API endpoints, schemas, and data structures

### Security Tests (104 files)
- Security tests covering authentication, authorization, tenant isolation, and adversarial scenarios

### Chaos Tests (5 files)
- test_database_failure.py
- test_external_dependency_failure.py
- test_llm_failure.py
- test_redis_failure.py
- Chaos engineering tests for resilience validation

### Cache Tests (2 files)
- test_redis_tenant_isolation.py
- Cache-related integration tests

### Architecture Tests (10 files)
- test_async_session_only.py
- test_canonical_module_sentinels.py
- test_clerk_isolation_sentinel.py
- test_layer3_models_shim_contract.py
- test_layer3_runtime_shim_drift.py
- test_no_merge_markers.py
- test_no_non_runtime_imports.py
- test_no_runtime_notimplemented.py
- test_tenant_architecture.py
- test_testability_architecture.py

### CI Tests (55 files)
- CI workflow tests, build promotion tests, compatibility checks

### Root-Level Cross-Layer Tests (5 files)
- test_cross_tenant_hostile.py
- test_l4_l5_concrete_response_contracts.py
- test_model_registry_integration.py
- test_release_evidence_packet.py
- test_tenant_rate_limiting.py

## Key Invariants Discovered

### Cross-Layer Tenant Isolation
- **Rule**: No cross-tenant data leakage across any layer
- **Enforcement**: Cross-tenant hostile tests, tenant isolation security persistence tests
- **Code Path**: `tests/backend_integrated/test_cross_tenant_hostile_layers.py`

### Cross-Layer Data Flow
- **Rule**: Data must flow correctly through all layers with proper validation
- **Enforcement**: Cross-layer data flow validation tests
- **Code Path**: `tests/backend_integrated/test_cross_layer_data_flow_validation.py`

### Evidence Provenance
- **Rule**: Evidence must maintain provenance integrity across layers
- **Enforcement**: Calculation evidence provenance integrity tests
- **Code Path**: `tests/backend_integrated/test_calculation_evidence_provenance_integrity.py`

### Operational Resilience
- **Rule**: System must remain operational under failure conditions
- **Enforcement**: Operational resilience tests, chaos engineering tests
- **Code Path**: `tests/backend_integrated/test_operational_resilience_real_services.py`, `tests/chaos/`

### Release Environment
- **Rule**: Release environments must meet production readiness criteria
- **Enforcement**: Release environment smoke validation tests
- **Code Path**: `tests/backend_integrated/test_release_environment_smoke_validation.py`

### Agent Tool Contracts
- **Rule**: Agent tool execution must respect real tool contracts
- **Enforcement**: Agent grounding real tool contracts tests
- **Code Path**: `tests/backend_integrated/test_agent_grounding_real_tool_contracts.py`

### CRM Governance
- **Rule**: CRM export and approval must follow governance rules
- **Enforcement**: Approval export CRM governance tests
- **Code Path**: `tests/backend_integrated/test_approval_export_crm_governance.py`

## Test Markers
- `@pytest.mark.asyncio` - Async test functions
- `@pytest.mark.parametrize` - Parameterized tests
- `@pytest.mark.backend_integrated` - Backend-integrated tests requiring live services

## Discovery Notes
- Cross-layer integration has comprehensive test coverage (264 total tests)
- Strong security test coverage (106 security tests)
- Good coverage of cross-tenant isolation across layers
- Chaos engineering tests for resilience validation
- Contract tests for API compliance
- Architecture tests for canonical module compliance
- CI tests for build and deployment validation
- Backend-integrated tests require live services
