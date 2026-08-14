from __future__ import annotations

"""Backend-authoritative, tenant-bound authorization snapshot."""

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession
from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.dependencies import require_authenticated

from ...database import get_db_from_context
from ...tenants.service import get_tenant

router = APIRouter(prefix="/authz", tags=["authorization"])


def _camel(name: str) -> str:
    head, *tail = name.split("_")
    return head + "".join(word.capitalize() for word in tail)


class AuthorizationSnapshot(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=_camel)

    tenant_id: str
    tenant_slug: str
    role: str
    expires_at: datetime
    permissions: list[str]
    entitlements: list[str]
    tenant_member: bool
    account_ids: list[str]


def _strings(value: Any) -> list[str]:
    if not isinstance(value, (list, tuple, set, frozenset)):
        return []
    return sorted({item.strip() for item in value if isinstance(item, str) and item.strip()})


def _expiry(ctx: RequestContext) -> datetime:
    value = ctx.raw.get("exp") if isinstance(ctx.raw, dict) else None
    try:
        if isinstance(value, bool) or value is None:
            raise ValueError
        expiry = datetime.fromtimestamp(float(value), tz=UTC)
    except (TypeError, ValueError, OverflowError):
        raise HTTPException(status_code=401, detail="Usable authentication expiry required")
    if expiry <= datetime.now(UTC):
        raise HTTPException(status_code=401, detail="Authentication context expired")
    return expiry


@router.get("/snapshot", response_model=AuthorizationSnapshot, response_model_by_alias=True)
async def get_authorization_snapshot(
    tenant_slug: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db_from_context),
    ctx: RequestContext = Depends(require_authenticated),
) -> AuthorizationSnapshot:
    if ctx.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authoritative tenant required"
        )
    expiry = _expiry(ctx)
    tenant = await get_tenant(db, ctx.tenant_id)
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authoritative tenant unavailable"
        )
    resolved_slug = str(tenant.slug).strip()
    if tenant_slug is not None and tenant_slug != resolved_slug:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Tenant selector mismatch"
        )

    raw = ctx.raw if isinstance(ctx.raw, dict) else {}
    roles = _strings([ctx.tenant_role, *ctx.roles])
    permissions = _strings([getattr(item, "value", item) for item in ctx.permissions])
    return AuthorizationSnapshot(
        tenant_id=str(ctx.tenant_id),
        tenant_slug=resolved_slug,
        role=roles[0] if roles else "",
        expires_at=expiry,
        permissions=permissions,
        entitlements=_strings(raw.get("entitlements")),
        tenant_member=True,
        account_ids=_strings(raw.get("account_ids")),
    )
