from __future__ import annotations

from value_fabric.shared.error_handling.exceptions import AuthorizationError, NotFoundError
"""Tenant admin dashboard API."""


from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.dependencies import require_tenant_admin

from ....database import get_db_from_context
from ...models.tenant import Tenant
from ...models.user import User
from ...service import get_tenant
from ...usage import UsageTrackingService

router = APIRouter(prefix="/tenants/{tenant_id}", tags=["Tenant Admin"])


class TenantSettingsUpdate(BaseModel):
    """Update tenant settings."""

    name: str | None = None
    settings: dict | None = None


class TenantUserInfo(BaseModel):
    """User information for tenant listing."""

    id: str
    email: str
    role: str
    created_at: str
    last_login: str | None


class UsageMetricsResponse(BaseModel):
    """Usage metrics response."""

    tenant_id: str
    period: dict
    api_calls: dict
    agent_executions: dict
    llm_usage: dict


class AuditEventInfo(BaseModel):
    """Audit event information."""

    id: str
    action: str
    timestamp: str
    actor_id: str | None
    details: dict | None


class AuditLogResponse(BaseModel):
    """Audit log response."""

    events: list[AuditEventInfo]
    total: int
    limit: int
    offset: int


class TenantSettingsResponse(BaseModel):
    """Tenant settings response."""

    id: str
    name: str
    slug: str
    status: str
    tier_id: str
    settings: dict
    created_at: str
    updated_at: str


class TenantSettingsUpdateResponse(BaseModel):
    """Tenant settings update response."""

    id: str
    name: str
    settings: dict
    updated_at: str


def _verify_tenant_access(tenant_id: UUID, context: RequestContext) -> None:
    """Verify tenant access permissions.

    A user may access a tenant's admin dashboard if they own that tenant
    (JWT tenant_id matches) or if they hold the super_admin role.
    is_super_admin() must be called as a method — reading it as an attribute
    returns the bound method object (always truthy) and bypasses the check.
    """
    if str(context.tenant_id) != str(tenant_id):
        if not context.is_super_admin():
            raise AuthorizationError(message = "Access denied")


@router.get("/users", response_model=list[TenantUserInfo])
async def list_tenant_users(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db_from_context),
    context: RequestContext = Depends(require_tenant_admin),
) -> list[TenantUserInfo]:
    """List users in tenant (tenant_admin only)."""
    _verify_tenant_access(tenant_id, context)

    # Query users for this tenant
    result = await db.execute(
        select(User).where(User.tenant_id == tenant_id).where(User.deleted_at.is_(None))
    )
    users = result.scalars().all()

    return [
        TenantUserInfo(
            id=str(u.id),
            email=u.email,
            role=u.role,
            created_at=u.created_at.isoformat() if u.created_at else "",
            last_login=u.last_login_at.isoformat() if u.last_login_at else None,
        )
        for u in users
    ]


@router.get("/usage", response_model=UsageMetricsResponse)
async def get_tenant_usage(
    tenant_id: UUID,
    days: int = 30,
    db: AsyncSession = Depends(get_db_from_context),
    context: RequestContext = Depends(require_tenant_admin),
) -> UsageMetricsResponse:
    """Get usage metrics for tenant."""
    _verify_tenant_access(tenant_id, context)

    usage_service = UsageTrackingService(db)
    summary = await usage_service.get_usage_summary(tenant_id, days)

    return UsageMetricsResponse(
        tenant_id=str(tenant_id),
        period={
            "start": summary.period_start.isoformat(),
            "end": summary.period_end.isoformat(),
        },
        api_calls={
            "total": summary.api_calls_total,
        },
        agent_executions={
            "total": summary.agent_executions,
            "total_time_ms": summary.agent_execution_time_ms,
        },
        llm_usage={
            "tokens_input": summary.llm_tokens_input,
            "tokens_output": summary.llm_tokens_output,
            "requests": summary.llm_requests,
        },
    )


@router.get("/audit-log", response_model=AuditLogResponse)
async def get_tenant_audit_log(
    tenant_id: UUID,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db_from_context),
    context: RequestContext = Depends(require_tenant_admin),
) -> AuditLogResponse:
    """Get audit log for tenant."""
    _verify_tenant_access(tenant_id, context)

    # Query audit log
    try:
        from value_fabric.shared.audit.models import AuditEvent

        # P1-016: COUNT(*) for total to avoid O(n) fetch-all
        count_result = await db.execute(
            select(func.count()).select_from(AuditEvent).where(AuditEvent.tenant_id == tenant_id)
        )
        total_count: int = count_result.scalar_one()

        result = await db.execute(
            select(AuditEvent)
            .where(AuditEvent.tenant_id == tenant_id)
            .order_by(AuditEvent.timestamp.desc())
            .limit(limit)
            .offset(offset)
        )
        events = result.scalars().all()

        return AuditLogResponse(
            events=[
                AuditEventInfo(
                    id=str(e.id),
                    action=e.action,
                    timestamp=e.timestamp.isoformat() if e.timestamp else "",
                    actor_id=str(e.actor_id) if e.actor_id else None,
                    details=e.details,
                )
                for e in events
            ],
            total=total_count,
            limit=limit,
            offset=offset,
        )
    except Exception:
        # Fallback if audit table not available
        return AuditLogResponse(events=[], total=0, limit=limit, offset=offset)


@router.get("/settings", response_model=TenantSettingsResponse)
async def get_tenant_settings(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db_from_context),
    context: RequestContext = Depends(require_tenant_admin),
) -> TenantSettingsResponse:
    """Get tenant settings."""
    _verify_tenant_access(tenant_id, context)

    tenant = await get_tenant(db, tenant_id)
    if not tenant:
        raise NotFoundError(message = "Tenant not found")

    # Get tier_id from settings
    settings = tenant.settings or {}
    tier_id = settings.get("tier_id", "free")

    return TenantSettingsResponse(
        id=tenant.id,
        name=tenant.name,
        slug=tenant.slug,
        status=tenant.status,
        tier_id=tier_id,
        settings=settings,
        created_at=tenant.created_at.isoformat() if tenant.created_at else "",
        updated_at=tenant.updated_at.isoformat() if tenant.updated_at else "",
    )


@router.patch("/settings", response_model=TenantSettingsUpdateResponse)
async def update_tenant_settings(
    tenant_id: UUID,
    update: TenantSettingsUpdate,
    db: AsyncSession = Depends(get_db_from_context),
    context: RequestContext = Depends(require_tenant_admin),
) -> TenantSettingsUpdateResponse:
    """Update tenant settings (tenant_admin only)."""
    _verify_tenant_access(tenant_id, context)

    # Get current tenant
    tenant_result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = tenant_result.scalar_one_or_none()
    if not tenant:
        raise NotFoundError(message = "Tenant not found")

    # Update name if provided
    if update.name:
        tenant.name = update.name

    # Update settings if provided
    if update.settings:
        current_settings = tenant.settings or {}
        # Merge settings - only allow certain fields to be updated by tenant admin
        allowed_fields = {"custom_branding", "notification_preferences", "webhook_url"}
        for key, value in update.settings.items():
            if key in allowed_fields:
                current_settings[key] = value
        tenant.settings = current_settings

    tenant.updated_at = datetime.now(UTC)

    return TenantSettingsUpdateResponse(
        id=str(tenant.id),
        name=tenant.name,
        settings=tenant.settings,
        updated_at=tenant.updated_at.isoformat(),
    )
