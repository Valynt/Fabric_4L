# Multi-Tenancy in Fabric 4L

This document describes Fabric 4L's multi-tenant architecture, built on PostgreSQL Row-Level Security (RLS) with a future-ready isolation tier system.

## Overview

Fabric 4L uses a **shared schema with RLS** model for tenant isolation. Each tenant's data is logically separated at the database level using PostgreSQL's Row-Level Security policies, ensuring strong isolation guarantees without the operational complexity of schema-per-tenant or database-per-tenant approaches.

### Key Design Decisions

| Aspect | Decision | Rationale |
|--------|----------|-----------|
| Isolation Model | RLS-based shared schema | Strong guarantees, operational simplicity |
| Tenant ID | UUID in `app.tenant_id` session variable | Standard PostgreSQL RLS mechanism |
| Future Tiers | Schema & Database tiers planned | Migration path without re-architecture |
| Audit | Dedicated history table for tier changes | Governance and compliance requirements |

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        API Layer                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │   JWT Auth  │  │  API Keys   │  │  Service Accounts   │  │
│  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘  │
│         └─────────────────┴────────────────────┘            │
│                          │                                   │
│                   ┌────────▼────────┐                         │
│                   │ RequestContext  │                         │
│                   │  - tenant_id    │                         │
│                   │  - isolation_tier│                        │
│                   └────────┬────────┘                         │
└────────────────────────────┼─────────────────────────────────┘
                             │
┌────────────────────────────┼─────────────────────────────────┐
│                    Database Layer                            │
│                            │                                 │
│              ┌─────────────▼─────────────┐                   │
│              │  SET LOCAL app.tenant_id   │                   │
│              │       = 'tenant-uuid'      │                   │
│              └─────────────┬─────────────┘                    │
│                            │                                 │
│     ┌──────────────────────┼──────────────────────┐          │
│     │           PostgreSQL RLS Policies          │          │
│     │  ┌────────────────────────────────────────┐  │          │
│     │  │ CREATE POLICY tenant_isolation ON    │  │          │
│     │  │   accounts FOR ALL                     │  │          │
│     │  │   USING (tenant_id = current_setting( │  │          │
│     │  │     'app.tenant_id')::UUID);          │  │          │
│     │  └────────────────────────────────────────┘  │          │
│     └──────────────────────────────────────────────┘          │
│                            │                                 │
│              ┌─────────────▼─────────────┐                   │
│              │    Tenant Data Partition   │                   │
│              │  (transparently isolated)  │                   │
│              └───────────────────────────┘                    │
└─────────────────────────────────────────────────────────────┘
```

## Tenant Context Propagation

### JWT Token Claims

Tenant context is primarily extracted from JWT tokens. See [token-contract.md](./token-contract.md) for full claim specification.

```json
{
  "sub": "user-uuid",
  "tenant_id": "tenant-uuid",
  "org_id": "org-uuid",
  "tenant_role": "value_consultant",
  "isolation_tier": "shared",
  "roles": ["tenant_admin"],
  "scp": ["read", "write"]
}
```

### RequestContext

The `RequestContext` dataclass carries tenant information throughout the request lifecycle:

```python
@dataclass
class RequestContext:
    tenant_id: UUID | None = None
    user_id: UUID | None = None
    org_id: UUID | None = None          # Organization hierarchy
    tenant_role: str | None = None      # Role within tenant
    isolation_tier: str = "shared"      # shared | schema | database
    auth_source: str = "unknown"        # jwt_claim | api_key | service_account
    service_account_id: UUID | None = None
    service_account_scopes: list[str] = field(default_factory=list)
```

### Middleware Integration

The `GovernanceMiddleware` extracts tenant context and attaches it to the request:

```python
# FastAPI dependency to get context
async def get_request_context(request: Request) -> RequestContext:
    return getattr(request.state, "context", RequestContext())
```

## Database Session Setup

### Standard Pattern (RLS-enforced)

For most endpoints, use `get_db_from_context()` which:
1. Extracts tenant_id from RequestContext
2. Validates the tenant context is present
3. Sets `SET LOCAL app.tenant_id` for RLS

```python
from value_fabric.layer4_agents.src.database import get_db_from_context
from shared.identity.dependencies import get_request_context

@router.get("/accounts/{id}")
async def get_account(
    id: UUID,
    db: AsyncSession = Depends(get_db_from_context),
    context: RequestContext = Depends(get_request_context),
):
    # Database session automatically has RLS tenant context
    account = await db.get(Account, id)
    return account
```

### Mandatory Tenant Context

Require explicit tenant context for sensitive operations:

```python
from shared.identity.dependencies import require_tenant_context

@router.post("/sensitive-operation")
async def sensitive_op(
    context: RequestContext = Depends(require_tenant_context),
    db: AsyncSession = Depends(get_db_from_context),
):
    # Fails fast with 400 if tenant context missing
    ...
```

### Super-Admin Bypass

For cross-tenant administrative operations:

```python
from shared.identity.dependencies import require_privileged_access
from value_fabric.layer4_agents.src.database import get_db_with_optional_tenant

@router.get("/admin/all-tenants")
async def get_all_tenants(
    context: RequestContext = Depends(require_privileged_access()),
    db: AsyncSession = Depends(get_db_with_optional_tenant),
):
    # Requires X-Privileged-Reason header for audit
    # Bypasses tenant context (empty tenant_id for RLS)
    ...
```

## Layer 3 route import inventory (as of 2026-05-19)

Static inventory command:

```bash
rg "dependencies_tenant(_secured)?" services/layer3-knowledge/src/api/routes -n
```

Current state: all Layer 3 route modules import the secured wrapper, and no route modules import the legacy compatibility shim.

## Layer 3 Neo4j Tenant Dependency

Layer 3 Neo4j route access has one approved dependency module (single canonical
route dependency):
`services/layer3-knowledge/src/api/dependencies_tenant_secured.py`. Route code must
import `Neo4jTenantSession`, `get_neo4j_with_tenant`, or
`create_neo4j_tenant_session` from that module so every Neo4j operation is routed
through `Neo4jTenantSessionSecured` with query validation and tenant-parameter
force injection.

The legacy `services/layer3-knowledge/src/api/dependencies_tenant.py` module is a
compatibility shim only. It logs a deprecation warning on import and is scheduled
for hard removal on **2026-09-30**. New imports of that legacy module are blocked
by `python scripts/ci/check_layer3_legacy_tenant_dependency_imports.py` in CI.

Approved Layer 3 route import footprint (secured-only):

- `services/layer3-knowledge/src/api/routes/benchmarks.py`
- `services/layer3-knowledge/src/api/routes/calculators.py`
- `services/layer3-knowledge/src/api/routes/entities.py`
- `services/layer3-knowledge/src/api/routes/formula_governance.py`
- `services/layer3-knowledge/src/api/routes/formulas.py`
- `services/layer3-knowledge/src/api/routes/knowledge.py`
- `services/layer3-knowledge/src/api/routes/models_router.py`
- `services/layer3-knowledge/src/api/routes/signals.py`
- `services/layer3-knowledge/src/api/routes/variables.py`

## Isolation Tiers

### Current: Shared Tier

All tenants share database tables with RLS policies enforcing data separation.

**Pros:**
- Single connection pool
- Simple schema migrations
- No operational complexity

**Cons:**
- All eggs in one database
- Limited blast radius isolation

### Future: Schema Tier

Each tenant gets a dedicated PostgreSQL schema within the shared database.

**Pros:**
- Better isolation than RLS
- Schema-level resource limits possible
- Easier per-tenant migrations

**Cons:**
- Connection pool complexity
- Cross-tenant queries harder

### Future: Database Tier

Each tenant gets a dedicated PostgreSQL database (possibly on separate instances).

**Pros:**
- Maximum isolation
- Independent scaling
- Geographic data residency

**Cons:**
- Connection management complexity
- Higher operational overhead

### Tier Migration

When changing tiers, use the dedicated service function:

```python
from value_fabric.layer4_agents.src.tenants.service import update_tenant_isolation_tier

await update_tenant_isolation_tier(
    db,
    tenant_id,
    "schema",  # New tier
    changed_by=user_id,
    reason="Compliance requirement - dedicated schema",
    change_source="admin",
    request_id=request_id,
)
```

Changes are logged to `tenant_isolation_tier_history` table for audit.

## Testing Patterns

### Unit Tests

Test RequestContext behavior:

```python
def test_request_context_isolation_tier_defaults_to_shared():
    ctx = RequestContext()
    assert ctx.isolation_tier == "shared"
```

### Integration Tests

Test cross-tenant denial:

```python
@pytest.mark.asyncio
async def test_cannot_access_other_tenant_data():
    tenant_a, tenant_b = create_test_tenants()

    # Create data in tenant_a
    async with db_session(tenant_id=tenant_a) as db:
        await create_account(db, tenant_a, "Test Account")

    # Query with tenant_b context should return no results
    async with db_session(tenant_id=tenant_b) as db:
        accounts = await list_accounts(db)
        assert len(accounts) == 0  # RLS prevents access
```

### API Tests

Test tenant context validation:

```python
@pytest.mark.asyncio
async def test_api_rejects_missing_tenant_context():
    response = await client.get(
        "/accounts",
        headers={"Authorization": "Bearer invalid_token_no_tenant"}
    )
    assert response.status_code == 400
    assert "Tenant context required" in response.json()["detail"]
```

## Security Considerations

### RLS Policy Requirements

All tables with tenant data must have RLS policies:

```sql
-- Enable RLS
ALTER TABLE accounts ENABLE ROW LEVEL SECURITY;

-- Create tenant isolation policy
CREATE POLICY tenant_isolation ON accounts
    FOR ALL
    USING (tenant_id = current_setting('app.tenant_id')::UUID);

-- Super-admin bypass (optional)
CREATE POLICY super_admin_bypass ON accounts
    FOR ALL
    USING (current_setting('app.tenant_id') = '');
```

### Privileged Access Audit

All super-admin cross-tenant access is logged:

```python
# Logs: "Privileged access by super_admin: user=X, tenant=Y, reason=Z"
# Emits audit event: AuditAction.TENANT_CONTEXT_SET with bypass=True
```

### Tenant Resolution Audit

Every request has its tenant resolution logged:

```python
# Emits: AuditAction.TENANT_RESOLVED
# Details: resolution_source, tenant_id, auth_method, outcome
```

## Migration Roadmap

### Phase 1: Shared (Current)
✅ RLS-based isolation
✅ RequestContext standardization
✅ Audit logging

### Phase 2: Schema (Future)
⬜ Tier-aware connection routing
⬜ Schema provisioning automation
⬜ Cross-schema query utilities

### Phase 3: Database (Future)
⬜ Multi-database connection pools
⬜ Database provisioning pipeline
⬜ Geographic data residency

## References

- [Token Contract](./token-contract.md) - JWT claim specification
- `shared/identity/context.py` - RequestContext definition
- `shared/identity/middleware.py` - GovernanceMiddleware
- `services/layer4-agents/src/database.py` - DB session management
- `services/layer4-agents/src/tenants/models/` - Tenant models
