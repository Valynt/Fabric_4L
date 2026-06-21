# API Gateway Test Inventory

Generated: 2026-05-28

## Backend Tests
| Layer | Unit Tests | Integration Tests | Security Tests | E2E Tests |
|-------|-----------|-------------------|----------------|-----------|
| API Gateway | 0 unit tests | 26 integration tests | 10 security tests | 0 E2E tests |

## Test Categories

### Integration Tests (26 files)
- test_account_scope_isolation.py
- test_accounts.py
- test_agent_orchestrator.py
- test_agents.py
- test_audit_middleware.py
- test_auth_enforcement.py
- test_bcrypt_security.py
- test_clerk_webhook_idempotency.py
- test_database_tenant_boundary.py
- test_distributed_session_store.py
- test_distributed_store_contract.py
- test_driver_and_realization_response_shapes.py
- test_governance.py
- test_health.py
- test_i03_durable_persistence_and_llm.py
- test_impersonation_security.py
- test_intelligence_routes.py
- test_invitation_and_tenant_leakage.py
- test_jwks_and_token_validation.py
- test_privacy_dsar.py
- test_production_safety.py
- test_roi.py
- test_store_failure_modes.py
- test_tenant_isolation.py

### Security Tests (10 files)
- test_account_scope_isolation.py
- test_auth_enforcement.py
- test_bcrypt_security.py
- test_database_tenant_boundary.py
- test_impersonation_security.py
- test_invitation_and_tenant_leakage.py
- test_jwks_and_token_validation.py
- test_production_safety.py
- test_store_failure_modes.py
- test_tenant_isolation.py

## Key Invariants Discovered

### Tenant Isolation
- **Rule**: No cross-tenant reads or writes in gateway routes
- **Enforcement**: Tenant-required dependency, JWT-based tenant context
- **Code Path**: `app/core/tenant_context.py`, `app/core/tenant_enforcement.py`

### Authentication
- **Rule**: No unauthenticated access to protected resources
- **Enforcement**: JWT validation, Clerk authentication, auth enforcement middleware
- **Code Path**: `app/core/clerk_auth.py`, `app/core/auth_directory.py`

### Authorization
- **Rule**: No authorization bypass via headers, params, body fields
- **Enforcement**: Role-based access, account scope isolation
- **Code Path**: `app/core/account_scope.py`, `app/core/audit.py`

### Input Validation
- **Rule**: No unvalidated input reaching downstream services
- **Enforcement**: Pydantic schemas, validation middleware
- **Code Path**: `app/models/schemas.py`

### Impersonation Security
- **Rule**: Impersonation must be strictly controlled and audited
- **Enforcement**: Impersonation security checks, audit logging
- **Code Path**: `app/core/audit.py`, impersonation tests

### Webhook Security
- **Rule**: Clerk webhooks must validate signatures and enforce idempotency
- **Enforcement**: Webhook signature validation, idempotency keys
- **Code Path**: `app/routers/clerk_webhooks.py`

## Test Markers
- `@pytest.mark.parametrize` - Parameterized tests
- `@pytest.mark.skip` - Conditional test skipping

## Discovery Notes
- API Gateway has moderate test coverage (26 total tests, no unit tests)
- Strong security test coverage (10 security tests)
- Good coverage of tenant isolation and authentication
- Clerk webhook idempotency tests present
- Impersonation security tests present
- Invitation and tenant leakage tests present
- Production safety tests present
