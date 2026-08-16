from __future__ import annotations

from value_fabric.shared.error_handling.exceptions import (
    AuthorizationError,
    NotFoundError,
    ServiceUnavailableError,
)

"""Compatibility and shared security probe routes for Layer 1."""


from datetime import UTC, datetime
from hashlib import sha256
from typing import Any

from fastapi import APIRouter, Depends, Response
from value_fabric.shared.governance.deprecation_register import (
    DeprecationRegisterError,
    removal_date_for,
)
from value_fabric.shared.identity import RequestContext, Role, require_authenticated, require_role
from value_fabric.shared.observability.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)

# Register selector for this compatibility boundary. The sunset date itself lives
# in docs/deprecation_register.json (see D1) — never hardcode it here.
_INGEST_REGISTER_SELECTOR = "l1.api.short_ingest_compatibility_boundary"


def _hash_identifier(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()[:16]


def _get_deprecation_removal_date() -> str:
    """Return this route's sunset date from the canonical deprecation register.

    Reads ``docs/deprecation_register.json`` through the shared loader so runtime
    headers, startup warnings, and the CI gate consume one source and one schema.
    A missing or malformed register is logged loudly rather than silently
    replaced with an empty register.
    """
    try:
        return removal_date_for(_INGEST_REGISTER_SELECTOR)
    except DeprecationRegisterError as exc:
        logger.error(
            "deprecation_register_unavailable",
            error_code="DEPRECATION_REGISTER_UNAVAILABLE",
            selector=_INGEST_REGISTER_SELECTOR,
            error=repr(exc),
        )
        raise


def _record_compatibility_usage(*, endpoint: str, tenant_id: str, user_id: str) -> None:
    """Emit deprecation-usage telemetry for a legacy compatibility call."""
    logger.warning(
        "legacy_route_deprecation_usage",
        route_name="layer1_compatibility",
        legacy_route=endpoint,
        canonical_route="/api/v1/ingestion",
        tenant_hash=_hash_identifier(tenant_id),
        account_hash=_hash_identifier(user_id),
        removal_date=_get_deprecation_removal_date(),
        timestamp=datetime.now(UTC).isoformat(),
    )


def _add_deprecation_headers(response: Response) -> None:
    response.headers["Deprecation"] = "true"
    response.headers["Sunset"] = _get_deprecation_removal_date()
    response.headers["Link"] = '</api/v1/ingestion>; rel="successor-version"'


@router.post("/v1/ingest", tags=["Compatibility"])
async def short_ingest_compatibility_boundary(
    response: Response,
    ctx: RequestContext = Depends(require_authenticated),
) -> dict[str, str]:
    _add_deprecation_headers(response)
    _record_compatibility_usage(endpoint="/v1/ingest", tenant_id=str(ctx.tenant_id), user_id=str(ctx.user_id))
    raise ServiceUnavailableError(message="Use the canonical /api/v1/ingestion endpoints for Layer 1 ingestion operations.")


@router.get("/api/v1/entities", tags=["Security Compatibility"])
async def entity_security_boundary(
    _ctx: RequestContext = Depends(require_authenticated),
) -> dict[str, list[Any]]:
    raise NotFoundError(message="Entity listing is owned by the Layer 3 Knowledge Graph API. Use /api/v1/knowledge/entities instead.")


@router.post("/api/v1/entities", tags=["Security Compatibility"])
async def entity_create_security_boundary(
    _ctx: RequestContext = Depends(require_authenticated),
) -> dict[str, str]:
    raise NotFoundError(message="Entity creation is owned by the Layer 3 Knowledge Graph API. Use /api/v1/knowledge/entities instead.")


@router.delete("/api/v1/entities/{entity_id}", tags=["Security Compatibility"])
async def entity_delete_security_boundary(
    entity_id: str,
    _ctx: RequestContext = Depends(require_role(Role.TENANT_ADMIN, Role.SUPER_ADMIN)),
) -> dict[str, str]:
    raise ServiceUnavailableError(message=f"Entity deletion for {entity_id} is owned by the Layer 3 entity API contract.")


@router.get("/api/v1/user/profile", tags=["Security Compatibility"])
async def user_profile_security_boundary(
    ctx: RequestContext = Depends(require_authenticated),
) -> dict[str, str]:
    return {"user_id": str(ctx.user_id), "tenant_id": str(ctx.tenant_id)}


@router.get("/api/v1/user/{user_id}/private-data", tags=["Security Compatibility"])
async def user_private_data_security_boundary(
    user_id: str,
    ctx: RequestContext = Depends(require_authenticated),
) -> dict[str, str]:
    if str(ctx.user_id) != user_id:
        raise AuthorizationError(message = "User cannot access another user's private data")
    return {"user_id": user_id}


@router.get("/api/admin/users", tags=["Security Compatibility"])
@router.get("/api/admin/config", tags=["Security Compatibility"])
@router.get("/api/admin/audit-logs", tags=["Security Compatibility"])
@router.get("/api/admin/tenants", tags=["Security Compatibility"])
async def admin_read_security_boundary(
    _ctx: RequestContext = Depends(require_role(Role.TENANT_ADMIN, Role.SUPER_ADMIN)),
) -> dict[str, str]:
    raise ServiceUnavailableError(
        message="Admin read endpoints are not implemented in Layer 1. Query the Layer 4 tenant admin API instead."
    )
