# Fabric 4L Tenant Management — Phase 1: RLS Hardening & Tenant Registry Enhancement

Strengthen existing RLS-based tenant isolation, normalize naming inconsistencies, and enhance tenant lifecycle management while keeping schema-per-tenant as a future tier option.

---

## 1. Objective

Phase 1 focuses on hardening the existing **Row-Level Security (RLS)** tenant isolation strategy that is currently mature and operational. This phase:

1. Normalizes column naming (`organization_id` → `tenant_id`)
2. Implements tenant status lifecycle (pending → active → suspended → deleted)
3. Enhances RLS policies for complete table coverage
4. Strengthens tenant context validation
5. Creates the foundation for automated provisioning (Phase 2)

The existing `isolation_tier` field in the Tenant model already supports future migration to schema-per-tenant. This remains a Phase 4+ consideration.

---

## 2. Current State Audit

### 2.1 Existing Tenant Infrastructure

| Component | File | Status | Notes |
|-----------|------|--------|-------|
| Tenant Model | `layer4-agents/src/tenants/models/tenant.py` | ✅ Complete | Has `isolation_tier` field (shared/schema/database) |
| RLS Session Manager | `layer4-agents/src/database.py` | ✅ Mature | Fail-safe validation, tier-aware routing framework |
| RequestContext | `shared/identity/context.py` | ✅ Complete | Multi-tier support, audit integration |
| OIDC Client | `shared/identity/oidc.py` | ✅ Mature | Generic OIDC, JWKS validation, PKCE support |
| GovernanceMiddleware | `shared/identity/middleware.py` | ✅ Complete | JWT/API key resolution, role mapping |
| Infisical Config | `.infisical.json` | ✅ Configured | Multi-environment secret paths |

### 2.2 Naming Inconsistencies

| Layer | Table | Current Column | Target Column |
|-------|-------|---------------|---------------|
| Layer 1 | `scraping_targets` | `organization_id` | `tenant_id` |
| Layer 1 | `scraping_jobs` | `organization_id` | `tenant_id` |
| Layer 1 | `raw_content` | `organization_id` | `tenant_id` |
| Layer 1 | `extracted_data` | `organization_id` | `tenant_id` |
| Layer 5 | `truth_objects` | `organization_id` | `tenant_id` |
| Layer 5 | `truth_sources` | `organization_id` | `tenant_id` |
| Layer 5 | `model_versions` | `organization_id` | `tenant_id` |

### 2.3 Current RLS Coverage

| Layer | Migration | Tables Covered |
|-------|-----------|----------------|
| Layer 1 | `004_add_rls_policies.py` | 8 tables |
| Layer 4 | `007_add_rls_policies.py` | 8 tables |
| Layer 5 | `002_add_rls_policies.py` + `003_add_model_registry.py` | 7 tables |

### 2.4 Tenant Status (Current)

The Tenant model has a `status` field but lacks lifecycle management:
- Current values: `active`, `suspended`, `deleted`
- Missing: Transition logic, suspension enforcement

---

## 3. Target Architecture

### 3.1 Tenant Status Lifecycle

```
┌─────────┐    register     ┌─────────┐    provision    ┌─────────┐
│  START  │ ─────────────→ │ PENDING │ ─────────────→ │ ACTIVE  │
└─────────┘                └─────────┘                └────┬────┘
                                                         │
                    ┌────────────────────────────────────┘
                    │ suspend
                    ▼
              ┌───────────┐    reactivate    ┌─────────┐
              │ SUSPENDED │ ←─────────────── │         │
              └─────┬─────┘                  │         │
                    │      delete            │         │
                    └──────────────────────→ │ DELETED │
                                             └─────────┘
```

**Transitions:**
- `PENDING` → `ACTIVE`: After successful provisioning (Phase 2)
- `ACTIVE` → `SUSPENDED`: Non-payment, policy violation, admin action
- `SUSPENDED` → `ACTIVE`: Admin reactivation
- `ACTIVE|SUSPENDED` → `DELETED`: Admin deletion (soft delete)

### 3.2 Enhanced Request Flow

```
Request → GovernanceMiddleware → Tenant Status Check → RLS Context Set → Handler
                ↓                        ↓
         Resolve tenant_id          If suspended → 403 Forbidden
         from JWT/API key
```

---

## 4. Task Breakdown

### Task 1.1: Layer 1 Column Rename Migration
**Estimated Effort:** 4 hours
**Priority:** P1

Create migration to rename `organization_id` to `tenant_id` in Layer 1.

**Migration File:** `services/layer1-ingestion/migrations/versions/006_rename_org_to_tenant.py`

```python
"""Rename organization_id to tenant_id in Layer 1 tables.

Revision ID: 006
Revises: 005_add_crawl_path_and_decisions.py
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision: str = '006'
down_revision: Union[str, None] = '005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLES = [
    'scraping_targets',
    'scraping_jobs',
    'raw_content',
    'extracted_data',
]

def upgrade() -> None:
    for table in TABLES:
        op.alter_column(
            table,
            'organization_id',
            new_column_name='tenant_id',
            existing_type=sa.UUID(),
            existing_nullable=False,
        )

def downgrade() -> None:
    for table in TABLES:
        op.alter_column(
            table,
            'tenant_id',
            new_column_name='organization_id',
            existing_type=sa.UUID(),
            existing_nullable=False,
        )
```

**Model Updates:**
- `services/layer1-ingestion/src/models.py`: Update all `organization_id` references

**Task Updates:**
- `services/layer1-ingestion/src/shared/tasks.py`: Update Celery task queries

---

### Task 1.2: Layer 5 Column Rename Migration
**Estimated Effort:** 3 hours
**Priority:** P1

Create migration to rename `organization_id` to `tenant_id` in Layer 5.

**Migration File:** `services/layer5-ground-truth/src/layer5_ground_truth/migrations/versions/004_rename_org_to_tenant.py`

```python
"""Rename organization_id to tenant_id in Layer 5 tables.

Revision ID: 004
Revises: 003_add_model_registry.py
"""
TABLES = [
    'truth_objects',
    'truth_sources',
    'validation_events',
    'maturity_history',
    'model_versions',
    'model_deployments',
    'model_evaluations',
]

# Same pattern as Task 1.1
```

**Model Updates:**
- `services/layer5-ground-truth/src/layer5_ground_truth/models.py`

---

### Task 1.3: Tenant Status Lifecycle Implementation
**Estimated Effort:** 6 hours
**Priority:** P0

Implement proper status lifecycle with transition validation.

**Modified File:** `services/layer4-agents/src/tenants/models/tenant.py`

Add to existing Tenant class:

```python
from enum import Enum

class TenantStatus(str, Enum):
    PENDING = "pending"      # Awaiting provisioning
    ACTIVE = "active"        # Fully operational
    SUSPENDED = "suspended"  # Access blocked
    DELETED = "deleted"      # Soft deleted

# Update Tenant.status field
status: Mapped[str] = mapped_column(
    String(20),
    nullable=False,
    default=TenantStatus.PENDING.value,  # Changed from "active"
    comment="Lifecycle status",
)

# Add transition tracking
status_changed_at: Mapped[datetime | None] = mapped_column(
    DateTime(timezone=True),
    nullable=True,
)
status_reason: Mapped[str | None] = mapped_column(
    String(255),
    nullable=True,
    comment="Reason for last status change",
)

VALID_TRANSITIONS = {
    TenantStatus.PENDING: {TenantStatus.ACTIVE, TenantStatus.DELETED},
    TenantStatus.ACTIVE: {TenantStatus.SUSPENDED, TenantStatus.DELETED},
    TenantStatus.SUSPENDED: {TenantStatus.ACTIVE, TenantStatus.DELETED},
    TenantStatus.DELETED: set(),  # Terminal state
}

def can_transition_to(self, new_status: str) -> bool:
    """Check if status transition is valid."""
    current = TenantStatus(self.status)
    target = TenantStatus(new_status)
    return target in self.VALID_TRANSITIONS.get(current, set())

def transition_to(
    self,
    new_status: str,
    reason: str | None = None,
) -> None:
    """Transition to new status with validation."""
    if not self.can_transition_to(new_status):
        raise ValueError(
            f"Invalid transition: {self.status} → {new_status}"
        )
    self.status = new_status
    self.status_changed_at = datetime.now(UTC)
    self.status_reason = reason
```

**New File:** `services/layer4-agents/src/tenants/constants.py`

```python
"""Tenant management constants."""
from enum import Enum

class TenantStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DELETED = "deleted"

DEFAULT_TIER = "shared"
SCHEMA_PREFIX = "t_"
```

---

### Task 1.4: Suspended Tenant Enforcement
**Estimated Effort:** 3 hours
**Priority:** P0

Add middleware check to block suspended tenants.

**Modified File:** `packages/shared/src/value_fabric/shared/identity/middleware.py`

Add after tenant resolution:

```python
from fastapi import HTTPException, status
from layer4_agents.src.tenants.constants import TenantStatus

async def check_tenant_status(db_session, tenant_id: UUID) -> None:
    """Check if tenant is active, raise 403 if suspended."""
    result = await db_session.execute(
        select(Tenant.status).where(Tenant.id == tenant_id)
    )
    status = result.scalar()

    if status == TenantStatus.SUSPENDED.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant suspended. Contact support.",
        )
    elif status == TenantStatus.PENDING.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant pending activation. Complete onboarding.",
        )
    elif status == TenantStatus.DELETED.value:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )
```

Integrate into `GovernanceMiddleware`:

```python
# After resolving tenant_id from JWT/API key
if context.tenant_id:
    await check_tenant_status(db, context.tenant_id)
```

---

### Task 1.5: RLS Policy Audit & Enhancement
**Estimated Effort:** 4 hours
**Priority:** P1

Audit and complete RLS coverage across all layers.

**New Migration:** `services/layer4-agents/migrations/versions/012_add_missing_rls.py`

Check for uncovered tables and add RLS:

```python
"""Add RLS policies to any uncovered tables.

Revision ID: 012
"""
from alembic import op

# Tables to verify coverage
REQUIRED_TABLES = [
    'accounts',
    'account_contacts',
    'account_notes',
    'crm_sync_states',
    'feature_flags',
    'audit_events',
    'oidc_sessions',
    'model_registry',
    # Add any missing from new features
]

def upgrade() -> None:
    for table in REQUIRED_TABLES:
        # Check if policy exists, create if not
        op.execute(f"""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_policies
                    WHERE tablename = '{table}'
                    AND policyname = 'tenant_isolation_policy'
                ) THEN
                    CREATE POLICY tenant_isolation_policy ON {table}
                        USING (tenant_id::text = current_setting('app.tenant_id', true));
                END IF;
            END
            $$;
        """)

        # Enable RLS
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
```

---

### Task 1.6: Tenant Service Lifecycle Methods
**Estimated Effort:** 4 hours
**Priority:** P1

Add lifecycle management to tenant service.

**Modified File:** `services/layer4-agents/src/tenants/service.py`

```python
from .constants import TenantStatus
from shared.audit import emit_audit_event, AuditAction

class TenantService:
    """Enhanced tenant service with lifecycle management."""

    async def suspend_tenant(
        self,
        tenant_id: UUID,
        reason: str,
        actor_id: UUID,
    ) -> Tenant:
        """Suspend a tenant."""
        tenant = await self.get_tenant(tenant_id)
        tenant.transition_to(TenantStatus.SUSPENDED.value, reason)

        await emit_audit_event(
            action=AuditAction.TENANT_SUSPENDED,
            tenant_id=tenant_id,
            actor_id=actor_id,
            details={"reason": reason},
        )
        return tenant

    async def reactivate_tenant(
        self,
        tenant_id: UUID,
        reason: str,
        actor_id: UUID,
    ) -> Tenant:
        """Reactivate a suspended tenant."""
        tenant = await self.get_tenant(tenant_id)
        tenant.transition_to(TenantStatus.ACTIVE.value, reason)

        await emit_audit_event(
            action=AuditAction.TENANT_REACTIVATED,
            tenant_id=tenant_id,
            actor_id=actor_id,
            details={"reason": reason},
        )
        return tenant

    async def soft_delete_tenant(
        self,
        tenant_id: UUID,
        reason: str,
        actor_id: UUID,
    ) -> Tenant:
        """Soft delete a tenant."""
        tenant = await self.get_tenant(tenant_id)
        tenant.transition_to(TenantStatus.DELETED.value, reason)

        await emit_audit_event(
            action=AuditAction.TENANT_DELETED,
            tenant_id=tenant_id,
            actor_id=actor_id,
            details={"reason": reason},
        )
        return tenant
```

---

### Task 1.7: Provisioning Service Skeleton
**Estimated Effort:** 2 hours
**Priority:** P2

Create skeleton for Phase 2 provisioning.

**New File:** `services/layer4-agents/src/tenants/provisioning.py`

```python
"""Tenant provisioning service — Phase 1 skeleton for Phase 2 implementation."""
from dataclasses import dataclass
from enum import Enum
from uuid import UUID

class ProvisioningStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class ProvisioningState:
    tenant_id: UUID
    status: ProvisioningStatus
    step: str | None = None
    error: str | None = None

class TenantProvisioningService:
    """Service for automated tenant provisioning (Phase 2 implementation)."""

    async def provision_tenant(self, tenant_id: UUID) -> ProvisioningState:
        """Provision a new tenant.

        Phase 2 implementation will:
        1. Create Infisical secret path
        2. Seed default configuration
        3. Update tenant status to ACTIVE
        """
        # Skeleton for Phase 2
        raise NotImplementedError("Phase 2 implementation required")

    async def get_provisioning_status(
        self,
        tenant_id: UUID,
    ) -> ProvisioningState:
        """Get current provisioning status."""
        # Skeleton for Phase 2
        raise NotImplementedError("Phase 2 implementation required")
```

---

### Task 1.8: Update API Routes for Status Management
**Estimated Effort:** 3 hours
**Priority:** P1

Add tenant lifecycle endpoints.

**Modified File:** `services/layer4-agents/src/tenants/api/routes/tenants.py`

Add endpoints:

```python
from shared.identity.dependencies import require_super_admin

@router.post("/{tenant_id}/suspend")
async def suspend_tenant(
    tenant_id: UUID,
    request: SuspendTenantRequest,
    db: AsyncSession = Depends(get_db_from_context),
    context: RequestContext = Depends(require_super_admin()),
) -> TenantResponse:
    """Suspend a tenant (super_admin only)."""
    service = TenantService(db)
    tenant = await service.suspend_tenant(
        tenant_id, request.reason, context.user_id
    )
    return TenantResponse.from_model(tenant)

@router.post("/{tenant_id}/reactivate")
async def reactivate_tenant(
    tenant_id: UUID,
    request: ReactivateTenantRequest,
    db: AsyncSession = Depends(get_db_from_context),
    context: RequestContext = Depends(require_super_admin()),
) -> TenantResponse:
    """Reactivate a suspended tenant (super_admin only)."""
    service = TenantService(db)
    tenant = await service.reactivate_tenant(
        tenant_id, request.reason, context.user_id
    )
    return TenantResponse.from_model(tenant)
```

---

### Task 1.9: Test Updates
**Estimated Effort:** 6 hours
**Priority:** P1

Update tests for renamed columns and status lifecycle.

**Modified Files:**
- `services/layer4-agents/tests/test_tenant_isolation.py`
- `services/layer1-ingestion/tests/unit/test_celery_tasks.py`
- `tests/security/test_tenant_isolation.py`

**New Tests:**
- Status transition validation
- Suspended tenant blocking
- Column rename verification

---

## 5. Execution Order

| Step | Tasks | Dependencies |
|------|-------|--------------|
| 1 | Task 1.1, Task 1.2 | None (migrations first) |
| 2 | Task 1.3 | None |
| 3 | Task 1.6 | Task 1.3 |
| 4 | Task 1.4 | Task 1.3 |
| 5 | Task 1.8 | Task 1.3, Task 1.6 |
| 6 | Task 1.5 | None |
| 7 | Task 1.7 | None (skeleton) |
| 8 | Task 1.9 | All above |

---

## 6. Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| Column rename breaks Celery tasks | High | Comprehensive test updates; staging validation |
| Status check adds query overhead | Medium | Cache tenant status in Redis; refresh TTL |
| Migration rollback needed | Medium | Test downgrade paths; backup before deploy |
| Suspended tenant check bypass | Critical | Security review of middleware integration |

---

## 7. Rollback Strategy

If issues encountered:

1. **Column Renames:** Run migration downgrade scripts
2. **Status Check:** Feature flag to disable suspended check
3. **RLS Policies:** Migration includes policy removal

---

## 8. Acceptance Criteria

1. All `organization_id` columns renamed to `tenant_id` in Layers 1 and 5
2. Tenant status transitions validated (invalid transitions rejected)
3. Suspended tenants receive 403 with appropriate message
4. Pending tenants blocked with onboarding message
5. All tenant-scoped tables have RLS policies
6. Tenant service lifecycle methods emit audit events
7. All existing tests pass with updated column names
8. New tests for status lifecycle pass

---

## 9. File Inventory

| Action | File | Description |
|--------|------|-------------|
| **Create** | `layer1-ingestion/migrations/versions/006_rename_org_to_tenant.py` | Layer 1 column rename |
| **Create** | `layer5-ground-truth/.../migrations/versions/004_rename_org_to_tenant.py` | Layer 5 column rename |
| **Create** | `layer4-agents/migrations/versions/012_add_missing_rls.py` | RLS policy completion |
| **Create** | `layer4-agents/src/tenants/constants.py` | Tenant constants |
| **Create** | `layer4-agents/src/tenants/provisioning.py` | Provisioning skeleton |
| **Modify** | `layer4-agents/src/tenants/models/tenant.py` | Add lifecycle fields/methods |
| **Modify** | `layer4-agents/src/tenants/service.py` | Add lifecycle methods |
| **Modify** | `layer4-agents/src/tenants/api/routes/tenants.py` | Add status endpoints |
| **Modify** | `shared/identity/middleware.py` | Add status checks |
| **Modify** | `layer1-ingestion/src/models.py` | Update column references |
| **Modify** | `layer1-ingestion/src/shared/tasks.py` | Update Celery queries |
| **Modify** | `layer5-ground-truth/.../models.py` | Update column references |

---

## 10. Post-Phase 1 State

After Phase 1 completion:

- ✅ RLS-based isolation hardened and complete
- ✅ Tenant lifecycle management operational
- ✅ Column naming consistent across all layers
- ✅ Suspended/pending tenants properly blocked
- ✅ Schema-per-tenant remains a future option (`isolation_tier` field preserved)
- ✅ Ready for Phase 2 automated provisioning

---

## References

- `services/layer4-agents/src/database.py` — RLS session management
- `services/layer4-agents/src/tenants/models/tenant.py` — Tenant model
- `shared/identity/context.py` — RequestContext with isolation tiers
- `shared/identity/middleware.py` — GovernanceMiddleware
- `shared/identity/oidc.py` — Generic OIDC client (not Keycloak-specific)
