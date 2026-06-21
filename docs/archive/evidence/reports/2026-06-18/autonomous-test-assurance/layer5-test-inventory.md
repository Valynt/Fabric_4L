# Layer 5 Test Inventory

Generated: 2026-05-28

## Backend Tests
| Layer | Unit Tests | Integration Tests | Security Tests | E2E Tests |
|-------|-----------|-------------------|----------------|-----------|
| Layer 5 Ground Truth | 13 unit tests | 39 integration tests | 8 security tests | 0 E2E tests |

## Test Categories

### Unit Tests (13 files)
- test_approval_workflow_models.py
- test_assumption_governance_models.py
- test_assumption_governance_new_models.py
- test_benchmark_governance_models.py
- test_formula_governance_models.py
- test_layer5_truth_invariants.py
- test_policy_enforcement.py
- test_policy_governance_models.py
- test_truth_object_tenant_id_required.py
- test_truth_object_validation.py
- test_truth_service.py
- test_truth_service_and_api_tenant_boundaries.py
- test_value_realization_ledger_models.py

### Integration Tests (39 files)
- test_agent_permission_service.py
- test_api.py
- test_api_tenant_propagation.py
- test_approval_state_machine.py
- test_assumption_approval_service.py
- test_assumption_governance_api.py
- test_audit_append_only_guards.py
- test_audit_write_monitor.py
- test_compat_app_surface_contract.py
- test_config_layer3_defaults.py
- test_cross_tenant_hostile.py
- test_database_optional_tenant_security.py
- test_db_pool_metrics.py
- test_endpoint_response_shape_snapshots.py
- test_error_contract_adapter.py
- test_freshness_monitor.py
- test_freshness_monitor_concurrency.py
- test_governance_alerts.py
- test_governance_api_contract.py
- test_governance_api_security.py
- test_governance_lifecycle_matrix.py
- test_layer3_failure_modes.py
- test_migration_schema_alignment.py
- test_migration_validation.py
- test_model_registry.py
- test_observability_schema.py
- test_production_fail_closed_i02.py
- test_readiness.py
- test_route_scope_authorization.py
- test_router_db_dependencies.py
- test_security_fixes.py
- test_startup_environment_gating.py
- test_state_machine.py
- test_structured_logging_smoke.py
- test_tenant_id_consistency.py
- test_transition_concurrency.py

### Security Tests (8 files)
- test_cross_tenant_hostile.py
- test_database_optional_tenant_security.py
- test_governance_api_security.py
- test_layer3_failure_modes.py
- test_production_fail_closed_i02.py
- test_route_scope_authorization.py
- test_security_fixes.py
- test_truth_service_and_api_tenant_boundaries.py

## Key Invariants Discovered

### Tenant Isolation
- **Rule**: No cross-tenant reads or writes in truth objects or governance entities
- **Enforcement**: RLS policies, tenant-scoped database sessions
- **Code Path**: `src/database.py`, `src/api/tenant_context.py`

### Authentication
- **Rule**: No unauthenticated access to protected resources
- **Enforcement**: JWT authentication, service auth, Fabric auth envelope
- **Code Path**: `src/api/auth.py`, `src/api/main.py`

### Authorization
- **Rule**: No authorization bypass via headers, params, body fields
- **Enforcement**: Role-based access, route scope authorization
- **Code Path**: `src/api/governance_router.py`

### Input Validation
- **Rule**: No unvalidated input reaching truth object persistence
- **Enforcement**: Pydantic schemas, truth object validation
- **Code Path**: `src/api/schemas.py`, validation modules

### Audit Immutability
- **Rule**: Audit events must be append-only and immutable
- **Enforcement**: Append-only guards, immutability constraints
- **Code Path**: `src/observability/`, audit modules

### Approval Workflow
- **Rule**: Approval state transitions must follow defined governance matrix
- **Enforcement**: State machine, approval workflow models
- **Code Path**: `src/services/approval_state_machine.py`

## Test Markers
- `@pytest.mark.unit` - Unit test marker
- `@pytest.mark.asyncio` - Async test functions

## Discovery Notes
- Layer 5 has moderate test coverage (52 total tests)
- Security test coverage present (8 security tests)
- Good coverage of tenant isolation in truth objects
- Production fail-closed tests present
- Governance API security tests
- Approval workflow state machine tests
- Audit append-only guard tests
