# Production Invariants

Generated: 2026-05-04 (Autonomous Test Assurance Agent - Phase 2)

## Security Invariants

### Tenant Isolation
- **Rule**: No cross-tenant reads or writes across API, persistence, graph, search, agent, export, and audit surfaces
- **Enforcement**: PostgreSQL RLS policies with `SET LOCAL app.tenant_id`, RequestContext tenant context, fail-safe validation
- **Code Path**:
  - `services/layer4-agents/src/database.py` - validate_tenant_id(), set_tenant_context(), get_db_from_context()
  - `services/layer5-ground-truth/src/layer5_ground_truth/database.py` - validate_tenant_id(), get_db_from_context()
  - `packages/shared/src/value_fabric/shared/identity/context.py` - RequestContext with immutable tenant_id
  - `packages/shared/src/value_fabric/shared/identity/middleware.py` - GovernanceMiddleware resolution order
  - RLS migrations in layer4-agents and layer5-ground-truth with admin_role/system_role TO clauses
- **Fail-Safe Mode**: FAIL_SAFE_MODE=True requires explicit tenant context, rejects missing/empty tenant_id
- **Reserved Keywords**: 'system', 'admin', 'internal' for system operations
- **Bypass**: Super-admin operations only via explicit is_super_admin() check with admin_role/system_role in RLS TO clauses
- **Validation Metrics**: Tracked via _tenant_validation_metrics (validations_total, validation_failures, uuid_format_errors, missing_context_errors, empty_tenant_errors)

### Authentication
- **Rule**: No unauthenticated access to protected resources
- **Enforcement**: GovernanceMiddleware with JWT verification, X-API-Key HMAC verification, X-Tenant-ID header fallback
- **Code Path**:
  - `packages/shared/src/value_fabric/shared/identity/middleware.py` - GovernanceMiddleware resolution order
  - `services/layer5-ground-truth/src/layer5_ground_truth/api/auth.py` - get_current_user() dependency
  - JWT decoded with JWT_SECRET, verifies exp claim, HMAC-SHA256 signature
  - Resolution order: Bearer JWT → X-API-Key → X-Tenant-ID → query param (dev/test only)
  - RequestContext stored in ContextVar for downstream access
- **Public Paths**: /health, /metrics, /docs, /openapi.json, /redoc bypass authentication
- **Failure Mode**: HTTP 401 Unauthorized if no valid identity resolved
- **JWT Claims**: tenant_id (required), user_id, roles, raw payload
- **Auth Sources**: jwt_claim, api_key, service_account (normalized via _normalise_auth_source)

### Authorization
- **Rule**: No authorization bypass via headers, params, body fields, or stale context
- **Enforcement**: Role-based access control via RequestContext.has_role(), is_super_admin(), Permission checks
- **Code Path**:
  - `packages/shared/src/value_fabric/shared/identity/context.py` - RequestContext.has_role(), has_permission(), is_super_admin()
  - `services/layer5-ground-truth/src/layer5_ground_truth/api/auth.py` - TokenClaims.require_role()
  - `packages/shared/src/value_fabric/shared/identity/permissions.py` - ROLE_PERMISSIONS mapping
- **Immutable Fields**: RequestContext.tenant_id and permissions are immutable after construction (__setattr__ protection)
- **Privileged Access**: require_privileged_access() for admin operations
- **Failure Mode**: HTTP 403 Forbidden if role/permission requirements not met

### Input Validation
- **Rule**: No unvalidated input reaching persistence, queues, tools, or LLM calls
- **Enforcement**: Pydantic BaseModel schemas with Field() validators, field_validator, model_validator
- **Code Path**:
  - `services/layer5-ground-truth/src/layer5_ground_truth/api/schemas.py` - TruthSourceCreate, TruthObjectCreate, ValidateRequest with validators
  - `services/layer6-benchmarks/src/api/schemas.py` - DatasetSummary, ComparisonRequestPayload, ValidationRequestPayload
  - `services/layer6-benchmarks/src/config.py` - field_validator for neo4j_password
  - UUID validation via validate_tenant_id() for tenant_id fields
  - String length constraints (min_length, max_length), numeric ranges (ge, le)
- **Failure Mode**: HTTP 400 Bad Request on validation errors
- **Specific Validations**: claim_not_empty(), dispute_reason required when action='dispute', neo4j_password cannot be 'password'

### Secrets Protection
- **Rule**: No secrets exposed in logs, errors, responses, bundles, or LLM prompts
- **Enforcement**: Secret redaction in LLM safety guards, K8s secretKeyRef for credentials, Infisical integration
- **Code Path**:
  - `tests/security/test_week4_llm_safety.py` - password/API key redaction
  - `tests/security/test_week2_credential_hardening.py` - secretKeyRef validation
  - `services/layer6-benchmarks/src/api/main.py` - load_infisical_secrets()
  - MIN_SERVICE_SECRET_LENGTH = 32 for X-Service-Auth header
- **Failure Mode**: Secret redaction before logging or LLM inclusion

## Reliability Invariants

### Error Handling
- **Rule**: All exceptions are caught and converted to appropriate HTTP responses
- **Enforcement**: Try/except blocks with HTTPException raising, specific exception handling
- **Code Path**:
  - `services/layer6-benchmarks/src/database.py` - AuthError, ConfigurationError, ServiceUnavailable handling
  - `services/layer5-ground-truth/src/layer5_ground_truth/database.py` - TenantContextError handling
- **Failure Mode**: HTTP 5xx for system errors, HTTP 4xx for client errors

### Database Session Management
- **Rule**: Database sessions always commit or rollback, never left in ambiguous state
- **Enforcement**: Async context managers with try/commit/except/rollback pattern
- **Code Path**:
  - `services/layer5-ground-truth/src/layer5_ground_truth/database.py` - get_db_from_context(), db_session()
- **Failure Mode**: Automatic rollback on exception, session cleanup on shutdown

### Rate Limiting
- **Rule**: API endpoints are rate-limited to prevent abuse
- **Enforcement**: RedisRateLimiter with configurable REDIS_RATE_LIMITING_REQUIRED flag
- **Code Path**:
  - `services/layer5-ground-truth/src/layer5_ground_truth/api/main.py` - redis_rate_limiter initialization
  - `services/layer4-agents/tests/test_crm_tools_pagination.py` - rate limit graceful handling
- **Failure Mode**: HTTP 429 Too Many Requests when rate limit exceeded

### Connection Pooling
- **Rule**: Database connections are pooled and reused efficiently
- **Enforcement**: SQLAlchemy async_sessionmaker with pool_size, max_overflow, pool_pre_ping
- **Code Path**:
  - `services/layer5-ground-truth/src/layer5_ground_truth/database.py` - get_engine() pool configuration
- **Failure Mode**: Connection pool exhaustion handled by max_overflow

## Governance Invariants

### Audit Logging
- **Rule**: All tenant-scoped operations are logged with tenant context
- **Enforcement**: Structured logging with tenant_id from RequestContext
- **Code Path**:
  - Logging configured in pytest.ini with LOG_LEVEL=DEBUG for tests
  - RequestContext provides tenant context for all operations
- **Failure Mode**: Logs include tenant_id for traceability

### Session Cleanup
- **Rule**: Expired sessions are cleaned up automatically
- **Enforcement**: OIDCCleanupTask background service for session expiration
- **Code Path**:
  - `services/layer4-agents/tests/test_oidc_cleanup.py` - cleanup_expired_oidc_sessions()
- **Failure Mode**: Expired sessions deleted, rollback on error

### Cascade Deletion
- **Rule**: Related entities are deleted when parent is deleted
- **Enforcement**: SQLAlchemy cascade delete on relationships
- **Code Path**:
  - `services/layer5-ground-truth/tests/test_model_registry.py` - cascade delete tests
- **Failure Mode**: Related entities automatically deleted with parent

### Data Consistency
- **Rule**: Database transactions maintain ACID properties
- **Enforcement**: AsyncSession with autocommit=False, autoflush=False, explicit commit/rollback
- **Code Path**:
  - `services/layer5-ground-truth/src/layer5_ground_truth/database.py` - session factory configuration
- **Failure Mode**: Transaction rollback on any exception

## Critical Test Requirements

### Positive Tests Required
- Valid JWT authentication succeeds
- Valid X-Tenant-ID header authentication succeeds
- Tenant-scoped queries return only tenant's own data
- Role-based authorization permits authorized actions
- Valid input passes Pydantic validation
- Database commits succeed on valid operations
- Rate limiting permits normal usage

### Negative/Adversarial Tests Required
- Invalid JWT fails with 401
- Missing authentication fails with 401
- Cross-tenant access fails with 403/404
- Unauthorized role access fails with 403
- Invalid input fails with 400
- Malformed UUID fails validation
- SQL injection attempts are blocked
- Secrets are redacted from logs/responses
- Rate limit exceeded returns 429
- Concurrent tenant isolation is maintained

### Regression Tests Required
- RLS policy bypass attempts fail
- Super-admin bypass requires explicit role
- Query param fallback disabled in production
- Session cleanup removes expired sessions
- Cascade deletion removes all related entities
- Connection pool handles exhaustion gracefully
