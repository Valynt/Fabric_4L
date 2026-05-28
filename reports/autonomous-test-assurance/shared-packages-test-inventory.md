# Shared Packages Test Inventory

Generated: 2026-05-28

## Shared Package Tests
| Package | Unit Tests | Integration Tests | Contract Tests | Security Tests |
|---------|-----------|-------------------|---------------|---------------|
| shared | 27 tests | 0 tests | 0 tests | 4 tests |
| platform-contract | 5 tests | 0 tests | 5 tests | 0 tests |
| value_fabric | 1 test | 0 tests | 0 tests | 0 tests |

## Test Categories

### Shared Package Tests (27 files)
- test_audit.py
- test_siem_integration.py
- test_postgresql.py
- test_pr2_lifespan.py
- test_error_handling.py
- test_trace_id_sanitization_regression.py
- test_app.py
- test_pr1_controls.py
- test_idempotency_core.py
- test_auth_mode.py
- test_context.py
- test_dependencies.py
- test_fabric_auth_envelope.py
- test_fabric_auth_middleware.py
- test_hashing.py
- test_jwt.py
- test_permissions.py
- test_policy_registry.py
- test_mcp_handshake.py
- test_tool_discovery.py
- test_auth_security.py
- test_mcp_gateway_unit.py
- test_circuit_breaker.py
- test_watcher.py
- test_production_safety.py
- test_tenant_scoping.py
- test_testability.py

### Platform Contract Tests (5 files)
- test_agent_semantic_contracts.py
- test_context_contract.py
- test_database_contract.py
- test_llm_output_parser.py
- test_tool_boundary_contract.py

### Value Fabric Tests (1 file)
- test_structured_logging_smoke.py

### Security Tests (4 files)
- test_auth_security.py
- test_fabric_auth_envelope.py
- test_fabric_auth_middleware.py
- test_tenant_scoping.py

## Key Invariants Discovered

### Authentication
- **Rule**: Fabric auth envelope must be validated for all requests
- **Enforcement**: Fabric auth middleware, envelope validation
- **Code Path**: `src/value_fabric/shared/identity/`

### Authorization
- **Rule**: Policy registry must enforce role-based access
- **Enforcement**: Policy registry, permissions checks
- **Code Path**: `src/value_fabric/shared/identity/policy_registry.py`

### Tenant Isolation
- **Rule**: Tenant scoping must be enforced in storage operations
- **Enforcement**: Tenant-scoped storage, boundary checks
- **Code Path**: `src/value_fabric/shared/storage/`, `src/value_fabric/shared/boundaries/`

### Input Validation
- **Rule**: No unvalidated input reaching shared utilities
- **Enforcement**: Error handling, validation contracts
- **Code Path**: `src/value_fabric/shared/error_handling/`

### Audit Logging
- **Rule**: All security-relevant events must be audited
- **Enforcement**: Audit emitter, SIEM integration
- **Code Path**: `src/value_fabric/shared/audit/`

### Production Safety
- **Rule**: Production environment must reject insecure bypasses
- **Enforcement**: Production safety checks, security controls
- **Code Path**: `src/value_fabric/shared/security/`, `src/value_fabric/shared/startup.py`

### Contract Compliance
- **Rule**: Agent outputs must comply with canonical contracts
- **Enforcement**: Agent semantic contracts, tool boundary contracts
- **Code Path**: `src/python/canonical/`

## Test Markers
- Contract tests - Platform contract compliance tests
- Security tests - Authentication, authorization, tenant isolation tests

## Discovery Notes
- Shared packages have moderate test coverage (33 total tests)
- Platform contract tests focus on canonical contract compliance
- Good coverage of authentication and authorization in shared identity
- Tenant scoping tests present
- Production safety tests present
- Audit and SIEM integration tests present
- MCP gateway security tests present
