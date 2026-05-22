"""Synchronous identity helpers for Layer 1/2 database dependencies.

Layer 1 still uses synchronous SQLAlchemy sessions for several route handlers, so
its database dependencies cannot directly depend on async middleware internals.
These helpers bridge the canonical request-scoped ``RequestContext`` populated by
``GovernanceMiddleware`` into a small synchronous context object and retain a
verified service-auth fallback for compatibility tests.
"""

from __future__ import annotations

import hmac
import logging
import os
import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, FrozenSet, Iterable, List, Optional
from uuid import UUID, uuid4

from fastapi import Header, HTTPException, Request, status

from .context import (
    AUTH_SOURCE_API_KEY,
    AUTH_SOURCE_JWT,
    AUTH_SOURCE_SERVICE_ACCOUNT,
    AUTH_SOURCE_UNKNOWN,
    ISOLATION_TIER_SHARED,
    VALID_AUTH_SOURCES,
    VALID_ISOLATION_TIERS,
    RequestContext,
)
from .fallback_telemetry import enforce_fallback_enabled, record_fallback_usage
from .permissions import Permission, Role, ROLE_PERMISSIONS
from value_fabric.shared.models.typed_dict import TypedDictModel

logger = logging.getLogger(__name__)
_thread_local = threading.local()
DEFAULT_API_KEY_ROLE = Role.READ_ONLY.value
INVALID_API_KEY_CONTEXT_ERROR_CODE = "INVALID_API_KEY_CONTEXT"


@dataclass
class SyncRequestContext:
    """Synchronous request context used by sync SQLAlchemy dependencies."""

    tenant_id: Optional[UUID | str] = None
    user_id: Optional[Any] = None
    roles: List[str] = field(default_factory=list)
    api_key_id: Optional[str] = None
    permissions: FrozenSet[Permission | str] | Iterable[Permission | str] = field(default_factory=frozenset)
    source: str = AUTH_SOURCE_UNKNOWN
    raw: Dict[str, Any] = field(default_factory=dict)
    auth_source: Optional[str] = None
    request_id: Optional[str] = None
    org_id: Optional[Any] = None
    tenant_role: Optional[str] = None
    isolation_tier: str = ISOLATION_TIER_SHARED
    service_account_id: Optional[str] = None
    service_account_scopes: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.roles = [str(role) for role in (self.roles or [])]
        self.permissions = frozenset(self.permissions or [])
        self.service_account_scopes = [str(scope) for scope in (self.service_account_scopes or [])]
        if self.auth_source is None:
            self.auth_source = self.source
        if self.source == AUTH_SOURCE_UNKNOWN and self.auth_source:
            self.source = self.auth_source

    def is_auth_source_valid(self) -> bool:
        return self.auth_source in VALID_AUTH_SOURCES

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.tenant_id:
            errors.append("tenant_id is required")
        if not self.auth_source or not self.is_auth_source_valid():
            errors.append(f"auth_source must be one of {sorted(VALID_AUTH_SOURCES)}")
        if self.isolation_tier not in VALID_ISOLATION_TIERS:
            errors.append(f"isolation_tier must be one of {sorted(VALID_ISOLATION_TIERS)}")
        if self.auth_source == AUTH_SOURCE_SERVICE_ACCOUNT:
            if not self.service_account_id:
                errors.append("service account auth_source requires service_account_id")
            if not self.service_account_scopes:
                errors.append("service account auth_source requires non-empty service_account_scopes")
        return errors

    def is_super_admin(self) -> bool:
        return Role.SUPER_ADMIN.value in self.roles or "super_admin" in self.roles

    def to_dict(self) -> dict[str, Any]:
        return {
            "tenant_id": str(self.tenant_id) if self.tenant_id is not None else None,
            "user_id": str(self.user_id) if self.user_id is not None else None,
            "api_key_id": self.api_key_id,
            "org_id": str(self.org_id) if self.org_id is not None else None,
            "service_account_id": self.service_account_id,
            "roles": list(self.roles),
            "permissions": [value.value if isinstance(value, Permission) else str(value) for value in self.permissions],
            "tenant_role": self.tenant_role,
            "isolation_tier": self.isolation_tier,
            "auth_source": self.auth_source,
            "source": self.source,
            "service_account_scopes": list(self.service_account_scopes),
            "request_id": self.request_id,
        }


class SyncRequestContext_to_dictResult(TypedDictModel):
    api_key_id: Any
    auth_source: Any
    isolation_tier: Any
    org_id: Any
    permissions: Any
    request_id: Any
    roles: Any
    service_account_id: Any
    service_account_scopes: Any
    tenant_id: Any
    tenant_role: Any
    user_id: Any


def _parse_uuid(value: Any) -> UUID | None:
    if value is None or value == "":
        return None
    if isinstance(value, UUID):
        return value
    return UUID(str(value))


def _permissions_for_roles(roles: Iterable[str]) -> FrozenSet[Permission]:
    permissions: set[Permission] = set()
    for role_str in roles:
        try:
            permissions |= ROLE_PERMISSIONS[Role(str(role_str))].permissions
        except (ValueError, KeyError):
            logger.debug("Unknown role '%s' in sync context", role_str)
    return frozenset(permissions)


def _from_request_context(ctx: RequestContext) -> SyncRequestContext:
    return SyncRequestContext(
        tenant_id=ctx.tenant_id,
        user_id=ctx.user_id,
        roles=list(ctx.roles),
        api_key_id=ctx.api_key_id,
        permissions=frozenset(ctx.permissions),
        source=ctx.source,
        raw=dict(ctx.raw or {}),
        auth_source=ctx.auth_source,
        request_id=ctx.request_id,
        org_id=ctx.org_id,
        tenant_role=ctx.tenant_role,
        isolation_tier=ctx.isolation_tier,
        service_account_id=ctx.service_account_id,
        service_account_scopes=list(ctx.service_account_scopes),
    )


def _service_auth_context(x_tenant_id: str, x_service_auth: Optional[str]) -> SyncRequestContext:
    expected_secret = os.getenv("SERVICE_AUTH_SECRET", "")
    if not expected_secret or not x_service_auth or not hmac.compare_digest(x_service_auth, expected_secret):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid service authentication",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        tenant_id = UUID(str(x_tenant_id))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid X-Tenant-ID header",
        ) from exc
    return SyncRequestContext(
        tenant_id=tenant_id,
        user_id=None,
        roles=[Role.SYSTEM.value],
        permissions=frozenset(ROLE_PERMISSIONS[Role.SYSTEM].permissions),
        source=AUTH_SOURCE_SERVICE_ACCOUNT,
        auth_source=AUTH_SOURCE_SERVICE_ACCOUNT,
        service_account_id="service-auth-header",
        service_account_scopes=["internal:service-to-service"],
        raw={"service_auth_header": True},
    )


def get_request_context_sync(
    request: Request,
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
    x_service_auth: Optional[str] = Header(None, alias="X-Service-Auth"),
    x_organization_id: Optional[str] = Header(None, alias="X-Organization-ID"),
) -> SyncRequestContext:
    """Return a sync context bridged from canonical governance state.

    Prefer the async ``GovernanceMiddleware`` context already stored on
    ``request.state``. If a legacy caller reaches this dependency without that
    middleware state, accept ``X-Tenant-ID`` only when paired with the configured
    ``X-Service-Auth`` secret. ``X-Organization-ID`` remains a legacy fallback for
    older tests, but it no longer takes precedence over authenticated context.
    """
    governance_context = getattr(request.state, "governance_context", None)
    if governance_context is not None:
        if hasattr(governance_context, "validate"):
            validation_errors = list(governance_context.validate())
            if validation_errors:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={
                        "error": "INVALID_AUTH_CONTEXT",
                        "message": "Request identity context failed validation.",
                        "validation_errors": validation_errors,
                    },
                    headers={"WWW-Authenticate": "Bearer"},
                )
        return _from_request_context(governance_context)

    if x_tenant_id:
        enforce_fallback_enabled("sync.service_auth_header", default=True)
        record_fallback_usage(
            "sync.service_auth_header",
            tenant_id=x_tenant_id,
            client_id=request.headers.get("X-Client-ID"),
            service="shared.identity.middleware_sync",
            path=str(request.url.path),
        )
        return _service_auth_context(x_tenant_id, x_service_auth)

    if x_organization_id:
        enforce_fallback_enabled("sync.organization_header", default=True)
        try:
            tenant_id = UUID(x_organization_id)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid X-Organization-ID header",
            ) from exc
        record_fallback_usage(
            "sync.organization_header",
            tenant_id=tenant_id,
            client_id=request.headers.get("X-Client-ID"),
            service="shared.identity.middleware_sync",
            path=str(request.url.path),
        )
        return SyncRequestContext(
            tenant_id=tenant_id,
            roles=[Role.SYSTEM.value],
            permissions=frozenset(ROLE_PERMISSIONS[Role.SYSTEM].permissions),
            source=AUTH_SOURCE_SERVICE_ACCOUNT,
            auth_source=AUTH_SOURCE_SERVICE_ACCOUNT,
            service_account_id="legacy-organization-header",
            service_account_scopes=["internal:legacy-sync-context"],
        )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_request_context_sync(
    request: Request,
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
    x_service_auth: Optional[str] = Header(None, alias="X-Service-Auth"),
    x_organization_id: Optional[str] = Header(None, alias="X-Organization-ID"),
) -> SyncRequestContext:
    """Require a valid sync request context."""
    return get_request_context_sync(
        request,
        x_tenant_id=x_tenant_id,
        x_service_auth=x_service_auth,
        x_organization_id=x_organization_id,
    )


class GovernanceMiddlewareSync:
    """Sync SQLAlchemy-compatible governance middleware."""

    _PUBLIC_PATHS: frozenset[str] = frozenset({
        "/health",
        "/health/detailed",
        "/metrics",
        "/docs",
        "/openapi.json",
        "/redoc",
        "/",
    })

    def __init__(
        self,
        app: Any,
        api_key_resolver: Callable[[str], dict | None] | None = None,
        jwt_secret: str | None = None,
    ) -> None:
        self.app = app
        self._api_key_resolver = api_key_resolver
        self._jwt_secret = jwt_secret or os.getenv("JWT_SECRET", "")
        self._service_auth_secret = os.getenv("SERVICE_AUTH_SECRET", "")

    def __call__(self, environ: dict, start_response: Callable) -> Any:
        request_path = environ.get("PATH_INFO", "")
        if self._is_public_path(request_path):
            return self.app(environ, start_response)

        ctx = self._resolve_identity_sync(
            auth_header=environ.get("HTTP_AUTHORIZATION"),
            api_key_header=environ.get("HTTP_X_API_KEY"),
            x_tenant_header=environ.get("HTTP_X_TENANT_ID"),
            x_service_auth=environ.get("HTTP_X_SERVICE_AUTH", ""),
            request_path=request_path,
            request_method=environ.get("REQUEST_METHOD"),
        )

        _thread_local.request_context = ctx
        _thread_local.request_id = ctx.request_id if ctx else str(uuid4())
        try:
            return self.app(environ, start_response)
        finally:
            _thread_local.request_context = None
            _thread_local.request_id = None

    def _is_public_path(self, path: str) -> bool:
        return path in self._PUBLIC_PATHS or path.startswith("/docs") or path.startswith("/redoc")

    def _resolve_identity_sync(
        self,
        *,
        auth_header: str | None = None,
        api_key_header: str | None = None,
        x_tenant_header: str | None = None,
        x_service_auth: str = "",
        request_path: str | None = None,
        request_method: str | None = None,
    ) -> SyncRequestContext | None:
        from .jwt import decode_jwt

        if auth_header and auth_header.startswith("Bearer "):
            token_str = auth_header[7:]
            if not token_str.startswith("vf_"):
                try:
                    payload = decode_jwt(token_str, self._jwt_secret)
                    if payload:
                        return self._build_context_from_jwt_sync(payload)
                except Exception as exc:
                    logger.debug("JWT resolution failed: %s", exc)
                    return None

        if api_key_header and self._api_key_resolver:
            try:
                record = self._api_key_resolver(api_key_header)
                if record and record.get("enabled", True):
                    candidate = self._build_context_from_api_key_sync(record)
                    if candidate.validate():
                        logger.warning(
                            "API key context rejected: %s",
                            INVALID_API_KEY_CONTEXT_ERROR_CODE,
                            extra={"error_code": INVALID_API_KEY_CONTEXT_ERROR_CODE},
                        )
                        return None
                    return candidate
            except Exception as exc:
                logger.debug("API key resolution failed: %s", exc)

        if x_tenant_header:
            if not self._service_auth_secret:
                logger.warning("X-Tenant-ID rejected: SERVICE_AUTH_SECRET not configured")
                return None
            if not hmac.compare_digest(x_service_auth, self._service_auth_secret):
                logger.warning("X-Tenant-ID rejected: invalid X-Service-Auth")
                return None
            try:
                return _service_auth_context(x_tenant_header, x_service_auth)
            except HTTPException:
                logger.debug("Invalid X-Tenant-ID: %s", x_tenant_header)
                return None

        return None

    def _build_context_from_jwt_sync(self, payload: dict[str, Any]) -> SyncRequestContext:
        tenant_id = _parse_uuid(payload.get("tenant_id"))
        user_id = _parse_uuid(payload.get("sub") or payload.get("user_id"))
        org_id = _parse_uuid(payload.get("org_id"))
        service_account_id = payload.get("service_account_id")
        service_account_scopes = payload.get("scopes", [])
        auth_source = AUTH_SOURCE_SERVICE_ACCOUNT if service_account_id else payload.get("auth_source", AUTH_SOURCE_JWT)
        roles = [str(role) for role in payload.get("roles", [])]

        return SyncRequestContext(
            tenant_id=tenant_id,
            user_id=user_id,
            org_id=org_id,
            tenant_role=payload.get("tenant_role"),
            isolation_tier=payload.get("isolation_tier", ISOLATION_TIER_SHARED),
            roles=roles,
            permissions=_permissions_for_roles(roles),
            auth_source=auth_source,
            source=auth_source,
            service_account_id=str(service_account_id) if service_account_id else None,
            service_account_scopes=service_account_scopes,
        )

    def _build_context_from_api_key_sync(self, record: dict[str, Any]) -> SyncRequestContext:
        tenant_id = _parse_uuid(record.get("tenant_id"))
        user_id = _parse_uuid(record.get("user_id"))
        role = record.get("role", DEFAULT_API_KEY_ROLE)
        roles = [str(role)]
        permissions = set(_permissions_for_roles(roles))
        for permission in record.get("permissions") or []:
            try:
                permissions.add(Permission(str(permission)))
            except ValueError:
                logger.debug("Ignoring unknown API-key permission '%s'", permission)

        return SyncRequestContext(
            tenant_id=tenant_id,
            user_id=user_id,
            api_key_id=str(record.get("key_id")) if record.get("key_id") is not None else None,
            roles=roles,
            permissions=frozenset(permissions),
            auth_source=AUTH_SOURCE_API_KEY,
            source=AUTH_SOURCE_API_KEY,
            request_id=record.get("request_id"),
        )

    def _derive_permissions_sync(self, roles: list[str]) -> list[str]:
        return [permission.value for permission in _permissions_for_roles(roles)]
