# Deferred Issues Documentation

This document categorizes and details the technical blockers for 195+ deferred test issues in the Layer 4 Agents codebase, providing actionable resolution paths.

## Executive Summary

- **Total Deferred Tests**: 195+ tests across 4 categories
- **Current Test Pass Rate**: 87.1% (1616/1855)
- **Primary Blockers**: Auth middleware complexity, external dependencies, API contract changes, integration test infrastructure

---

## Category 1: Complex Auth Middleware Mocking (56 tests)

### Affected Files
- `test_accounts_api.py` (27 tests) - 401 Unauthorized errors
- `test_workflow_controls.py` (8 tests) - 422 auth errors
- `test_harness_routes.py` (5 tests) - 401 auth errors
- `test_billing_service.py` (12 tests) - 401 auth errors
- `test_agent_tenant_isolation.py` (2 tests) - tenant context errors
- `test_admin_tool_h01.py` (1 test) - permission scope error
- `test_tenant_lifecycle.py` (4 tests) - GovernanceMiddleware signature issues

### Root Cause
GovernanceMiddleware no longer accepts `jwt_secret` parameter in `__init__`. Current signature:
```python
def __init__(
    self,
    app: Any,
    api_key_resolver: Optional[Callable] = None,
    rate_limiter: Optional[RedisRateLimiter] = None,
    tenant_settings_resolver: Optional[Callable] = None,
    on_rate_limit_hit: Optional[Callable[[str, str], None]] = None,
    enforce_authentication: bool = True,
) -> None:
```

Tests attempting to initialize with `jwt_secret` parameter fail with:
```
TypeError: GovernanceMiddleware.__init__() got an unexpected keyword argument 'jwt_secret'
```

### Technical Blockers
1. **Middleware API Change**: GovernanceMiddleware signature changed to remove `jwt_secret` parameter
2. **Auth Dependency Injection**: Tests use FastAPI with GovernanceMiddleware for authentication; simple dependency override insufficient
3. **Permission Scope Enforcement**: Some tests require specific admin permissions that middleware enforces
4. **Tenant Context Resolution**: Middleware resolves tenant from JWT; tests bypassing this lack context

### Required Actions
1. **Implement Test-Specific Middleware Factory**:
   - Create `TestGovernanceMiddleware` subclass that accepts test configuration
   - Override `_resolve_identity` to return mock RequestContext
   - Allow bypassing authentication with `enforce_authentication=False`

2. **Update Test Fixtures**:
   - Replace direct middleware instantiation with factory
   - Configure mock tenant context and user roles
   - Set `enforce_authentication=False` for service-layer tests

3. **Refactor Service-Layer Tests**:
   - For tests that don't need HTTP layer, call services directly
   - Pass RequestContext directly to service methods
   - Avoid FastAPI TestClient for unit tests

### Prerequisites
- GovernanceMiddleware test support implementation
- Mock RequestContext factory for tests
- Updated test fixtures across 7 files

### Priority
**Medium** - Auth is critical but requires architectural changes. Can be deferred until middleware test infrastructure is established.

---

## Category 2: External Dependencies (12 tests)

### Affected Files
- `test_webhook_security.py` (10 tests) - Stripe module not installed
- `test_billing_service.py` (multiple tests) - Stripe dependency
- `test_oidc.py` (2 tests) - network dependencies

### Root Cause
Stripe module is optional and not installed in test environment. Code handles this gracefully:
```python
try:
    import stripe
    _stripe_available = True
except ImportError:
    stripe = None
    _stripe_available = False
    logger.warning("stripe module not installed - billing features disabled")
```

Tests attempting to use Stripe features fail with:
```
value_fabric.layer4.services.stripe_client.StripeNotConfiguredError: Stripe module not installed. Install with: pip install stripe
```

### Technical Blockers
1. **Stripe Module Installation**: Requires `pip install stripe` in test environment
2. **Network Access**: OIDC tests require external auth provider connectivity
3. **Webhook Signature Verification**: Requires Stripe webhook signing key
4. **Test Environment Isolation**: External dependencies break hermetic test execution

### Required Actions
1. **Stripe Mocking Strategy**:
   - Implement comprehensive Stripe client mock
   - Mock webhook signature verification
   - Mock customer/subscription CRUD operations
   - Use `unittest.mock.patch.dict('sys.modules', {'stripe': mock_stripe_module})` pattern

2. **OIDC Network Isolation**:
   - Mock OIDC discovery endpoint responses
   - Use `respx` or `httpx` to intercept network calls
   - Skip tests requiring real network access with pytest markers

3. **Test Environment Configuration**:
   - Add optional Stripe dependency to test requirements
   - Configure test environment variables for Stripe keys
   - Document when to install Stripe for integration tests

### Prerequisites
- Stripe client mock implementation
- Network mocking library (respx/httpx)
- Test environment variable configuration

### Priority
**Low** - External dependency management is infrastructure concern. Tests should be mocked rather than requiring real external services.

---

## Category 3: API Contract Changes (3 tests)

### Affected Files
- `test_llm_budget_guardrails.py` (3 tests) - tenant_id parameter removal

### Root Cause
LLMBudgetGuardrails methods changed signatures to remove `tenant_id` parameter:

**Old Signature** (tests still using):
```python
async def precheck_or_raise(self, tenant_id: str, model: str) -> LLMBudgetDecision
async def record_usage(self, tenant_id: str, cost_usd: float) -> None
```

**New Signature** (current implementation):
```python
async def precheck_or_raise(self, model: str) -> LLMBudgetDecision
# tenant_id now resolved from RequestContext via require_context
```

Tests fail with:
```
TypeError: LLMBudgetGuardrails.precheck_or_raise() got an unexpected keyword argument 'tenant_id'
TypeError: LLMBudgetGuardrails.record_usage() got an unexpected keyword argument 'tenant_id'
```

### Technical Blockers
1. **API Contract Alignment**: Tests written against old API contract
2. **Tenant Context Resolution**: New implementation uses RequestContext instead of explicit tenant_id
3. **Test Isolation**: Tests need to set RequestContext before calling methods

### Required Actions
1. **Update Test Calls**:
   - Remove `tenant_id` parameter from `precheck_or_raise` calls
   - Remove `tenant_id` parameter from `record_usage` calls
   - Set RequestContext in test context before method calls

2. **Add Context Fixtures**:
   ```python
   @pytest.fixture
   def mock_tenant_context():
       with patch("value_fabric.shared.identity.context._get_context") as ctx_mock:
           ctx_mock.return_value = RequestContext(
               tenant_id="test-tenant",
               user_id="test-user",
               roles=[Role.TENANT_ADMIN.value]
           )
           yield
   ```

3. **Update Test Assertions**:
   - Verify tenant_id is resolved from context
   - Test with missing context (should fail appropriately)

### Prerequisites
- RequestContext mock fixture
- Test context management

### Priority
**Medium** - API contract alignment needed for test validity. Quick fix once context mocking is in place.

---

## Category 4: Complex Integration Issues (15+ tests)

### Affected Files
- `test_usage_idempotency.py` (3 tests) - rollback/validation issues
- `test_analysis_smoke_mode_service_routes.py` (5 tests) - import errors
- `test_agent_mutation_approval_audit.py` (2 tests) - import errors
- `test_plan_version_billing.py` (1 test) - StopAsyncIteration
- `test_context_gatherer.py` (2 tests) - undefined variables
- `test_analysis_routes.py` (1 test) - validation error

### Root Cause Analysis

#### 4.1 Import Path Errors (8 tests)
**Files**: `test_analysis_smoke_mode_service_routes.py`, `test_agent_mutation_approval_audit.py`

**Error**:
```
AttributeError: module 'value_fabric.layer4.api.routes.analysis' has no attribute 'get_db_from_context'
```

**Root Cause**: Tests import from `value_fabric.layer4.api.routes.analysis` but `get_db_from_context` is in `value_fabric.layer4.database`. Tests using incorrect import paths.

#### 4.2 Database Session Mocking Issues (3 tests)
**Files**: `test_usage_idempotency.py`

**Errors**:
```
AssertionError: Expected 'rollback' to have been called.
AttributeError: 'coroutine' object has no attribute '_stripe_response'
```

**Root Cause**: Async database session mocking is incomplete. Rollback verification fails because mocks don't properly simulate async behavior.

#### 4.3 Async Context Management (1 test)
**Files**: `test_plan_version_billing.py`

**Error**:
```
StopAsyncIteration
```

**Root Cause**: Async generator or iterator exhausted prematurely in test setup.

#### 4.4 Undefined Variables (2 tests)
**Files**: `test_context_gatherer.py`

**Errors**:
```
NameError: name 'MockSession' is not defined
NameError: name 'session' is not defined
```

**Root Cause**: Test fixtures or setup code missing variable definitions.

#### 4.5 Response Validation Errors (1 test)
**Files**: `test_analysis_routes.py`

**Error**:
```
fastapi.exceptions.ResponseValidationError: Input should be a valid dictionary
```

**Root Cause**: FastAPI response model validation failing due to TypedDict vs dict mismatch.

### Technical Blockers
1. **Import Path Refactoring**: Multiple files using incorrect canonical import paths
2. **Async Mock Complexity**: Properly mocking async database sessions requires understanding of SQLAlchemy async patterns
3. **Test Fixture Fragility**: Fixtures not properly isolated or cleaned up
4. **Response Model Mismatches**: TypedDict models not matching expected response shapes

### Required Actions

#### 4.1 Fix Import Paths
```python
# Incorrect (current)
from value_fabric.layer4.api.routes.analysis import get_db_from_context

# Correct
from value_fabric.layer4.database import get_db_from_context
```

#### 4.2 Improve Async Session Mocking
```python
@pytest.fixture
def mock_db():
    session = AsyncMock(spec=AsyncSession)
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()  # Ensure this is properly awaited
    return session
```

#### 4.3 Fix Async Generator Tests
- Ensure async generators are properly iterated
- Add proper cleanup in test fixtures
- Use `pytest-asyncio` markers correctly

#### 4.4 Define Missing Variables
- Add missing fixture definitions
- Ensure all test dependencies are properly scoped
- Use pytest fixtures instead of global variables

#### 4.5 Align Response Models
- Verify TypedDict models match actual response shapes
- Update response models if API has changed
- Add response validation tests

### Prerequisites
- Import path audit across test suite
- Async mocking best practices documentation
- Response model contract validation

### Priority
**Low** - Integration test stability is ongoing concern. These are individual test bugs that can be fixed incrementally.

---

## Resolution Sequence

### Phase 1: Quick Wins (1-2 days)
1. **Category 3: API Contract Changes** (3 tests)
   - Update LLMBudgetGuardrails test signatures
   - Add RequestContext mock fixture
   - **Impact**: 3 tests fixed, minimal risk

### Phase 2: Infrastructure (3-5 days)
2. **Category 1: Auth Middleware** (56 tests)
   - Implement TestGovernanceMiddleware factory
   - Update test fixtures
   - **Impact**: 56 tests fixed, enables future auth testing

### Phase 3: Integration Stability (5-7 days)
3. **Category 4: Integration Issues** (15+ tests)
   - Fix import paths
   - Improve async mocking
   - Fix fixture issues
   - **Impact**: 15+ tests fixed, improves overall test reliability

### Phase 4: External Dependencies (Ongoing)
4. **Category 2: External Dependencies** (12 tests)
   - Implement Stripe mocking
   - Add network mocking
   - **Impact**: 12 tests fixed, reduces external dependencies

---

## Recommendations

### Immediate Actions
1. Implement TestGovernanceMiddleware factory for auth testing
2. Update LLMBudgetGuardrails tests to match new API contract
3. Audit and fix import paths in test files

### Medium-Term Actions
1. Establish comprehensive async session mocking patterns
2. Implement Stripe client mocking strategy
3. Add network mocking for OIDC tests

### Long-Term Actions
1. Consider service-layer testing to avoid middleware complexity
2. Establish test environment with optional external dependencies
3. Implement integration test infrastructure improvements

---

## Dependencies

### Cross-Category Dependencies
- **Auth Middleware → Integration Issues**: Proper auth mocking needed for integration tests
- **API Contract → Auth Middleware**: RequestContext mocking needed for both
- **External Dependencies → Integration Issues**: Stripe mocking needed for billing integration tests

### External Dependencies
- Redis for rate limiting tests (optional, can be mocked)
- Stripe for billing tests (can be mocked)
- Network access for OIDC tests (can be mocked)
- PostgreSQL for integration tests (testcontainers available)

---

## Success Metrics

- **Target Test Pass Rate**: 95%+ (from current 87.1%)
- **Deferred Tests**: <50 (from current 195+)
- **Test Execution Time**: <2 minutes for full suite
- **Test Reliability**: <5% flaky test rate
