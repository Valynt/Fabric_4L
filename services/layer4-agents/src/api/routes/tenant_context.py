from __future__ import annotations

from value_fabric.shared.error_handling.exceptions import AuthenticationError, NotFoundError
"""Canonical tenant context endpoint for authenticated frontend and API clients."""


from typing import Any

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.dependencies import require_authenticated

from ...database import get_db_from_context
from ...tenants.service import get_tenant

router = APIRouter(prefix="/tenant", tags=["tenant-context"])


class TenantSummary(BaseModel):
    id: str
    name: str
    slug: str
    status: str
    tier_id: str
    settings: dict[str, Any]


class ActorSummary(BaseModel):
    user_id: str | None
    roles: list[str]
    permissions: list[str]
    api_key_id: str | None
    service_account_id: str | None


class RequestSummary(BaseModel):
    request_id: str | None
    auth_source: str
    isolation_tier: str


class TenantContextResponse(BaseModel):
    tenant: TenantSummary
    actor: ActorSummary
    request: RequestSummary


@router.get("/context", response_model=TenantContextResponse)
async def get_tenant_context(
    db: AsyncSession = Depends(get_db_from_context),
    ctx: RequestContext = Depends(require_authenticated),
) -> TenantContextResponse:
    """Return the canonical authenticated tenant context.

    This endpoint exposes the validated request context together with the
    current tenant metadata needed by onboarding and settings workflows.
    """
    if ctx.tenant_id is None:
        raise AuthenticationError(message = "Validated tenant context required")

    tenant = await get_tenant(db, ctx.tenant_id)
    if tenant is None:
        raise NotFoundError(message = "Tenant not found")

    settings = tenant.settings or {}
    return TenantContextResponse(
        tenant=TenantSummary(
            id=str(tenant.id),
            name=tenant.name,
            slug=tenant.slug,
            status=tenant.status,
            tier_id=settings.get("tier_id", "free"),
            settings=settings,
        ),
        actor=ActorSummary(
            user_id=str(ctx.user_id) if ctx.user_id is not None else None,
            roles=list(ctx.roles),
            permissions=[
                value.value if hasattr(value, "value") else str(value)
                for value in ctx.permissions
            ],
            api_key_id=ctx.api_key_id,
            service_account_id=ctx.service_account_id,
        ),
        request=RequestSummary(
            request_id=ctx.request_id,
            auth_source=ctx.auth_source or ctx.source,
            isolation_tier=ctx.isolation_tier,
        ),
    )
