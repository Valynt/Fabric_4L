"""Tenant management API endpoints.

Task 3: Multi-Tenancy Hardening - Tenant Provisioning Automation

Provides admin endpoints for tenant lifecycle management:
- POST /v1/tenants/provision - Create new tenant with admin user
- GET /v1/tenants/{tenant_id} - Get tenant details
- GET /v1/tenants - List all tenants (super-admin only)
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession
from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.dependencies import require_privileged_access

from ..database import get_db_from_context as get_db_session
from ..services.tenant_provisioning import (
    TenantProvisioningService,
    TenantProvisionRequest,
    TenantProvisionResult,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/tenants", tags=["Tenants"])


# ═══════════════════════════════════════════════════════════════════════════
# Request/Response Models
# ═══════════════════════════════════════════════════════════════════════════

class ProvisionTenantRequest(BaseModel):
    """Request to provision a new tenant."""
    
    tenant_name: str = Field(..., min_length=3, max_length=100, description="Tenant name")
    admin_email: EmailStr = Field(..., description="Admin user email")
    org_id: UUID | None = Field(None, description="Optional organization ID")
    isolation_tier: str = Field("shared", description="Isolation tier: shared, schema, or database")
    metadata: dict[str, Any] | None = Field(None, description="Optional metadata")
    
    class Config:
        json_schema_extra = {
            "example": {
                "tenant_name": "acme-corp",
                "admin_email": "admin@acme.com",
                "isolation_tier": "shared",
                "metadata": {
                    "industry": "technology",
                    "region": "us-west"
                }
            }
        }


class ProvisionTenantResponse(BaseModel):
    """Response from tenant provisioning."""
    
    tenant_id: UUID
    admin_user_id: UUID
    admin_temp_password: str | None = Field(
        None,
        description=(
            "One-time temporary password for initial admin login. "
            "Only returned on first successful provisioning and must be changed at first login."
        ),
    )
    created_at: str
    isolation_tier: str
    password_change_required: bool = Field(
        True,
        description="Whether the admin must rotate credentials at first login.",
    )
    status: str = Field(..., description="success, partial, or failed")
    errors: list[str] | None = None
    message: str = Field(..., description="Human-readable status message")


class TenantSummary(BaseModel):
    """Summary information about a tenant."""
    
    tenant_id: UUID
    tenant_name: str
    isolation_tier: str
    created_at: str
    user_count: int = 0
    entity_count: int = 0


# Fixed allowlist of tables that may hold tenant-scoped entity rows. Any
# value used in raw SQL identifier position MUST come from this set so the
# f-string composition below cannot become an injection sink if the list is
# ever sourced from request input by a future contributor.
_TENANT_ENTITY_TABLES: frozenset[str] = frozenset({
    "entities",
    "knowledge_entities",
    "graph_entities",
    "crm_accounts",
    "accounts",
})


async def _count_tenant_entities(db_session: AsyncSession, tenant_id: UUID) -> int:
    """Count persisted tenant entities from available production tables.

    The tenant summary endpoint previously returned a hard-coded value because
    Neo4j-backed entity counting was not wired into this service. Returning a
    constant is misleading in production, so this helper queries real tenant-
    scoped tables when they exist and otherwise returns zero from an explicit
    database check. Missing optional tables are handled as absence of data, not
    as fabricated counts.
    """
    from sqlalchemy import text

    total = 0
    for table_name in _TENANT_ENTITY_TABLES:
        # Defense in depth: the identifier is interpolated into raw SQL, so
        # reject anything that is not a known table name even though the loop
        # currently iterates a hardcoded set.
        if table_name not in _TENANT_ENTITY_TABLES:
            raise ValueError(f"Refusing to query unknown table: {table_name!r}")

        exists_result = await db_session.execute(
            text("SELECT to_regclass(:table_name) IS NOT NULL"),
            {"table_name": table_name},
        )
        if not bool(exists_result.scalar()):
            continue

        count_result = await db_session.execute(
            text(f'SELECT COUNT(*) FROM "{table_name}" WHERE tenant_id = :tenant_id'),
            {"tenant_id": tenant_id},
        )
        total += int(count_result.scalar() or 0)
    return total


# ═══════════════════════════════════════════════════════════════════════════
# Endpoints
# ═══════════════════════════════════════════════════════════════════════════

@router.post(
    "/provision",
    response_model=ProvisionTenantResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Provision new tenant",
    description="""
    Provision a new tenant with automated setup:
    - Creates tenant record in PostgreSQL
    - Creates admin user with temporary password
    - Sets up RLS policies (for schema/database tiers)
    - Configures Neo4j constraints
    - Emits audit trail
    
    **Requires:** super_admin role + X-Privileged-Reason header
    
    **Idempotent:** Returns existing tenant if name already exists
    """,
)
async def provision_tenant(
    request: ProvisionTenantRequest,
    context: RequestContext = Depends(require_privileged_access()),
    db_session: AsyncSession = Depends(get_db_session),
) -> ProvisionTenantResponse:
    """Provision a new tenant with full automated setup.
    
    This endpoint requires super-admin privileges and a justification
    in the X-Privileged-Reason header for audit purposes.
    
    Args:
        request: Tenant provisioning request
        context: Request context (super-admin required)
        db_session: Database session
        
    Returns:
        ProvisionTenantResponse with tenant_id, admin credentials, and status
        
    Raises:
        HTTPException: 400 if validation fails, 500 if provisioning fails
    """
    logger.info(
        f"Provisioning tenant '{request.tenant_name}' by super_admin {context.user_id}"
    )
    
    try:
        # Create provisioning service
        service = TenantProvisioningService(db_session=db_session)
        
        # Convert request to service model
        provision_request = TenantProvisionRequest(
            tenant_name=request.tenant_name,
            admin_email=request.admin_email,
            org_id=request.org_id,
            isolation_tier=request.isolation_tier,
            metadata=request.metadata,
        )
        
        # Provision tenant
        result: TenantProvisionResult = await service.provision_tenant(provision_request)
        
        # Build response message
        if result.status == "success":
            message = f"Tenant '{request.tenant_name}' provisioned successfully"
        elif result.status == "partial":
            message = f"Tenant '{request.tenant_name}' provisioned with warnings"
        else:
            message = f"Tenant '{request.tenant_name}' provisioning failed"
        
        return ProvisionTenantResponse(
            tenant_id=result.tenant_id,
            admin_user_id=result.admin_user_id,
            admin_temp_password=result.admin_temp_password,
            created_at=result.created_at.isoformat(),
            isolation_tier=result.isolation_tier,
            password_change_required=result.password_change_required,
            status=result.status,
            errors=result.errors,
            message=message,
        )
        
    except ValueError as e:
        logger.warning(f"Tenant provisioning validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except RuntimeError as e:
        logger.error(f"Tenant provisioning failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Tenant provisioning failed: {str(e)}",
        )
    except Exception as e:
        logger.error(f"Unexpected error during tenant provisioning: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during tenant provisioning",
        )


@router.get(
    "/{tenant_id}",
    response_model=TenantSummary,
    summary="Get tenant details",
    description="""
    Get detailed information about a specific tenant.
    
    **Requires:** super_admin role or tenant_admin for the specific tenant
    """,
)
async def get_tenant(
    tenant_id: UUID,
    context: RequestContext = Depends(require_privileged_access()),
    db_session: AsyncSession = Depends(get_db_session),
) -> TenantSummary:
    """Get tenant details by ID.
    
    Args:
        tenant_id: Tenant UUID
        context: Request context
        db_session: Database session
        
    Returns:
        TenantSummary with tenant information
        
    Raises:
        HTTPException: 404 if tenant not found
    """
    from sqlalchemy import text
    
    # Query tenant
    query = text("""
        SELECT id, name, isolation_tier, created_at
        FROM tenants
        WHERE id = :tenant_id
    """)
    
    result = await db_session.execute(query, {"tenant_id": tenant_id})
    row = result.fetchone()
    
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant {tenant_id} not found",
        )
    
    # Get user count
    user_count_query = text("""
        SELECT COUNT(*) FROM users WHERE tenant_id = :tenant_id
    """)
    user_count_result = await db_session.execute(user_count_query, {"tenant_id": tenant_id})
    user_count = user_count_result.scalar() or 0
    
    entity_count = await _count_tenant_entities(db_session, row[0])

    return TenantSummary(
        tenant_id=row[0],
        tenant_name=row[1],
        isolation_tier=row[2],
        created_at=row[3].isoformat(),
        user_count=user_count,
        entity_count=entity_count,
    )


@router.get(
    "",
    response_model=list[TenantSummary],
    summary="List all tenants",
    description="""
    List all tenants in the system.
    
    **Requires:** super_admin role
    """,
)
async def list_tenants(
    context: RequestContext = Depends(require_privileged_access()),
    db_session: AsyncSession = Depends(get_db_session),
    limit: int = 100,
    offset: int = 0,
) -> list[TenantSummary]:
    """List all tenants (super-admin only).
    
    Args:
        context: Request context (super-admin required)
        db_session: Database session
        limit: Maximum number of results
        offset: Pagination offset
        
    Returns:
        List of TenantSummary objects
    """
    from sqlalchemy import text
    
    query = text("""
        SELECT id, name, isolation_tier, created_at
        FROM tenants
        ORDER BY created_at DESC
        LIMIT :limit OFFSET :offset
    """)
    
    result = await db_session.execute(query, {"limit": limit, "offset": offset})
    rows = result.fetchall()
    
    tenants = []
    for row in rows:
        # Get user count for each tenant
        user_count_query = text("""
            SELECT COUNT(*) FROM users WHERE tenant_id = :tenant_id
        """)
        user_count_result = await db_session.execute(user_count_query, {"tenant_id": row[0]})
        user_count = user_count_result.scalar() or 0
        
        entity_count = await _count_tenant_entities(db_session, row[0])

        tenants.append(TenantSummary(
            tenant_id=row[0],
            tenant_name=row[1],
            isolation_tier=row[2],
            created_at=row[3].isoformat(),
            user_count=user_count,
            entity_count=entity_count,
        ))
    
    return tenants
