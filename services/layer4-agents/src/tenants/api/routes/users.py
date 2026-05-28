from __future__ import annotations

from value_fabric.shared.error_handling.exceptions import NotFoundError
"""User management API routes (tenant_admin only).

POST   /v1/users/invite          — invite a user to the caller's tenant
GET    /v1/users                 — list users in the caller's tenant
GET    /v1/users/{user_id}       — get a user
PATCH  /v1/users/{user_id}       — update a user's role / status
DELETE /v1/users/{user_id}       — deactivate a user
"""


from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.dependencies import require_tenant_admin
from value_fabric.shared.identity.models import (
    UserInviteRequest,
    UserModel,
    UserUpdateRequest,
)

from ....database import get_db_from_context
from ...service import (
    deactivate_user,
    get_user,
    invite_user,
    list_users,
    update_user,
)

router = APIRouter(prefix="/users", tags=["Users"])


@router.post("/invite", response_model=UserModel, status_code=status.HTTP_201_CREATED)
async def api_invite_user(
    request: UserInviteRequest,
    ctx: RequestContext = Depends(require_tenant_admin),
    db: AsyncSession = Depends(get_db_from_context),
) -> UserModel:
    """Invite a user to the caller's tenant. Requires ``tenant_admin`` role."""
    invited_by = UUID(ctx.user_id) if ctx.user_id else None
    return await invite_user(db, ctx.tenant_id, request, invited_by=invited_by)


@router.get("", response_model=list[UserModel])
async def api_list_users(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    ctx: RequestContext = Depends(require_tenant_admin),
    db: AsyncSession = Depends(get_db_from_context),
) -> list[UserModel]:
    """List all users in the caller's tenant. Requires ``tenant_admin`` role."""
    return await list_users(db, ctx.tenant_id, limit=limit, offset=offset)


@router.get("/{user_id}", response_model=UserModel)
async def api_get_user(
    user_id: UUID,
    ctx: RequestContext = Depends(require_tenant_admin),
    db: AsyncSession = Depends(get_db_from_context),
) -> UserModel:
    """Get a user by ID. Requires ``tenant_admin`` role."""
    user = await get_user(db, ctx.tenant_id, user_id)
    if not user:
        raise NotFoundError(message = str(f"User {user_id} not found"))
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
        raise NotFoundError(message = str(f"User {user_id} not found"))
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
        raise NotFoundError(message = str(f"User {user_id} not found"))
