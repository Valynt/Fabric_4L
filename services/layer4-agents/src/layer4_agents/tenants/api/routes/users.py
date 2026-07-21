from __future__ import annotations

import asyncio

from value_fabric.shared.error_handling.exceptions import NotFoundError

"""User management API routes (tenant_admin only).

POST   /v1/users/invite          — invite a user to the caller's tenant
POST   /v1/users/accept-invite   — accept an invitation and activate account
GET    /v1/users                 — list users in the caller's tenant
GET    /v1/users/{user_id}       — get a user
PATCH  /v1/users/{user_id}       — update a user's role / status
DELETE /v1/users/{user_id}       — deactivate a user
"""


import logging
import os
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.dependencies import require_authenticated, require_tenant_admin
from value_fabric.shared.identity.models import (
    UserAcceptInviteRequest,
    UserInviteRequest,
    UserModel,
    UserUpdateRequest,
)
from value_fabric.shared.rate_limiting.ip_limiter import IPRateLimitDependency

from ....database import get_db_from_context
from ...invitations import InvitationService
from ...service import (
    accept_invitation,
    deactivate_user,
    get_tenant,
    get_user,
    invite_user,
    list_users,
    update_user,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/users", tags=["Users"])

_accept_invite_limiter = IPRateLimitDependency(requests_per_minute=10)


# ---------------------------------------------------------------------------
# Invitation helpers
# ---------------------------------------------------------------------------


def _get_invitation_service() -> InvitationService:
    """Create an InvitationService, wiring Redis if available."""
    redis_url = os.getenv("REDIS_URL")
    redis_client = None
    if redis_url:
        try:
            import redis

            redis_client = redis.from_url(redis_url, decode_responses=True)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning("Failed to connect to Redis for invitations: %s", exc)
    return InvitationService(redis_client=redis_client)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/invite", response_model=UserModel, status_code=status.HTTP_201_CREATED)
async def api_invite_user(
    request: UserInviteRequest,
    ctx: RequestContext = Depends(require_tenant_admin),
    db: AsyncSession = Depends(get_db_from_context),
) -> UserModel:
    """Invite a user to the caller's tenant. Requires ``tenant_admin`` role.

    Generates an invitation token and sends an invitation email if an email
    provider (SendGrid or SMTP) is configured.
    """
    invited_by = UUID(ctx.user_id) if ctx.user_id else None
    invitation_service = _get_invitation_service()

    user, token = await invite_user(
        db,
        ctx.tenant_id,
        request,
        invited_by=invited_by,
        inviter_roles=ctx.roles,
        invitation_service=invitation_service,
    )

    # Send invitation email if token was generated
    if token:
        tenant = await get_tenant(db, ctx.tenant_id)
        tenant_name = tenant.name if tenant else "your organization"
        # Fetch inviter name if possible — simplified: pass None
        email_sent = await invitation_service.send_invitation_email(
            to_email=request.email,
            tenant_name=tenant_name,
            inviter_name=None,
            invitation_token=token,
        )
        if not email_sent:
            logger.warning(
                "Invitation email not sent for user %s in tenant %s — no email provider configured",
                request.email,
                ctx.tenant_id,
            )

    return user


@router.post("/accept-invite", response_model=UserModel)
async def api_accept_invite(
    request: UserAcceptInviteRequest,
    db: AsyncSession = Depends(get_db_from_context),
    _rate_limit: None = Depends(_accept_invite_limiter),
) -> UserModel:
    """Accept an invitation by setting a password and activating the account.

    This endpoint is **public** (does not require authentication) because the
    caller is an unauthenticated invitee redeeming their invitation token.
    """
    invitation_service = _get_invitation_service()
    return await accept_invitation(db, request, invitation_service)


@router.get("", response_model=list[UserModel])
async def api_list_users(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    ctx: RequestContext = Depends(require_tenant_admin),
    db: AsyncSession = Depends(get_db_from_context),
) -> list[UserModel]:
    """List all users in the caller's tenant. Requires ``tenant_admin`` role."""
    return await list_users(db, ctx.tenant_id, limit=limit, offset=offset)


@router.get("/me", response_model=UserModel)
async def api_get_current_user(
    ctx: RequestContext = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db_from_context),
) -> UserModel:
    """Get the currently authenticated user (self-service)."""
    if not ctx.user_id or not ctx.tenant_id:
        raise NotFoundError(message="Current user context is incomplete")
    user_id = UUID(str(ctx.user_id))
    tenant_id = UUID(str(ctx.tenant_id))
    user = await get_user(db, tenant_id, user_id)
    if not user:
        raise NotFoundError(message="Current user not found")
    return user


@router.patch("/me", response_model=UserModel)
async def api_update_current_user(
    request: UserUpdateRequest,
    ctx: RequestContext = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db_from_context),
) -> UserModel:
    """Update the currently authenticated user's own profile.

    Only ``display_name`` may be changed via self-service. Requests that
    include ``role`` or ``status`` are rejected to prevent privilege
    escalation by non-admins.
    """
    from value_fabric.shared.error_handling.exceptions import AuthorizationError

    if request.role is not None or request.status is not None:
        raise AuthorizationError(message="Role and status can only be changed by tenant admins")
    if not ctx.user_id or not ctx.tenant_id:
        raise NotFoundError(message="Current user context is incomplete")
    user_id = UUID(str(ctx.user_id))
    tenant_id = UUID(str(ctx.tenant_id))
    user = await update_user(
        db, tenant_id, user_id, UserUpdateRequest(display_name=request.display_name)
    )
    if not user:
        raise NotFoundError(message="Current user not found")
    return user


@router.get("/{user_id}", response_model=UserModel)
async def api_get_user(
    user_id: UUID,
    ctx: RequestContext = Depends(require_tenant_admin),
    db: AsyncSession = Depends(get_db_from_context),
) -> UserModel:
    """Get a user by ID. Requires ``tenant_admin`` role."""
    user = await get_user(db, ctx.tenant_id, user_id)
    if not user:
        raise NotFoundError(message=str(f"User {user_id} not found"))
    return user


@router.patch("/{user_id}", response_model=UserModel)
async def api_update_user(
    user_id: UUID,
    request: UserUpdateRequest,
    ctx: RequestContext = Depends(require_tenant_admin),
    db: AsyncSession = Depends(get_db_from_context),
) -> UserModel:
    """Update a user's role or status. Requires ``tenant_admin`` role."""
    user = await update_user(db, ctx.tenant_id, user_id, request)
    if not user:
        raise NotFoundError(message=str(f"User {user_id} not found"))
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def api_deactivate_user(
    user_id: UUID,
    ctx: RequestContext = Depends(require_tenant_admin),
    db: AsyncSession = Depends(get_db_from_context),
) -> None:
    """Deactivate a user. Requires ``tenant_admin`` role."""
    deactivated = await deactivate_user(db, ctx.tenant_id, user_id)
    if not deactivated:
        raise NotFoundError(message=str(f"User {user_id} not found"))
