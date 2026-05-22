"""
Authentication and tenant-context dependency for Layer 5 Ground Truth API.

Identity is resolved by the canonical ``GovernanceMiddleware`` (shared across
L1-L6). ``get_current_user`` is a thin adapter that reads the already-validated
``RequestContext`` from ``request.state.governance_context`` and returns a
``TokenClaims`` dataclass for RBAC checks.

Resolution precedence (enforced upstream by ``GovernanceMiddleware``):
  1. ``Authorization: Bearer <JWT>`` — verified with ``JWT_SECRET``.
  2. ``X-API-Key`` — HMAC-verified against the stored hash (disabled on L5).

Fail-closed contract:
  - In any production-like runtime (``ENVIRONMENT``/``APP_ENV`` in
    ``production|staging``), no ``GovernanceMiddleware`` context means 401.
    No header or query-param fallback is permitted.
  - Dev/test fallback is limited to direct JWT verification gated behind
    ``ALLOW_INSECURE_DEV_AUTH_BYPASS=true`` **and** a non-production
    environment. Tenant headers and query params remain non-authoritative
    diagnostics and cannot create tenant context on their own.
"""

import logging
from dataclasses import dataclass, field
from uuid import UUID

import jwt
from fastapi import Depends, Header, HTTPException, Request, status
from value_fabric.shared.identity.context import AUTH_SOURCE_JWT, RequestContext
from value_fabric.shared.identity.fallback_telemetry import (
    enforce_fallback_enabled,
    record_fallback_usage,
)
from value_fabric.shared.identity.permissions import (
    Role,
    get_role_permissions,
    normalize_role_claims,
)
from value_fabric.shared.identity.policy_registry import (
    authorize_action as authorize_shared_action,
)

from ..config import Settings, get_settings

logger = logging.getLogger(__name__)
_AUTH_REQUIRED = "authentication_required"


def _auth_http_exception(status_code: int, *, error_code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={
            "error": _AUTH_REQUIRED,
            "error_code": error_code,
            "message": message,
        },
        headers={"WWW-Authenticate": "Bearer"},
    )


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class TokenClaims:
    """Parsed and validated JWT claims."""

    tenant_id: UUID
    user_id: str | None = None
    email: str | None = None
    roles: list[str] = field(default_factory=list)
    permissions: list[str] = field(default_factory=list)
    raw: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.permissions and self.roles:
            self.permissions = _derive_permissions(self.roles)

    def has_role(self, role: str) -> bool:
        return role in self.roles

    def require_role(self, role: str) -> None:
        if not self.has_role(role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{role}' is required for this operation.",
            )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _derive_permissions(roles: list[str]) -> list[str]:
    permissions: set[str] = set()
    for role_name in normalize_role_claims(roles):
        try:
            permissions.update(permission.value for permission in get_role_permissions(Role(role_name)))
        except ValueError:
            continue
    return sorted(permissions)


def authorize_action(action: str, caller: TokenClaims) -> TokenClaims:
    ctx = RequestContext(
        tenant_id=caller.tenant_id,
        user_id=caller.user_id,
        roles=caller.roles,
        permissions=frozenset(caller.permissions),
        auth_source=AUTH_SOURCE_JWT,
    )
    authorize_shared_action(action, ctx, target_tenant_id=str(caller.tenant_id))
    return caller


def _decode_jwt(token: str, settings: Settings) -> dict:
    """
    Decode and verify a JWT using the configured secret.

    Returns the payload dict on success and raises 401 on any validation failure.
    """
    try:
        header = jwt.get_unverified_header(token)
        header_alg = header.get("alg")
        if not isinstance(header_alg, str) or not header_alg.strip():
            raise _auth_http_exception(
                status.HTTP_401_UNAUTHORIZED,
                error_code="AUTH_INVALID_TOKEN",
                message="Invalid token.",
            )
        if header_alg.upper() != settings.jwt_algorithm.upper():
            raise _auth_http_exception(
                status.HTTP_401_UNAUTHORIZED,
                error_code="AUTH_INVALID_TOKEN",
                message="Invalid token.",
            )
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
            options={
                "require": ["sub", settings.jwt_tenant_claim, "exp", "iat", "nbf", "iss", "aud"],
                "verify_exp": True,
                "verify_aud": True,
                "verify_iss": True,
                "verify_iat": True,
                "verify_nbf": True,
            },
        )
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("JWT has expired")
        raise _auth_http_exception(
            status.HTTP_401_UNAUTHORIZED,
            error_code="AUTH_TOKEN_EXPIRED",
            message="Token has expired.",
        )
    except jwt.InvalidTokenError as exc:
        logger.debug("JWT validation failed: %s", exc)
        raise _auth_http_exception(
            status.HTTP_401_UNAUTHORIZED,
            error_code="AUTH_INVALID_TOKEN",
            message="Invalid token.",
        ) from exc


def _extract_org_id_from_payload(payload: dict, settings: Settings) -> UUID | None:
    """Pull the organization UUID from a decoded JWT payload."""
    raw = payload.get(settings.jwt_tenant_claim)
    if not raw:
        return None
    try:
        return UUID(str(raw))
    except (ValueError, AttributeError):
        return None


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------


def _token_claims_from_context(ctx) -> TokenClaims:
    """Build a ``TokenClaims`` view from the shared ``RequestContext``.

    The GovernanceMiddleware always validates tenant/user/role context before
    the dependency runs; this helper is a pure translation to the dataclass
    consumed by Layer 5 route handlers.
    """
    tenant_raw = ctx.tenant_id
    try:
        tenant_uuid = tenant_raw if isinstance(tenant_raw, UUID) else UUID(str(tenant_raw))
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tenant context is invalid.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    user_id = str(ctx.user_id) if ctx.user_id is not None else None
    roles = [str(role) for role in (ctx.roles or [])]
    return TokenClaims(
        tenant_id=tenant_uuid,
        user_id=user_id,
        roles=roles,
        permissions=[
            permission.value if hasattr(permission, "value") else str(permission)
            for permission in (ctx.permissions or frozenset())
        ],
        raw=dict(getattr(ctx, "raw", {}) or {}),
    )


def get_current_user(
    request: Request,
    authorization: str | None = Header(default=None),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    settings: Settings = Depends(get_settings),
) -> TokenClaims:
    """
    Resolve the caller's identity from the GovernanceMiddleware context.

    Primary path (all environments): read ``request.state.governance_context``
    populated by the canonical ``GovernanceMiddleware``.

    Dev/test fallback (non-production only, requires
    ``ALLOW_INSECURE_DEV_AUTH_BYPASS=true``): when no middleware context is
    present, tolerate a legacy direct JWT path to keep existing test fixtures
    working without weakening production.

    Raises HTTP 401 if no valid identity can be resolved.
    """
    # ── 1. Primary path — GovernanceMiddleware-validated context ──────────
    ctx = getattr(request.state, "governance_context", None) or getattr(
        request.state, "context", None
    )
    if ctx is not None and getattr(ctx, "tenant_id", None):
        return _token_claims_from_context(ctx)

    # In any production-like runtime, a missing middleware context is a
    # fail-closed 401 — no header or query-param fallback is permitted.
    if settings.is_production_like or not settings.allow_insecure_dev_auth_bypass:
        raise _auth_http_exception(
            status.HTTP_401_UNAUTHORIZED,
            error_code="AUTH_REQUIRED",
            message="Authentication required.",
        )

    # ── 2. Dev/test fallback — direct Bearer JWT verification ─────────────
    if authorization:
        if not authorization.startswith("Bearer "):
            raise _auth_http_exception(
                status.HTTP_401_UNAUTHORIZED,
                error_code="AUTH_INVALID_TOKEN",
                message="Invalid token.",
            )
        enforce_fallback_enabled("layer5.direct_jwt", default=True)
        token = authorization[7:].strip()
        if not token:
            raise _auth_http_exception(
                status.HTTP_401_UNAUTHORIZED,
                error_code="AUTH_INVALID_TOKEN",
                message="Invalid token.",
            )
        payload = _decode_jwt(token, settings)
        org_id = _extract_org_id_from_payload(payload, settings)
        if org_id is None:
            raise _auth_http_exception(
                status.HTTP_401_UNAUTHORIZED,
                error_code="AUTH_INVALID_TOKEN",
                message="Invalid token.",
            )

        user_id = payload.get(settings.jwt_user_claim)
        email = payload.get("email")
        roles = payload.get(settings.jwt_roles_claim, [])
        if isinstance(roles, str):
            roles = [roles]
        if x_tenant_id and x_tenant_id != str(org_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenant context mismatch.",
            )
        record_fallback_usage(
            "layer5.direct_jwt",
            tenant_id=org_id,
            client_id=request.headers.get("X-Client-ID"),
            service="layer5-ground-truth",
            path=str(request.url.path),
        )
        return TokenClaims(
            tenant_id=org_id,
            user_id=user_id,
            email=email,
            roles=roles,
            permissions=_derive_permissions(roles),
            raw=payload,
        )

    raise _auth_http_exception(
        status.HTTP_401_UNAUTHORIZED,
        error_code="AUTH_REQUIRED",
        message="Authentication required.",
    )
