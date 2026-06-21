# Production Invariants

Generated: 2026-05-23 (Autonomous Test Assurance Agent - Phase 2 Extraction)
Source: Code analysis + contract.md + runtime patterns

## Tenant Isolation

### Rule: No cross-tenant reads or writes
- **Enforcement**: 
  - Neo4j: `require_request_tenant_id()` dependency extracts tenant from RequestContext
  - Cypher queries: Parameterised `tenant_id` in all MATCH clauses
  - Query validation: `QueryValidator` blocks unscoped Entity/tenant-owned label queries
  - Session wrapper: `Neo4jTenantSessionSecured` auto-injects tenant_id into parameters
- **Code Path**: 
  - `services/layer3-knowledge/src/api/dependencies_tenant_secured.py`
  - `services/layer3-knowledge/src/db/query_execution.py`
  - `services/layer3-knowledge/src/security/query_validator.py`
- **Fail-Closed**: Missing tenant context raises HTTPException 400

### Rule: Tenant context must be immutable and request-scoped
- **Enforcement**: RequestContext from shared.identity, AsyncLocalStorage propagation
- **Anti-Patterns Deprecated**: Passing tenantId as function parameter, direct header access outside auth middleware
- **Code Path**: `value_fabric/shared.identity/`

## Authentication

### Rule: No unauthenticated access to protected resources
- **Enforcement**: GovernanceMiddleware validates JWT/headers before route handlers
- **Contract**: Auth phase produces AuthContext; downstream code never re-validates
- **Code Path**: `services/api/` (API gateway auth enforcement)

### Rule: Missing tenant context must fail closed
- **Enforcement**: `require_request_tenant_id()` raises HTTPException 400 when context absent or empty
- **Code Path**: `services/layer3-knowledge/src/api/dependencies_tenant_secured.py:391-397`

## Authorization

### Rule: No authorization bypass via headers, params, body fields, or stale context
- **Enforcement**: 
  - Tenant context extracted from RequestContext (not raw headers)
  - Query parameterisation prevents injection via user input
  - `TenantQueryExecutor.run()` forces execution tenant over caller-supplied parameters
- **Code Path**: `services/layer3-knowledge/src/db/query_execution.py`

## Input Validation

### Rule: No unvalidated input reaching persistence, queues, tools, or LLM calls
- **Enforcement**: 
  - Pydantic schemas for request/response validation
  - FastAPI Query validation with bounds (depth: 1-MAX_QUERY_DEPTH)
  - Relationship type regex validation: `^[A-Z_][A-Z0-9_]*$`
- **Code Path**: 
  - `services/layer3-knowledge/src/api/routes/graph_viz.py:319` (_VALID_REL_TYPE)
  - `services/layer3-knowledge/src/api/routes/graph_viz.py:199` (depth validation)

## Query Execution Safety

### Rule: Cypher queries must be tenant-scoped
- **Enforcement**: 
  - `QueryValidator.validate_structural_tenant_scope()` blocks unscoped MATCH on tenant-owned labels
  - `TenantQueryExecutor._validate()` checks for tenant_id predicate
  - Fallback tenant-owned labels: Entity, Account, BusinessCase, etc. (90+ labels)
- **Code Path**: `services/layer3-knowledge/src/db/query_execution.py:48-93`

### Rule: Query depth must not exceed MAX_QUERY_DEPTH
- **Enforcement**: 
  - `MAX_QUERY_DEPTH = 10` (global limit)
  - `CypherDepthLimitExceeded` raised when depth exceeded
  - FastAPI Query validation: `depth=Query(2, ge=1, le=MAX_QUERY_DEPTH)`
- **Code Path**: `services/layer3-knowledge/src/db/query_execution.py:36`

### Rule: Query timeout enforced to prevent resource exhaustion
- **Enforcement**: 
  - `QUERY_TIMEOUT_SECONDS = 30.0`
  - `asyncio.wait_for()` wraps all Neo4j queries
  - Returns HTTPException 400 on timeout with code CYPHER_TIMEOUT
- **Code Path**: `services/layer3-knowledge/src/db/query_execution.py:37`

## Error Handling

### Rule: Security-sensitive errors must not leak information
- **Enforcement**: 
  - Entity-not-found returns 404 (not 403) to avoid existence leakage
  - Cross-tenant access attempts return 404 (not 403)
  - Neo4j unavailability returns 503 (not 500)
- **Code Path**: `services/layer3-knowledge/src/api/routes/graph_viz.py`

### Rule: All errors must follow canonical error shape
- **Enforcement**: HTTPException with status codes and structured detail messages
- **Contract**: Defined in contract.md section 2.5 (Error Response Contract)

## Database Isolation

### Rule: PostgreSQL RLS must enforce tenant isolation
- **Enforcement**: 
  - `SET LOCAL app.tenant_id = :tenant_id` at transaction start
  - RLS policy: `tenant_id::text = current_setting('app.tenant_id', true)`
  - Every tenant-scoped table MUST have `tenant_id` NOT NULL column
- **Code Path**: Migration files in all layers, `services/layer5-ground-truth/tests/test_tenant_id_consistency.py`

## Tool Invocation

### Rule: Tools must inherit tenant context from orchestrating agent
- **Enforcement**: Tenant context propagated via AsyncLocalStorage, not function parameters
- **Anti-Patterns Deprecated**: Tools accessing tenant context via function parameters
- **Code Path**: `contracts/agent-registry/`

## Rate Limiting

### Rule: Rate limiting keyed by tenant_id + endpoint_pattern + identity_hash
- **Enforcement**: Middleware phase 5 applies rate limits
- **Code Path**: `tests/test_tenant_rate_limiting.py`

## Layer 3 Specific Invariants

### Rule: Graph visualization routes must be tenant-scoped
- **Enforcement**: All 3 endpoints (`/graph`, `/entities/{id}/subgraph`, `/v1/graph/subgraph`) use `require_request_tenant_id`
- **Code Path**: `services/layer3-knowledge/src/api/routes/graph_viz.py:81,198,324`

### Rule: Neo4j session must be secured for tenant operations
- **Enforcement**: `Neo4jTenantSessionSecured` wrapper with query validation
- **Code Path**: `services/layer3-knowledge/src/api/dependencies_tenant_secured.py:89-242`

### Rule: Relationship type filtering must prevent injection
- **Enforcement**: Regex validation `_VALID_REL_TYPE` before Cypher interpolation
- **Code Path**: `services/layer3-knowledge/src/api/routes/graph_viz.py:319,381-386`

## Critical Invariants Requiring Regression Tests

1. **P0**: Missing tenant context → HTTPException 400 (all endpoints)
2. **P0**: Cross-tenant data access → blocked by query parameterisation
3. **P0**: Unscoped Cypher queries → blocked by QueryValidator
4. **P1**: Query depth > MAX_QUERY_DEPTH → rejected with 422
5. **P1**: Query timeout → returns 400 with CYPHER_TIMEOUT code
6. **P1**: Relationship type injection → blocked by regex
7. **P1**: Entity-not-found → returns 404 (not 403)
8. **P1**: Neo4j unavailability → returns 503
9. **P2**: Empty tenant_id in context → rejected with 400
10. **P2**: Malformed tenant_id → rejected by validation

## Phase 2 Extraction Updates (2026-05-23)
- **DB Session Pattern**: `SET LOCAL app.tenant_id` enforced in L4/L5 database.py
- **Tenant Context**: RequestContext from value_fabric.shared.identity.context
- **Auth Middleware**: GovernanceMiddleware validates JWT/headers
- **Validation**: Pydantic BaseModel schemas for request/response
- **Error Handling**: HTTPException with 401/403/404/503 status codes
- **RLS Policies**: PostgreSQL Row-Level Security with tenant_id::text = current_setting('app.tenant_id', true)
- **Fail-Closed**: MissingTenantContextError raised when tenant context absent
- **Privileged Access**: X-Privileged-Reason header for admin bypass with audit logging
