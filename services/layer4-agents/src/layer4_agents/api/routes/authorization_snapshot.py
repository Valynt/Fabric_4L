from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel
from sqlalchemy.ext.asyncio import AsyncSession
from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.dependencies import require_authenticated

from ...database import get_db_from_context
from ...tenants.service import get_tenant

router = APIRouter(prefix="/authz", tags=["authorization"])


class AuthorizationSnapshot(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    tenant_id: str
    tenant_slug: str
    role: str
    expires_at: datetime
    permissions: list[str]
    entitlements: list[str]
    tenant_member: bool
    account_ids: list[str]


class AuthorizationSnapshotResponse(BaseModel):
    snapshot: AuthorizationSnapshot


def _string_claim_list(raw: dict[str, Any], claim: str) -> list[str]:
    value = raw.get(claim, [])
    if not isinstance(value, (list, tuple, set)):
        return []
    return sorted({item for item in value if isinstance(item, str) and item})


@router.get("/snapshot", response_model=AuthorizationSnapshotResponse)
async def get_authorization_snapshot(
    tenant_slug: str = Query(min_length=1),
    db: AsyncSession = Depends(get_db_from_context),
    ctx: RequestContext = Depends(require_authenticated),
) -> AuthorizationSnapshotResponse:
    """Return grants derived only from the authenticated, tenant-bound context."""
    if ctx.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Validated tenant context required",
        )

    tenant = await get_tenant(db, ctx.tenant_id)
    if tenant is None or tenant.slug != tenant_slug:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requested tenant does not match authenticated tenant",
        )

    role = ctx.tenant_role or next((role for role in ctx.roles if role), "")
    raw_expiry = ctx.raw.get("exp")
    try:
        expires_at = datetime.fromtimestamp(float(raw_expiry), tz=UTC)
    except (TypeError, ValueError, OverflowError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated context has no valid expiry",
        ) from exc
    if not role or expires_at <= datetime.now(UTC):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated context is incomplete or expired",
        )

    permissions = sorted(
        {
            permission.value if hasattr(permission, "value") else str(permission)
            for permission in ctx.permissions
            if str(permission)
        }
    )
    return AuthorizationSnapshotResponse(
        snapshot=AuthorizationSnapshot(
            tenant_id=str(tenant.id),
            tenant_slug=tenant.slug,
            role=role,
            expires_at=expires_at,
            permissions=permissions,
            entitlements=_string_claim_list(ctx.raw, "entitlements"),
            tenant_member=True,
            account_ids=_string_claim_list(ctx.raw, "account_ids"),
        )
    )
