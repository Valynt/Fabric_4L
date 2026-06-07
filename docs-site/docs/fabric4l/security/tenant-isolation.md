---
owner: security-team
status: active
last_reviewed: 2026-06-07
---

# Tenant Isolation

Tenant isolation is a **first-class invariant** in Value Fabric. Any data read or write must be scoped by authenticated tenant context. This page documents how tenant context is extracted, propagated, filtered in databases and graph queries, and audited. It also covers common anti-patterns that must be avoided.

!!! danger "Invariant"
    Any data read or write must be scoped by tenant context. Do not trust request body tenant IDs over authenticated context. Missing tenant context must **fail closed**.

## How Tenant Context Is Extracted

Tenant context is established at the **auth** middleware phase and propagated automatically across the request lifecycle.

| Step | Mechanism | Location |
|---|---|---|
| 1. JWT validation | `sub`, `tenant_id`, `role` claims extracted from Bearer token | `GovernanceMiddleware` auth phase |
| 2. Header spoofing ignored | `X-Tenant-ID` header is ignored; JWT `tenant_id` claim takes precedence | Middleware |
| 3. Context injection | `RequestContext` attached to `request.state.context` | Middleware |
| 4. DB session setup | `SET LOCAL app.tenant_id = :tenant_id` at transaction start | `get_db_from_context()` |
| 5. Graph query scoping | `$tenant_id` parameter bound to every Cypher query | Neo4j session helpers |
| 6. Cache key prefixing | Redis keys prefixed with `tenant:{tenant_id}:` | Cache layer |

!!! warning "Static tenant inference enforcement"
    The CI static gate `scripts/ci/boundary_check.py` blocks runtime source code from inferring tenant context from:
    - `request.headers.get("X-Tenant-ID")`
    - `request.query_params`
    - `.get("tenant_id")` on request payload/query objects
    - `api_key.tenant_id` or `getattr(api_key, "tenant_id", ...)`

    Allowed exceptions are limited to shared tenant resolver compatibility paths under `packages/shared/src/shared/identity/*` and `packages/shared/src/shared/boundaries/tenant_boundary.py`.

## Preferred Pattern vs Anti-Pattern

### Secure (Preferred)

```python
# Extract tenant_id from authenticated context
tenant_id = ctx.tenant_id

# Pass to repository/service methods
repo.method(..., tenant_id=tenant_id)

# Database session uses context-derived tenant
async with get_db_from_context(ctx) as db:
    result = await repo.get_entities(db, tenant_id=ctx.tenant_id)
```

### Insecure (Blocked)

```python
# NEVER trust request body tenant IDs
tenant_id = request.json().get("tenant_id")  # BLOCKED

# NEVER read tenant from headers outside auth middleware
tenant_id = request.headers.get("X-Tenant-ID")  # BLOCKED by static gate

# NEVER use raw SQL with inline tenant_id
query = f"SELECT * FROM entities WHERE tenant_id = '{tenant_id}'"  # BLOCKED
```

## Database Query Filtering (PostgreSQL RLS)

All tenant-scoped tables use **shared-schema PostgreSQL** with mandatory `tenant_id` columns and Row-Level Security (RLS) policies.

### RLS Policy Specification

| Concern | Canonical Decision |
|---|---|
| Isolation model | Shared schema + `tenant_id` NOT NULL + RLS |
| Session variable | `SET LOCAL app.tenant_id = :tenant_id` |
| RLS policy expression | `tenant_id::text = current_setting('app.tenant_id', true)` |
| Admin bypass | `SET LOCAL app.tenant_id = ''` with `admin_role` / `system_role` + audit logging |
| FastAPI dependency | `get_db_from_context()` reads tenant from `RequestContext` |
| Background tasks | Explicit `SET LOCAL` using `tenant_id` from task payload |

### RLS Enforcement Tests

`tests/security/test_tenant_isolation.py` includes database-level RLS tests:

```python
def test_postgres_rls_policy_blocks_cross_tenant_select(
    self, client, tenant_a_token, db_connection
):
    # Direct DB query without tenant context
    with db_connection.cursor() as cursor:
        cursor.execute(
            "SELECT id, tenant_id FROM entities WHERE id = %s", (entity_id,)
        )
        result = cursor.fetchone()
        # RLS should return None because no tenant context is set
        assert result is None or result[1] == "tenant-a"

def test_postgres_rls_policy_blocks_cross_tenant_update(
    self, client, tenant_a_token, tenant_b_token, db_connection
):
    with db_connection.cursor() as cursor:
        cursor.execute("SET row_security = on")
        cursor.execute("SET app.current_tenant = 'tenant-b'")
        cursor.execute(
            "UPDATE entities SET name = %s WHERE id = %s",
            ("hacked-name", entity_id)
        )
        update_count = cursor.rowcount
        # Should affect 0 rows due to RLS
        assert update_count == 0
```

## Graph Query Filtering (Neo4j)

Layer 3 enforces tenant isolation in Cypher queries via parameterized `$tenant_id` bindings.

### Cypher Query Patterns

```cypher
-- Secure: parameterized tenant_id
MATCH (n:Entity {tenant_id: $tenant_id})
WHERE n.id = $entity_id
RETURN n

-- Insecure (BLOCKED by semgrep): direct interpolation
MATCH (n:Entity {tenant_id: 'tenant-a'})
RETURN n
```

### Semgrep Enforcement

`.semgrep/cypher-dynamic-guard.yml` blocks dynamic Cypher construction:

| Rule | Severity | Blocks |
|---|---|---|
| `cypher-dynamic-label-injection` | ERROR | f-string label interpolation in MATCH/CREATE |
| `cypher-dynamic-rel-type-injection` | ERROR | f-string relationship type interpolation |
| `cypher-dynamic-where-clause` | WARNING | String-joined WHERE clauses |
| `cypher-dynamic-set-clause` | WARNING | String-joined SET clauses |

Safe dynamic patterns must be annotated with `# cypher-dynamic-safe: <reason>`.

### Direct Mutation Audit

`.semgrep/block-direct-mutation.yml` blocks direct `MERGE`/`CREATE`/`DELETE` on tenant-owned labels outside `AuditedGraphMutation`:

```yaml
rules:
  - id: block-direct-graph-mutation
    message: |
      Direct Cypher MERGE/CREATE/DELETE on tenant-owned labels must go through
      AuditedGraphMutation. This bypasses tenant isolation, audit logging, and metrics.
    severity: ERROR
    patterns:
      - pattern-regex: '(MERGE|CREATE|DELETE).*\{.*tenant_id'
      - pattern-not-regex: 'AuditedGraphMutation'
```

### Neo4j Tenant Query Tests

`tests/security/test_neo4j_tenant_query_enforcement.py` verifies:
- Entity detail queries include `tenant_id`
- Batch operations pass `tenant_id` to helpers
- Source contains ≥ 10 tenant-scoped MATCH patterns
- Missing tenant context fails closed with explicit error

## Cross-Tenant Access Prevention

### API-Level Prevention

| Attack Vector | Defense | Test |
|---|---|---|
| Tenant ID header spoofing | JWT claim precedence | `test_jwt_tenant_claim_takes_precedence` |
| Tenant ID in request body | Ignored; authenticated context used | `test_tenant_isolation_in_graph_queries` |
| IDOR (sequential ID enumeration) | UUIDv4 IDs only | `test_idor_prevention_via_uuid_randomization` |
| Cross-tenant JWT | Signature validation rejects tampered claims | `test_modified_tenant_claim_rejected` |
| Admin endpoint access by standard user | RBAC 403 | `test_standard_user_blocked_from_admin_endpoint` |

### Concurrent Isolation

`tests/security/test_tenant_isolation.py` includes concurrent tests:

```python
async def test_concurrent_bulk_reads_maintain_isolation(self, client, tenant_a_token, tenant_b_token):
    # 50 concurrent requests alternating between tenants
    tasks = []
    for i in range(25):
        tasks.append(bulk_read_request(tenant_a_token, "tenant-a"))
        tasks.append(bulk_read_request(tenant_b_token, "tenant-b"))
    results = await asyncio.gather(*tasks, return_exceptions=True)
    # Verify each response only contains data for its respective tenant
```

## Cache Isolation (Redis)

Redis cache keys are prefixed with the tenant ID to prevent cross-tenant cache leakage:

```python
# Secure: tenant-prefixed cache key
cache_key = f"tenant:{tenant_id}:entities:{entity_id}"

# Cache invalidation only affects requesting tenant's keys
```

Tests in `tests/security/test_tenant_isolation.py` verify that:
- Cache keys include the tenant prefix
- Cross-tenant cache reads via API are blocked
- Cache invalidation respects tenant boundaries

## Tenant Isolation Tests

The security suite includes a dedicated tenant isolation manifest:

| Test File | Coverage |
|---|---|
| `test_tenant_boundary_fails_closed.py` | Missing tenant context rejection |
| `test_cross_tenant_api.py` | API-level cross-tenant reads/writes |
| `test_cross_tenant_write.py` | Write-side isolation |
| `test_cross_tenant_jwt.py` | JWT tampering for cross-tenant access |
| `test_cross_layer_tenant.py` | Layer-to-layer tenant propagation |
| `test_cross_layer_tenant_isolation_matrix.py` | Matrix of cross-layer isolation scenarios |
| `test_graph_tenant_hostile_regression.py` | Neo4j hostile tenant regression |
| `test_hostile_tenant_e2e_matrix.py` | End-to-end hostile tenant journeys |
| `test_neo4j_cross_tenant_write_isolation.py` | Graph write isolation |
| `test_models_cross_tenant_isolation.py` | Model-level isolation |
| `test_formula_governance_cross_tenant_isolation.py` | Formula cross-tenant boundaries |
| `test_benchmarks_cross_tenant_isolation.py` | Benchmark cross-tenant boundaries |

Run the full suite:

```bash
pytest tests/security/test_tenant_isolation.py
pytest tests/security/test_cross_layer_tenant_isolation_matrix.py
pytest tests/security/test_hostile_tenant_e2e_matrix.py
```

## What to Audit When Changing Repository Code

Before modifying any repository, service, or database access layer:

- [ ] Confirm `tenant_id` is extracted from authenticated context (`ctx.tenant_id`), not request body or headers
- [ ] Confirm `tenant_id` is passed to all repository/service methods
- [ ] Confirm queries filter by `tenant_id` (SQL `WHERE tenant_id = ...` or Cypher `{tenant_id: $tenant_id}`)
- [ ] Confirm writes persist tenant ownership
- [ ] Confirm RLS policies apply to new tables (add `tenant_id` NOT NULL + RLS policy)
- [ ] Confirm tests cover hostile cross-tenant access (Tenant A trying to read Tenant B)
- [ ] Confirm cache keys include tenant prefix
- [ ] Confirm background jobs (Celery) set `SET LOCAL app.tenant_id` before DB operations
- [ ] Confirm Neo4j mutations go through `AuditedGraphMutation`
- [ ] Run `pytest tests/security/test_tenant_isolation.py` and related files

## Common Anti-Patterns to Avoid

| Anti-Pattern | Why It's Dangerous | Replacement |
|---|---|---|
| `tenant_id = request.json().get("tenant_id")` | Attacker can supply any tenant ID | `tenant_id = ctx.tenant_id` |
| `X-Tenant-ID` header outside auth middleware | Header spoofing | JWT claim precedence in middleware |
| Raw SQL with f-string tenant_id | SQL injection + bypass | Parameterized queries + RLS |
| Direct Cypher `MERGE`/`CREATE`/`DELETE` | Bypasses audit and tenant isolation | `AuditedGraphMutation.write_node()` |
| Missing `tenant_id` in cache key | Cross-tenant cache leakage | `tenant:{tenant_id}:...` prefix |
| Background job without `SET LOCAL` | RLS bypass in Celery tasks | Explicit tenant context in task payload |
| `get_db()` without tenant context | No RLS enforcement | `get_db_from_context(ctx)` |
| Using `organization_id` instead of `tenant_id` | Column name drift | Standardize on `tenant_id` |

## Validation Commands

```bash
# Tenant isolation suite
pytest tests/security/test_tenant_isolation.py -v

# Cross-layer matrix
pytest tests/security/test_cross_layer_tenant_isolation_matrix.py -v

# Neo4j-specific enforcement
pytest tests/security/test_neo4j_tenant_query_enforcement.py -v
pytest tests/security/test_neo4j_cross_tenant_write_isolation.py -v

# Graph hostile regression
pytest tests/security/test_graph_tenant_hostile_regression.py -v

# Model and formula isolation
pytest tests/security/test_models_cross_tenant_isolation.py -v
pytest tests/security/test_formula_governance_cross_tenant_isolation.py -v

# RLS static check
pytest tests/security/test_rls_enforcement.py -v

# Boundary static check (blocks header-based tenant inference)
pytest tests/security/test_boundary_check_static.py -v
```
