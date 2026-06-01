import json
from uuid import UUID

from fastapi import Request
from value_fabric.shared.error_handling.exceptions import AuthorizationError

from ..observability.structured_logging import get_logger

logger = get_logger(__name__)


def _as_uuid(raw: str | UUID | None) -> UUID | None:
    if raw is None:
        return None
    if isinstance(raw, UUID):
        return raw
    try:
        return UUID(str(raw))
    except (ValueError, TypeError, AttributeError):
        return None


def _audit_fields(request: Request, actor: str | None, tenant_id: UUID) -> dict[str, str]:
    request_id = request.headers.get("X-Request-ID") or getattr(
        getattr(request.state, "governance_context", None), "request_id", None
    )
    return {
        "tenant_id": str(tenant_id),
        "actor": actor or "unknown",
        "request_id": str(request_id or "unknown"),
    }


async def enforce_authenticated_tenant_precedence(
    request: Request,
    authenticated_tenant_id: UUID,
    *,
    actor: str | None,
) -> UUID:
    """Enforce tenant-source precedence: authenticated context wins.

    If request query/header/payload provide a tenant id that conflicts with the
    authenticated tenant context, fail closed with 403 and emit an audit log.
    """
    candidates: list[tuple[str, UUID | None]] = [
        ("header:X-Tenant-ID", _as_uuid(request.headers.get("X-Tenant-ID"))),
        ("query:tenant_id", _as_uuid(request.query_params.get("tenant_id"))),
    ]

    content_type = (request.headers.get("content-type") or "").lower()
    if "application/json" in content_type:
        try:
            body = await request.json()
        except (json.JSONDecodeError, RuntimeError):
            body = None
        if isinstance(body, dict):
            for key in ("tenant_id", "organization_id", "org_id"):
                if key in body:
                    candidates.append((f"payload:{key}", _as_uuid(body.get(key))))

    for source, candidate in candidates:
        if candidate is None:
            continue
        if candidate != authenticated_tenant_id:
            fields = _audit_fields(request, actor, authenticated_tenant_id)
            logger.warning("cross_tenant_request_denied", event="cross_tenant_request_denied", source=source, auth_tenant_id=fields["tenant_id"], requested_tenant_id=str(candidate), actor=fields["actor"], request_id=fields["request_id"], tenant_id=fields["tenant_id"])
            raise AuthorizationError(message = "Cross-tenant request denied.")

    return authenticated_tenant_id
