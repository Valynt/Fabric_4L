# Production Invariants

Generated: 2026-05-27

## Tenant Isolation

### Rule: No cross-tenant reads or writes
- **Enforcement**: PostgreSQL RLS policies with `SET LOCAL app.tenant_id`
- **Code Path**: 
  - `packages/shared/src/value_fabric/shared/storage/client.py` - Storage key normalization with tenant_id
  - `services/layer7-billing/src/layer7_billing/database.py` - `db_session_for_context(tenant_id)` sets PostgreSQL config
  - `services/layer5-ground-truth/tests/test_tenant_id_consistency.py` - Validates tenant_id column usage
- **Contract Reference**: docs/contract.md §2.2 (ratified 2026-04-25)
- **Anti-patterns Deprecated**: 
  - Passing tenantId as parameter through service layers
  - Using organization_id instead of tenant_id
  - Ad-hoc tenant ID in raw SQL queries

### Rule: Tenant context must be immutable and request-scoped
- **Enforcement**: AsyncLocalStorage or language-equivalent
- **Code Path**: `services/layer7-billing/src/layer7_billing/database.py` - `get_db_from_context()` reads from RequestContext
- **Contract Reference**: docs/contract.md §2.1 (proposed, target ratified 2026-05-23)
- **Required Fields**: tenant_id (UUIDv4), tenant_tier, region, issued_at, scope

## Authentication

### Rule: No unauthenticated access to protected resources
- **Enforcement**: `require_authenticated` dependency in FastAPI routes
- **Code Path**: 
  - `services/layer4-agents/tests/test_agent_tenant_isolation.py` - Uses `require_authenticated` override
  - `services/api/app/tests/test_auth_enforcement.py` - Auth enforcement tests
- **Validation**: JWT token validation, JWKS verification
- **Code Path**: `services/api/app/tests/test_jwks_and_token_validation.py`

### Rule: No authorization bypass via headers, params, body fields, or stale context
- **Enforcement**: Role checks, permission validators
- **Code Path**: `services/api/app/tests/test_impersonation_security.py` - Impersonation security tests
- **Anti-patterns**: Direct header access outside auth middleware, deriving context differently per service

## Input Validation

### Rule: No unvalidated input reaching persistence, queues, tools, or LLM calls
- **Enforcement**: Pydantic schema validation
- **Code Path**: 
  - `services/layer7-billing/src/layer7_billing/api/main.py` - Principal, Plan, UsageEventIn models
  - `services/layer6-benchmarks/tests/test_settings_validation.py` - Settings validation
- **Contract Reference**: docs/contract.md §2.3 (input validation pattern)

### Rule: Password security must follow bcrypt production behavior
- **Enforcement**: Bcrypt with proper salt and work factor
- **Code Path**: `services/api/app/tests/test_bcrypt_security.py` - Password hashing validation
- **Invariants**: 
  - Passwords over 72 bytes rejected
  - 72-byte limit accepted
  - Proper salt generation

## Database Isolation

### Rule: Every tenant-scoped table MUST have tenant_id column with NOT NULL
- **Enforcement**: Migration validation, platform_contract_lint.py
- **Code Path**: `services/layer5-ground-truth/tests/test_tenant_id_consistency.py` - Validates column naming
- **Contract Reference**: docs/contract.md §2.2 (ratified)

### Rule: Every tenant-scoped table MUST have RLS policy using current_setting('app.tenant_id', true)
- **Enforcement**: Migration 006 fixes RLS policies after org_id → tenant_id rename
- **Code Path**: `services/layer5-ground-truth/tests/test_migration_validation.py` - RLS policy validation
- **Policy Expression**: `tenant_id::text = current_setting('app.tenant_id', true)`

### Rule: All production endpoints MUST use get_db_from_context() (not get_db())
- **Enforcement**: CI lint flags `Depends(get_db)` in production routes
- **Code Path**: `services/layer7-billing/src/layer7_billing/api/main.py` - Uses `get_db_from_context`
- **Contract Reference**: docs/contract.md §2.2

## Async Task Propagation

### Rule: Background tasks must set tenant context before any DB operation
- **Enforcement**: Explicit `SET LOCAL` using tenant_id from task payload
- **Code Path**: `services/layer1-ingestion/tests/security/test_celery_tenant_isolation_postgres.py`
- **Contract Reference**: docs/contract.md §2.2

### Rule: Message queue propagation requires explicit tenant_id field in every message payload
- **Enforcement**: Payload validation in Celery tasks
- **Code Path**: `services/layer1-ingestion/src/shared/tasks.py` - Celery task definitions
- **Recent Implementation**: L1→L2 Celery dispatch with tenant_id in payload

## Storage Isolation

### Rule: Storage keys must be tenant-scoped with normalized prefix
- **Enforcement**: `tenant-{tenant_id}/{key}` prefix pattern
- **Code Path**: `packages/shared/src/value_fabric/shared/storage/client.py` - `_normalize_key()` method
- **Invariant**: Tenant ID always prefixed to prevent cross-tenant access

## Rate Limiting

### Rule: Rate limiting must be tenant-scoped and enforced at gateway
- **Enforcement**: Tenant-aware rate limiting
- **Code Path**: `tests/test_tenant_rate_limiting.py` - Rate limiting validation
- **Invariant**: No tenant can exceed configured rate limits

## Production Safety

### Rule: Health endpoints must not expose internal URLs or sensitive data
- **Enforcement**: Health endpoint validation
- **Code Path**: `services/layer5-ground-truth/tests/test_security_fixes.py` - Health endpoint safety
- **Invariant**: Health responses contain only status indicators

### Rule: Clerk webhooks must be idempotent
- **Enforcement**: Webhook idempotency validation
- **Code Path**: `services/api/app/tests/test_clerk_webhook_idempotency.py`
- **Invariant**: Duplicate webhook events are handled safely

## Cross-Service Communication

### Rule: Cross-service requests must propagate tenant context via headers
- **Enforcement**: `x-fabric-tenant-id` header with signature verification
- **Contract Reference**: docs/contract.md §2.1
- **Code Path**: L1→L2 Celery dispatch implementation

### Rule: API contracts must be stable and versioned
- **Enforcement**: OpenAPI drift detection
- **Code Path**: `.github/workflows/openapi-drift-check.yml`
- **Invariant**: Breaking changes require version bump
