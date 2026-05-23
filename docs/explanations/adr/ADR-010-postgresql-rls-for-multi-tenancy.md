<!-- Migrated from services/ADRs/ during legacy path cleanup. -->

# ADR-010: PostgreSQL + RLS for Multi-Tenancy

**Status:** Accepted  
**Date:** April 2026  
**Authors:** Distinguished Engineering Team  
**Reviewers:** Security Architecture Committee

---

## Context

Value Fabric is a multi-tenant SaaS platform where:
- Each tenant's data must be strictly isolated
- Tenants share database infrastructure for cost efficiency
- Row-level security must be enforced at the database level
- Compliance requirements (SOC 2, GDPR) mandate tenant isolation

We evaluated:
1. **PostgreSQL with Row-Level Security (RLS)**
2. **Separate database per tenant**
3. **Separate schema per tenant**
4. **Application-level filtering only**

## Decision

We chose **PostgreSQL with Row-Level Security (RLS)** policies:

```sql
-- Enable RLS on tenant-scoped tables
ALTER TABLE accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE workflows ENABLE ROW LEVEL SECURITY;
ALTER TABLE formulas ENABLE ROW LEVEL SECURITY;

-- Create isolation policy
CREATE POLICY tenant_isolation ON accounts
    FOR ALL
    USING (tenant_id::text = current_setting('app.tenant_id', true));
```

## Rationale

### Comparison Matrix

| Criteria | PostgreSQL + RLS | Separate DB | Separate Schema | App-Level Only |
|----------|-----------------|-------------|-----------------|----------------|
| Security | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ |
| Cost Efficiency | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Operational Complexity | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| Query Performance | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Backup/Restore | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| Cross-Tenant Analytics | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

### Why PostgreSQL + RLS?

1. **Defense in Depth**: Database-enforced isolation even if application logic fails
   ```sql
   -- RLS prevents access regardless of application bugs
   SET LOCAL app.tenant_id = 'tenant-123';
   SELECT * FROM accounts;  -- Only sees tenant-123's data
   ```

2. **Cost Efficiency**: Single database cluster vs. hundreds of separate databases
   - Shared connection pool
   - Shared cache
   - Shared operational overhead

3. **Operational Simplicity**: Standard PostgreSQL operations
   - Single backup/restore process
   - Unified monitoring
   - Standard migrations with Alembic

4. **Compliance**: Database-level audit trail for access control

### Why Not Separate Database per Tenant?

- High operational overhead (connection management, backups, migrations)
- Resource fragmentation (some DBs idle, others overloaded)
- Complex cross-tenant analytics (federation required)
- Higher infrastructure costs

### Why Not Separate Schema per Tenant?

- Migration complexity (schema changes across N tenants)
- Connection pool inefficiency
- No significant security advantage over RLS
- Harder to maintain consistency

### Why Not Application-Level Only?

- Risk of developer error (forgetting `WHERE tenant_id = X`)
- No protection from direct database access
- Fails compliance audits requiring database-level controls
- Difficult to verify completeness

## Trade-offs

### Positive
- Strong security guarantee at database level
- Cost-efficient resource sharing
- Simplified operations
- Compliance-friendly audit trail

### Negative
- Single database becomes critical infrastructure
- Need for careful index design (tenant_id in all indexes)
- Complex backup for single tenant restore
- Query performance impact from RLS overhead

## Mitigations

| Risk | Mitigation |
|------|-----------|
| Single point of failure | PostgreSQL HA with streaming replication |
| Index performance | Include tenant_id in all indexes |
| Single tenant restore | Logical backups with tenant filtering |
| RLS overhead | Benchmark and optimize query plans |
| Tenant data export | Dedicated export API with filtering |

## Implementation

### Application-Level Tenant Context

```python
async def get_db_with_tenant(
    x_tenant_id: str = Header(..., alias="X-Tenant-ID")
) -> AsyncGenerator[AsyncSession, None]:
    """Database session with mandatory tenant context."""
    
    # Validate tenant ID
    if not is_valid_uuid(x_tenant_id):
        raise HTTPException(status_code=400, detail="Invalid tenant ID")
    
    async with async_session() as session:
        # SECURITY: Set tenant context for RLS
        await session.execute(
            text("SET LOCAL app.tenant_id = :tenant_id"),
            {"tenant_id": x_tenant_id}
        )
        
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

### RLS Policy Definitions

```sql
-- Tenant context helper
CREATE OR REPLACE FUNCTION get_current_tenant_id()
RETURNS TEXT AS $$
BEGIN
    RETURN current_setting('app.tenant_id', true);
EXCEPTION WHEN undefined_object THEN
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Isolation policies for each table
CREATE POLICY tenant_isolation_accounts ON accounts
    FOR ALL
    TO app_user
    USING (tenant_id::text = get_current_tenant_id());

CREATE POLICY tenant_isolation_workflows ON workflows
    FOR ALL
    TO app_user
    USING (tenant_id::text = get_current_tenant_id());

-- Admin bypass for support operations
CREATE ROLE vf_admin WITH LOGIN;
CREATE POLICY admin_bypass_accounts ON accounts
    FOR ALL
    TO vf_admin
    USING (true);
```

### Index Strategy

```sql
-- Include tenant_id in all indexes for partition pruning
CREATE INDEX idx_accounts_tenant_id ON accounts(tenant_id);
CREATE INDEX idx_accounts_tenant_lookup ON accounts(tenant_id, id);
CREATE INDEX idx_workflows_tenant_status ON workflows(tenant_id, status);

-- Composite index for common queries
CREATE INDEX idx_accounts_tenant_name ON accounts(tenant_id, name) 
INCLUDE (created_at, updated_at);
```

### Tenant Isolation Testing

```python
async def test_tenant_isolation():
    """Verify RLS prevents cross-tenant access."""
    
    # Create data for tenant A
    async with get_db_with_tenant("tenant-a") as db:
        account_a = Account(id=uuid4(), name="Account A", tenant_id="tenant-a")
        db.add(account_a)
        await db.commit()
    
    # Verify tenant A can see own data
    async with get_db_with_tenant("tenant-a") as db:
        result = await db.execute(select(Account))
        accounts = result.scalars().all()
        assert len(accounts) == 1
        assert accounts[0].name == "Account A"
    
    # Verify tenant B cannot see tenant A's data
    async with get_db_with_tenant("tenant-b") as db:
        result = await db.execute(select(Account))
        accounts = result.scalars().all()
        assert len(accounts) == 0  # RLS enforced!
    
    # Verify direct SQL without tenant context fails
    async with async_session() as db:
        # No SET LOCAL app.tenant_id
        result = await db.execute(select(Account))
        accounts = result.scalars().all()
        assert len(accounts) == 0  # Default deny!
```

## Consequences

### Accepted
- Need for strict tenant_id inclusion in all queries
- Performance overhead from RLS (minimal with proper indexing)
- Complexity of tenant context management

### Mitigated
- Developer errors via code review and integration tests
- Performance via composite indexes including tenant_id
- Context management via FastAPI dependencies

## Security Verification

```python
# Automated security tests
async def test_rls_security_matrix():
    """Matrix test for all RLS scenarios."""
    
    scenarios = [
        # (actor, action, resource, tenant, expected_result)
        ("tenant-a-user", "read", "tenant-a-account", "tenant-a", "allow"),
        ("tenant-a-user", "read", "tenant-b-account", "tenant-b", "deny"),
        ("tenant-a-user", "write", "tenant-a-account", "tenant-a", "allow"),
        ("tenant-a-user", "write", "tenant-b-account", "tenant-b", "deny"),
        ("admin", "read", "any-account", "any", "allow"),  # Admin bypass
        ("no-auth", "read", "any-account", "any", "deny"),
    ]
    
    for actor, action, resource, tenant, expected in scenarios:
        result = await attempt_access(actor, action, resource, tenant)
        assert result == expected, f"Failed: {actor} {action} {resource}"
```

## Related Decisions

- ADR-001: Multi-layer architecture
- ADR-002: Neo4j for knowledge graph (complementary, not competing)

---

**Last Updated:** April 21, 2026
