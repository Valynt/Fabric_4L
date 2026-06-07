---
status: active
last_reviewed: 2026-06-07
owner: platform-team
---

# Tenancy

Every data read and write in Fabric4L is scoped by tenant. This page describes the multi-tenant isolation strategy, how tenant context flows through requests, and the database-level and graph-level enforcement mechanisms.

<span class="vp-badge vp-badge--role">Developer</span>
<span class="vp-badge vp-badge--role">Admin</span>

## Multi-tenant architecture overview

Fabric4L uses a **shared-schema** model with mandatory tenant columns and PostgreSQL Row-Level Security (RLS). Neo4j uses composite unique constraints on `(id, tenant_id)`.

| Tier | Isolation model | Status |
|------|-----------------|--------|
| shared (default) | Shared schema + RLS | **Enforced Canon** |
| dedicated | Dedicated schema per tenant | Experimental |
| enterprise | Dedicated database instance | Experimental |

!!! note "Target architecture"
    `TenantAwarePool` and tiered isolation are preserved as experimental target architecture in `examples/experimental/tenant-aware-pool/`. They are not enforced canon.

## Tenant context in requests

Tenant context is established by the auth middleware and treated as immutable for the lifetime of the request.

| Field | Type | Description |
|-------|------|-------------|
| `tenant_id` | UUIDv4 | The owning tenant |
| `tenant_tier` | `shared` \| `dedicated` \| `enterprise` | Tenant isolation tier |
| `region` | string | Deployment region |
| `issued_at` | timestamp | Context creation time |
| `scope` | string | Access scope (e.g., `admin`, `read_only`) |

Access pattern:

```python
from value_fabric.shared.identity.context import getTenantContext

ctx = getTenantContext()
if ctx is None:
    raise TenantContextMissing()

tenant_id = ctx.tenant_id
```

!!! warning "Anti-pattern: parameter pollution"
    Passing `tenant_id` as an explicit function parameter through service layers is deprecated. Use the request-scoped context instead.

## Database-level isolation (PostgreSQL)

All tenant-scoped tables have:

1. A `tenant_id` column with `NOT NULL` constraint
2. An RLS policy using `current_setting('app.tenant_id', true)`

### Setting tenant context per transaction

```python
# FastAPI dependency
from shared.identity.dependencies import get_db_from_context

async def get_db_from_context():
    ctx = getTenantContext()
    async with db_session() as session:
        await session.execute(
            text("SET LOCAL app.tenant_id = :tenant_id"),
            {"tenant_id": str(ctx.tenant_id)}
        )
        yield session
```

### RLS policy expression

```sql
CREATE POLICY tenant_isolation ON entities
    USING (tenant_id::text = current_setting('app.tenant_id', true));
```

The `true` flag returns an empty string if the setting is missing, which causes the policy to return no rows (fail-safe).

### Admin bypass

Cross-tenant admin queries use `SET LOCAL app.tenant_id = ''` with a dedicated `admin_role` or `system_role`. This is audited and rate-limited.

## Graph-level isolation (Neo4j)

All Neo4j nodes and relationships include a `tenant_id` property. Composite unique constraints on `(id, tenant_id)` allow the same `id` to exist across different tenants.

```cypher
// Parameterized query with tenant filter
MATCH (n:Capability {tenant_id: $tenant_id})
WHERE n.id = $entity_id
RETURN n
```

!!! tip "Always parameterize Cypher"
    Never interpolate `tenant_id` into Cypher strings. Use parameterized queries so the query plan cache remains effective and injection is impossible.

## Preferred patterns for tenant scoping

### Correct pattern

```python
tenant_id = ctx.tenant_id
repo.method(..., tenant_id=tenant_id)
```

### Incorrect patterns

```python
# Do not read tenant ID from request body without validation
tenant_id = request.json()["tenant_id"]

# Do not pass tenant_id through every service layer explicitly
def service_call(tenant_id: UUID, ...): ...
```

## Validation

```bash
# Run tenant isolation tests
make gate-tenant-isolation

# Run hostile tenant security suite
pytest tests/security/test_hostile_tenant_e2e_matrix.py -v

# Run tenancy-specific tests
pnpm test:tenancy

# Check for legacy tenant dependency imports
make check-layer3-tenant-dependency-imports
```

## Related pages

- [Authentication](./auth.md) — How tenant_id is extracted from identity tokens
- [Data Flow](./data-flow.md) — Tenant propagation across queues and service calls
- `docs/explanations/adr/ADR-003-neo4j-pgvector-hybrid-graph-database.md`
