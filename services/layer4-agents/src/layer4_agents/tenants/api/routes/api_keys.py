from __future__ import annotations

import asyncio

from value_fabric.shared.error_handling.exceptions import NotFoundError

"""API key management routes (tenant_admin only).

POST   /v1/api-keys              — create an API key (with tier limit check)
GET    /v1/api-keys              — list API keys for caller's tenant
DELETE /v1/api-keys/{key_id}     — revoke (soft-delete) an API key

Phase 3 enhancements:
- Tier-based API key limit enforcement before creation
- Audit event emission on create/revoke
"""


import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.dependencies import require_tenant_admin
from value_fabric.shared.identity.models import (
    APIKeyCreateRequest,
    APIKeyCreateResponse,
    APIKeyModel,
)
from value_fabric.shared.identity.permissions import Role, get_role_rank

from ....database import get_db_from_context
from ...service import create_api_key, get_tenant_settings, list_api_keys, revoke_api_key
from ...tier_enforcement import TierEnforcement

logger = logging.getLogger(__name__)

# Audit integration (optional)
try:
    from value_fabric.shared.audit import AuditAction, AuditOutcome, emit_audit_event

    AUDIT_AVAILABLE = True
except ImportError:
    AUDIT_AVAILABLE = False
    emit_audit_event = None  # type: ignore
    AuditAction = None  # type: ignore
    AuditOutcome = None  # type: ignore

router = APIRouter(prefix="/api-keys", tags=["API Keys"])


async def _get_tenant_tier(db: AsyncSession, tenant_id: str) -> str:
    """Look up the tenant's tier_id from settings JSONB. Defaults to 'free'."""
    settings = await get_tenant_settings(db, UUID(tenant_id))
    return settings.get("tier_id", "free") if settings else "free"


@router.post("", response_model=APIKeyCreateResponse, status_code=status.HTTP_201_CREATED)
async def api_create_key(
    request: APIKeyCreateRequest,
    ctx: RequestContext = Depends(require_tenant_admin),
    db: AsyncSession = Depends(get_db_from_context),
) -> APIKeyCreateResponse:
    """Create a new API key scoped to the caller's tenant.

    Checks the tenant's tier-based API key limit before creation.
    The raw secret is returned **once** in ``api_key``; store it securely.
    Requires ``tenant_admin`` role.
    """
    user_id = UUID(ctx.user_id) if ctx.user_id else None

    # Phase 3: Check tier limit before creating
    tier_id = await _get_tenant_tier(db, ctx.tenant_id)
    enforcer = TierEnforcement(db)
    await enforcer.check_api_key_limit(
        tenant_id=UUID(ctx.tenant_id),
        tier_id=tier_id,
    )

    # Caller may carry multiple roles; use the highest-ranked one for the
    # grant constraint. SUPER_ADMIN and SYSTEM are not attainable via API key.
    creator_role = None
    if ctx.roles:
        creator_role = max(
            (Role(r) for r in ctx.roles if r in {role.value for role in Role}),
            key=get_role_rank,
            default=None,
        )

    result = await create_api_key(
        db, ctx.tenant_id, request, user_id=user_id, creator_role=creator_role
    )

    # Emit audit event
    if AUDIT_AVAILABLE and emit_audit_event:
        try:
            await emit_audit_event(
                action=AuditAction.API_KEY_CREATED,
                outcome=AuditOutcome.SUCCESS,
                actor_id=ctx.user_id,
                tenant_id=ctx.tenant_id,
                resource_type="api_key",
                resource_id=result.key_id,
                details={
                    "key_name": request.name if hasattr(request, "name") else None,
                    "role": request.role.value if hasattr(request, "role") else None,
                    "tier_id": tier_id,
                },
            )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.warning("Failed to emit API key create audit event", exc_info=True)

    return result


@router.get("", response_model=list[APIKeyModel])
async def api_list_keys(
    active_only: bool = Query(True),
    ctx: RequestContext = Depends(require_tenant_admin),
    db: AsyncSession = Depends(get_db_from_context),
) -> list[APIKeyModel]:
    """List API keys for the caller's tenant. Requires ``tenant_admin`` role."""
    return await list_api_keys(db, ctx.tenant_id, active_only=active_only)


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def api_revoke_key(
    key_id: str,
    ctx: RequestContext = Depends(require_tenant_admin),
    db: AsyncSession = Depends(get_db_from_context),
) -> None:
    """Revoke an API key. Requires ``tenant_admin`` role."""
    revoked = await revoke_api_key(db, ctx.tenant_id, key_id)
    if not revoked:
        raise NotFoundError(message = str(f"API key {key_id!r} not found"))

    # Emit audit event
    if AUDIT_AVAILABLE and emit_audit_event:
        try:
            await emit_audit_event(
                action=AuditAction.API_KEY_REVOKED,
                outcome=AuditOutcome.SUCCESS,
                actor_id=ctx.user_id,
                tenant_id=ctx.tenant_id,
                resource_type="api_key",
                resource_id=key_id,
                details={"revoked_by": ctx.user_id},
            )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.warning("Failed to emit API key revoke audit event", exc_info=True)
