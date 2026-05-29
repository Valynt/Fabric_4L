from __future__ import annotations

from value_fabric.shared.error_handling.exceptions import ConflictError, NotFoundError, ServiceUnavailableError
"""Tenant management API routes (super_admin only).

POST   /v1/tenants                          — create tenant
GET    /v1/tenants                          — list tenants
GET    /v1/tenants/{tenant_id}              — get tenant
PATCH  /v1/tenants/{tenant_id}              — update tenant
DELETE /v1/tenants/{tenant_id}              — soft-delete tenant
POST   /v1/tenants/{tenant_id}/suspend      — suspend tenant
POST   /v1/tenants/{tenant_id}/activate     — activate tenant
POST   /v1/tenants/{tenant_id}/status       — change status with reason
"""


import logging
from uuid import UUID

logger = logging.getLogger(__name__)

from fastapi import APIRouter, Cookie, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.dependencies import require_authenticated, require_super_admin
from value_fabric.shared.identity.models import (
    TenantCreateRequest,
    TenantModel,
    TenantUpdateRequest,
)

from ....api.security.csrf import CSRF_COOKIE_NAME, validate_double_submit
from ....database import get_db_from_context
from ...service import (
    create_tenant,
    delete_tenant,
    get_tenant,
    list_tenants,
    update_tenant,
    update_tenant_status,
)


class StatusChangeRequest(BaseModel):
    """Request body for tenant status change endpoints."""
    reason: str | None = Field(None, description="Human-readable reason for the status change")
    changed_by: str | None = Field(None, description="User ID or service name initiating the change")


router = APIRouter(prefix="/tenants", tags=["Tenants"])


class CurrentTenantSettingsResponse(BaseModel):
    id: str
    name: str
    slug: str
    status: str
    tier_id: str
    settings: dict
    created_at: str


class CurrentTenantSettingsUpdate(BaseModel):
    settings: dict | None = None


class CurrentTenantSettingsUpdateResponse(BaseModel):
    id: str
    name: str
    settings: dict
    updated_at: str


@router.get('/current/settings', response_model=CurrentTenantSettingsResponse)
async def api_get_current_tenant_settings(
    db: AsyncSession = Depends(get_db_from_context),
    ctx: RequestContext = Depends(require_authenticated),
) -> CurrentTenantSettingsResponse:
    tenant = await get_tenant(db, ctx.tenant_id)
    if not tenant:
        raise NotFoundError(message = 'Tenant not found')
    settings = tenant.settings or {}
    tier_id = settings.get('tier_id', 'free')
    return CurrentTenantSettingsResponse(
        id=str(tenant.id),
        name=tenant.name,
        slug=tenant.slug,
        status=tenant.status,
        tier_id=tier_id,
        settings=settings,
        created_at=tenant.created_at.isoformat() if tenant.created_at else '',
    )


@router.patch('/current/settings', response_model=CurrentTenantSettingsUpdateResponse)
async def api_update_current_tenant_settings(
    update: CurrentTenantSettingsUpdate,
    db: AsyncSession = Depends(get_db_from_context),
    ctx: RequestContext = Depends(require_authenticated),
    _csrf_cookie: str | None = Cookie(default=None, alias=CSRF_COOKIE_NAME),
    _csrf_ok: None = Depends(validate_double_submit),
) -> CurrentTenantSettingsUpdateResponse:
    tenant = await get_tenant(db, ctx.tenant_id)
    if not tenant:
        raise NotFoundError(message = 'Tenant not found')

    current_settings = tenant.settings or {}
    if update.settings:
        allowed_fields = {
            'custom_branding',
            'notification_preferences',
            'webhook_url',
            'security',
            'feature_flags',
            'limits',
            'retention',
            'integrations_summary',
        }
        for key, value in update.settings.items():
            if key in allowed_fields:
                current_settings[key] = value

    updated = await update_tenant(
        db,
        ctx.tenant_id,
        TenantUpdateRequest(settings=current_settings),
    )
    if not updated:
        raise ServiceUnavailableError(message='Failed to update tenant settings')

    return CurrentTenantSettingsUpdateResponse(
        id=str(updated.id),
        name=updated.name,
        settings=updated.settings or {},
        updated_at=updated.updated_at.isoformat() if updated.updated_at else '',
    )


@router.post("", response_model=TenantModel, status_code=status.HTTP_201_CREATED)
async def api_create_tenant(
    request: TenantCreateRequest,
    _ctx=Depends(require_super_admin),
    db: AsyncSession = Depends(get_db_from_context),
) -> TenantModel:
    """Create a new tenant. Requires ``super_admin`` role."""
    try:
        return await create_tenant(db, request)
    except IntegrityError as exc:
        message = str(exc.orig if getattr(exc, "orig", None) is not None else exc)
        if "uix_tenant_slug" in message or "duplicate key value" in message and "slug" in message:
            raise ConflictError(message="Tenant slug already exists") from exc
        raise


@router.get("", response_model=list[TenantModel])
async def api_list_tenants(
    tenant_status: str | None = Query(None, alias="status"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    _ctx=Depends(require_super_admin),
    db: AsyncSession = Depends(get_db_from_context),
) -> list[TenantModel]:
    """List all tenants. Requires ``super_admin`` role."""
    return await list_tenants(db, status=tenant_status, limit=limit, offset=offset)


@router.get("/{tenant_id}", response_model=TenantModel)
async def api_get_tenant(
    tenant_id: UUID,
    _ctx=Depends(require_super_admin),
    db: AsyncSession = Depends(get_db_from_context),
) -> TenantModel:
    """Get a tenant by ID. Requires ``super_admin`` role."""
    tenant = await get_tenant(db, tenant_id)
    if not tenant:
        raise NotFoundError(message = str(f"Tenant {tenant_id} not found"))
    return tenant


@router.patch("/{tenant_id}", response_model=TenantModel)
async def api_update_tenant(
    tenant_id: UUID,
    request: TenantUpdateRequest,
    _ctx=Depends(require_super_admin),
    db: AsyncSession = Depends(get_db_from_context),
) -> TenantModel:
    """Update a tenant. Requires ``super_admin`` role."""
    tenant = await update_tenant(db, tenant_id, request)
    if not tenant:
        raise NotFoundError(message = str(f"Tenant {tenant_id} not found"))
    return tenant


@router.delete("/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def api_delete_tenant(
    tenant_id: UUID,
    _ctx=Depends(require_super_admin),
    db: AsyncSession = Depends(get_db_from_context),
) -> None:
    """Soft-delete a tenant. Requires ``super_admin`` role."""
    deleted = await delete_tenant(db, tenant_id)
    if not deleted:
        raise NotFoundError(message = str(f"Tenant {tenant_id} not found"))


# ---------------------------------------------------------------------------
# Lifecycle endpoints (Phase 1, Task 1.7)
# ---------------------------------------------------------------------------


@router.post("/{tenant_id}/suspend", response_model=TenantModel)
async def api_suspend_tenant(
    tenant_id: UUID,
    body: StatusChangeRequest | None = None,
    _ctx=Depends(require_super_admin),
    db: AsyncSession = Depends(get_db_from_context),
) -> TenantModel:
    """Suspend a tenant (active -> suspended). Requires ``super_admin`` role."""
    reason = body.reason if body else None
    changed_by = body.changed_by if body else None
    try:
        updated = await update_tenant_status(
            db, tenant_id, "suspended", reason=reason, changed_by=changed_by,
        )
    except ValueError as e:
        logger.warning("tenant_suspend_conflict", extra={"error_code": "TENANT_SUSPEND_ERROR"})
        raise ConflictError(message="Invalid tenant status transition")
    if not updated:
        raise NotFoundError(message = str(f"Tenant {tenant_id} not found"))
    tenant = await get_tenant(db, tenant_id)
    return tenant


@router.post("/{tenant_id}/activate", response_model=TenantModel)
async def api_activate_tenant(
    tenant_id: UUID,
    body: StatusChangeRequest | None = None,
    _ctx=Depends(require_super_admin),
    db: AsyncSession = Depends(get_db_from_context),
) -> TenantModel:
    """Activate a tenant (pending/suspended -> active). Requires ``super_admin`` role."""
    reason = body.reason if body else None
    changed_by = body.changed_by if body else None
    try:
        updated = await update_tenant_status(
            db, tenant_id, "active", reason=reason, changed_by=changed_by,
        )
    except ValueError as e:
        logger.warning("tenant_activate_conflict", extra={"error_code": "TENANT_ACTIVATE_ERROR"})
        raise ConflictError(message="Invalid tenant status transition")
    if not updated:
        raise NotFoundError(message = str(f"Tenant {tenant_id} not found"))
    tenant = await get_tenant(db, tenant_id)
    return tenant


@router.post("/{tenant_id}/status", response_model=TenantModel)
async def api_change_tenant_status(
    tenant_id: UUID,
    target_status: str = Query(..., description="Target status: active, suspended, deleted"),
    body: StatusChangeRequest | None = None,
    _ctx=Depends(require_super_admin),
    db: AsyncSession = Depends(get_db_from_context),
) -> TenantModel:
    """Change tenant status with reason and audit trail. Requires ``super_admin`` role."""
    reason = body.reason if body else None
    changed_by = body.changed_by if body else None
    try:
        updated = await update_tenant_status(
            db, tenant_id, target_status, reason=reason, changed_by=changed_by,
        )
    except ValueError as e:
        logger.warning("tenant_status_change_conflict", extra={"error_code": "TENANT_STATUS_ERROR"})
        raise ConflictError(message="Invalid tenant status transition")
    if not updated:
        raise NotFoundError(message = str(f"Tenant {tenant_id} not found"))
    tenant = await get_tenant(db, tenant_id)
    return tenant
