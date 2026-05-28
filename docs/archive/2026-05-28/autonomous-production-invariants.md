# Production Invariants

Generated: 2026-05-28

## Tenant Isolation

### Rule: No cross-tenant reads or writes
- **Enforcement**: PostgreSQL RLS policies with `SET LOCAL app.tenant_id` at transaction start
- **Code Path**: 
  - `services/layer7-billing/src/layer7_billing/database.py:38` - `db_session_for_context` executes `set_config('app.tenant_id', :tenant_id)`
  - `services/layer5-ground-truth/src/layer5_ground_truth/migrations/versions/006_fix_rls_org_to_tenant.py` - RLS policy fixes
  - `services/layer4-agents/migrations/versions/026_fix_rls_null_tenant_policy.py` - RLS coverage
- **Anti-patterns**: Using `get_db()` without tenant context, ad-hoc tenant filtering in queries
- **Contract Reference**: docs/contract.md section 2.2

### Rule: Tenant context must be present in all database operations
- **Enforcement**: `get_db_from_context()` dependency requires `x_tenant_id` header
- **Code Path**: 
  - `services/layer7-billing/src/layer7_billing/database.py:47` - `get_db_from_context` reads from header
  - `services/layer4-agents/src/tenants/api/routes/tenants.py:78` - All routes use `Depends(get_db_from_context)`
- **Validation**: `require_tenant_context` raises 400 if tenant_id missing
- **Contract Reference**: docs/contract.md section 2.1

### Rule: Celery tasks must propagate tenant_id explicitly
- **Enforcement**: All Celery task signatures include `tenant_id` parameter
- **Code Path**:
  - `services/layer1-ingestion/src/shared/tasks.py:200` - `process_scraping_job(self, job_id: str, tenant_id: str)`
  - `services/layer2-extraction/src/layer2_extraction/shared/tasks.py:74` - `run_extraction_task` validates tenant_id in config
  - `services/layer1-ingestion/src/shared/tasks.py:786` - L1→L2 dispatch includes tenant_id in extraction_payload
- **Anti-patterns**: Tasks without tenant_id parameter, reading tenant from global state
- **Contract Reference**: docs/contract.md section 2.1 (Message queue propagation)

## Authentication

### Rule: No unauthenticated access to protected resources
- **Enforcement**: `require_authenticated` dependency on all protected routes
- **Code Path**:
  - `services/layer4-agents/src/tenants/api/routes/tenants.py:79` - `Depends(require_authenticated)`
  - `services/layer4-agents/src/tenants/api/routes/admin.py:111` - Admin routes require auth
- **Test Coverage**: `services/api/app/tests/test_auth_enforcement.py`
- **Contract Reference**: docs/contract.md section 2.3 (auth phase)

### Rule: Authentication context is immutable after establishment
- **Enforcement**: RequestContext is frozen after auth middleware sets it
- **Code Path**: `packages/shared/src/value_fabric/shared/identity/context.py` - RequestContext implementation
- **Anti-patterns**: Re-validating auth in route handlers, modifying request.state.identity
- **Contract Reference**: docs/contract.md section 2.3

## Authorization

### Rule: No authorization bypass via headers, params, body fields, or stale context
- **Enforcement**: Role checks via `require_role()` and tenant admin validation
- **Code Path**:
  - `services/layer7-billing/src/layer7_billing/api/main.py:64` - `require_role(principal, "billing:write")`
  - `services/layer4-agents/src/tenants/api/routes/admin.py:111` - `Depends(require_tenant_admin)`
- **Test Coverage**: `services/layer4-agents/tests/test_authorization_adversarial.py`
- **Contract Reference**: docs/contract.md section 2.3 (tenant_scope phase)

### Rule: Role-based access control is enforced at dependency level
- **Enforcement**: `require_tenant_admin`, `require_role` dependencies
- **Code Path**: `services/layer4-agents/src/tenants/api/routes/admin.py` - All admin routes
- **Anti-patterns**: Inline role checks in handlers, role inference from user properties
- **Contract Reference**: docs/contract.md section 2.3

## Input Validation

### Rule: No unvalidated input reaching persistence, queues, tools, or LLM calls
- **Enforcement**: Pydantic schema validation on all route inputs
- **Code Path**: FastAPI route parameters use Pydantic models
- **Validation**: OpenAPI spec validation in CI (contract-compliance workflow)
- **Anti-patterns**: Raw dict access, manual parsing, bypassing Pydantic
- **Contract Reference**: docs/contract.md section 2.3 (validation phase)

### Rule: LLM/tool inputs are validated against JSON Schema
- **Enforcement**: Tool registry with schema validation
- **Code Path**: `services/layer4-agents/src/tools/` - Tool definitions with schemas
- **Contract Reference**: docs/contract.md section 2.4 (Tool Invocation Boundary)

## Error Handling

### Rule: All HTTP errors follow canonical error envelope
- **Enforcement**: Structured error responses with code, message, request_id
- **Code Path**: `packages/shared/src/value_fabric/shared/error_handling/` - Error handling middleware
- **Contract Reference**: docs/contract.md section 2.6 (Canonical API Error Envelope)

### Rule: Error responses do not leak internal state
- **Enforcement**: Sanitized error messages, no stack traces in production
- **Code Path**: Error middleware filters internal details
- **Test Coverage**: `services/api/app/tests/test_production_safety.py`
- **Contract Reference**: docs/contract.md section 2.6

## Observability

### Rule: All requests have trace correlation IDs
- **Enforcement**: `RequestIDMiddleware` assigns X-Request-ID header
- **Code Path**: `packages/shared/src/value_fabric/shared/error_handling/middleware.py:60` - Trace ID assignment
- **Propagation**: Headers propagated across service boundaries
- **Contract Reference**: docs/contract.md section 2.3 (correlation phase)

### Rule: Agent/tool calls are traced with OpenTelemetry
- **Enforcement**: OTel spans for tool execution
- **Code Path**: `services/layer3-knowledge/src/tracing/middleware.py` - OTel integration
- **Contract Reference**: docs/contract.md section 2.5 (Agent Output Traceability)

## Resource Management

### Rule: Database sessions are scoped to request lifecycle
- **Enforcement**: `db_session_for_context` context manager
- **Code Path**: `services/layer7-billing/src/layer7_billing/database.py:36` - Session lifecycle
- **Anti-patterns**: Long-lived sessions, manual session management
- **Contract Reference**: docs/contract.md section 2.2

### Rule: Redis connections use tenant-scoped keys
- **Enforcement**: Tenant ID prefix in all cache keys
- **Code Path**: `services/layer1-ingestion/tests/security/test_global_robots_cache_isolation_postgres.py`
- **Test Coverage**: `tests/cache/test_redis_tenant_isolation.py`

## Rate Limiting

### Rule: Rate limiting is keyed by tenant_id + endpoint + identity
- **Enforcement**: Redis-backed rate limiter with composite keys
- **Code Path**: Rate limiting middleware in layer4-agents
- **Test Coverage**: `services/layer4-agents/tests/test_tenant_rate_limits.py`
- **Contract Reference**: docs/contract.md section 2.3 (rate_limit phase)

## Celery Task Dispatch

### Rule: Cross-service Celery dispatch uses fully qualified task names
- **Enforcement**: `send_task` with full module path
- **Code Path**: `services/layer1-ingestion/src/shared/tasks.py:802` - `"layer2_extraction.shared.tasks.run_extraction_task"`
- **Anti-patterns**: Short task names without module path
- **Recent Fix**: P0 bug fixed in code review (2026-05-28)

### Rule: Celery tasks validate tenant_id before execution
- **Enforcement**: Tenant ID validation at task entry point
- **Code Path**: `services/layer2-extraction/src/layer2_extraction/shared/tasks.py:92` - `if not tenant_id: raise ValueError`
- **Contract Reference**: docs/contract.md section 2.1 (Message queue propagation)

## API Contract Compliance

### Rule: All API changes are reflected in OpenAPI spec
- **Enforcement**: OpenAPI drift detection in CI
- **Code Path**: `.github/workflows/openapi-drift-check.yml`
- **Contract Reference**: docs/contract.md section 2.3 (OpenAPI validation)

### Rule: Frontend-backend contracts are synchronized
- **Enforcement**: Contract sync workflow
- **Code Path**: `.github/workflows/l4-frontend-contract-sync.yml`
- **Contract Reference**: docs/contract.md section 2.7

## Security Hardening

### Rule: No hardcoded credentials in code
- **Enforcement**: Credential scan in CI
- **Code Path**: `scripts/ci/check_hardcoded_credentials.py`
- **Test Coverage**: `tests/security/` - Security regression tests

### Rule: Production gates enforce fail-closed behavior
- **Enforcement**: Environment variable gating, feature flags
- **Code Path**: `services/layer1-ingestion/tests/security/test_production_gates_postgres.py`
- **Contract Reference**: docs/contract.md section 2.2 (fail-safe RLS)

## Migration Governance

### Rule: All migrations are reversible
- **Enforcement**: Alembic downgrade paths
- **Code Path**: Migration files in all layers
- **Test Coverage**: `tests/arch/test_no_merge_markers.py` - Migration validation

### Rule: Migrations preserve tenant isolation
- **Enforcement**: RLS policy updates in tenant-related migrations
- **Code Path**: `services/layer5-ground-truth/src/layer5_ground_truth/migrations/versions/006_fix_rls_org_to_tenant.py`
- **Contract Reference**: docs/contract.md section 2.2
