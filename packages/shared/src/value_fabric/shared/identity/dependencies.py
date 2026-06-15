"""FastAPI identity dependency compatibility helpers.

This module keeps the source-checkout import path fail-closed: mandatory security
regression tests import from ``value_fabric.shared.identity.dependencies`` without
requiring an installed wheel. The implementation intentionally delegates JWT
startup validation to the canonical security configuration module while exposing
FastAPI-compatible dependency helpers for deterministic unit gates.
"""

from __future__ import annotations

import inspect
import logging
import os
import sys
import time
import types
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

def _is_truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _allow_identity_fallback() -> bool:
    env = (os.getenv("VALUE_FABRIC_ENV") or os.getenv("ENV") or os.getenv("ENVIRONMENT") or "").strip().lower()
    app_env = (os.getenv("APP_ENV") or "").strip().lower()
    if env in {"local", "dev", "development", "test", "testing"}:
        return True
    if app_env in {"local", "dev", "development", "test", "testing"}:
        return True
    if _is_truthy(os.getenv("PYTEST_CURRENT_TEST")) or os.getenv("PYTEST_CURRENT_TEST"):
        return True
    if _is_truthy(os.getenv("CI")) and _is_truthy(os.getenv("ALLOW_IDENTITY_DEPENDENCY_FALLBACK_IN_CI")):
        return True
    return _is_truthy(os.getenv("ALLOW_IDENTITY_DEPENDENCY_FALLBACK"))


def _emit_fallback_observability(reason: str) -> None:
    metadata = {
        "reason": reason,
        "environment_metadata": {
            "VALUE_FABRIC_ENV": os.getenv("VALUE_FABRIC_ENV"),
            "ENV": os.getenv("ENV"),
            "ENVIRONMENT": os.getenv("ENVIRONMENT"),
            "APP_ENV": os.getenv("APP_ENV"),
            "CI": os.getenv("CI"),
            "PYTEST_CURRENT_TEST": bool(os.getenv("PYTEST_CURRENT_TEST")),
        },
        "process_metadata": {
            "pid": os.getpid(),
            "argv": list(sys.argv),
            "executable": sys.executable,
        },
    }
    logger.warning("identity.dependencies fallback activated", extra={"event": "identity_dependency_fallback", **metadata})
    try:
        from value_fabric.shared.audit import emit_audit_event as _emit_audit_event
        from value_fabric.shared.audit.models import AuditAction as _AuditAction, AuditOutcome as _AuditOutcome

        result = _emit_audit_event(
            action=getattr(_AuditAction, "UNKNOWN", "unknown"),
            outcome=getattr(_AuditOutcome, "ERROR", getattr(_AuditOutcome, "FAILURE", "failure")),
            resource_type="identity.dependencies",
            resource_id="fastapi-import-fallback",
            details=metadata,
        )
        if inspect.isawaitable(result):
            logger.warning(
                "identity.dependencies fallback audit emit returned awaitable outside request scope",
                extra={"event": "identity_dependency_fallback_audit_async", **metadata},
            )
    except Exception as exc:  # pragma: no cover
        logger.warning("identity.dependencies fallback audit emission failed: %s", exc, extra={"event": "identity_dependency_fallback_audit_error", **metadata})


def _resolve_fastapi_dependencies() -> tuple[Any, Any, Any, Any, Any]:
    try:  # pragma: no cover - FastAPI is available in CI, but keep import safe.
        from fastapi import Depends as fastapi_depends, HTTPException as fastapi_http_exception, Request as fastapi_request, status as fastapi_status
        from fastapi.params import Depends as fastapi_depends_param

        return fastapi_depends, fastapi_http_exception, fastapi_request, fastapi_status, fastapi_depends_param
    except (ImportError, ModuleNotFoundError) as exc:  # pragma: no cover
        if not _allow_identity_fallback():
            raise RuntimeError(
                "FastAPI dependency fallback is disabled outside sanctioned test/development runtime contexts"
            ) from exc
        _emit_fallback_observability(f"{type(exc).__name__}: {exc}")

        class _FallbackDependsParam:
            pass

        class _FallbackHTTPException(Exception):
            def __init__(self, status_code: int, detail: object | None = None, headers: dict[str, str] | None = None) -> None:
                super().__init__(detail)
                self.status_code = status_code
                self.detail = detail
                self.headers = headers or {}

        class _FallbackRequest:
            pass

        class _FallbackStatus:
            HTTP_400_BAD_REQUEST = 400
            HTTP_401_UNAUTHORIZED = 401
            HTTP_403_FORBIDDEN = 403

        return (lambda dependency=None: dependency), _FallbackHTTPException, _FallbackRequest, _FallbackStatus, _FallbackDependsParam


Depends, HTTPException, Request, status, DependsParam = _resolve_fastapi_dependencies()

from value_fabric.shared.audit import emit_audit_event
from value_fabric.shared.audit.models import AuditAction, AuditOutcome, PrivilegedAccessDetails
from value_fabric.shared.identity.context import (
    AUTH_SOURCE_UNKNOWN,
    RequestContext,
    get_request_context,
)
from value_fabric.shared.identity.permissions import Permission, Role
from value_fabric.shared.identity.policy_registry import authorize_action
from value_fabric.shared.security.config import validate_jwt_config

# Compatibility alias required by legacy tests and routes that patch/import
# ``shared.identity.dependencies`` while this source tree is imported through the
# ``value_fabric.shared`` package.
_shared_compat_module = sys.modules.setdefault("shared", types.ModuleType("shared"))
_identity_compat_module = sys.modules.setdefault("shared.identity", types.ModuleType("shared.identity"))
setattr(_shared_compat_module, "identity", _identity_compat_module)
setattr(_identity_compat_module, "dependencies", sys.modules[__name__])
sys.modules["shared.identity.dependencies"] = sys.modules[__name__]


def _unauthorized(detail: Any) -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


def _bad_request(detail: Any) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


def _forbidden(detail: Any) -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


async def _maybe_await(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


def _permission_value(permission: Permission | str) -> str:
    return permission.value if isinstance(permission, Permission) else str(permission)


def _role_value(role: Role | str) -> str:
    return role.value if isinstance(role, Role) else str(role)


def _header_value(request: Any, header_name: str) -> str | None:
    headers = getattr(request, "headers", {}) or {}
    getter = getattr(headers, "get", None)
    if callable(getter):
        return getter(header_name)
    return None


async def get_current_context(request: Request) -> Optional[RequestContext]:
    """Return the current request context, checking request.state then ContextVar."""

    if request is not None:
        state = getattr(request, "state", None)
        context = getattr(state, "governance_context", None)
        if context is not None:
            return context
        auth = getattr(state, "auth", None)
        if auth is not None:
            from value_fabric.shared.identity.fabric_auth import request_context_from_auth

            return request_context_from_auth(auth)
    return get_request_context()


async def get_optional_context(request: Request) -> Optional[RequestContext]:
    """Alias documenting optional request-context use at call sites."""

    return await get_current_context(request)


def _no_explicit_context() -> Optional[RequestContext]:
    """Prevent FastAPI from treating direct-call context overrides as body fields."""

    return None


async def require_authenticated(
    ctx: Optional[RequestContext] = Depends(get_current_context),
    *,
    context: Optional[RequestContext] = Depends(_no_explicit_context),
) -> RequestContext:
    """Require an authenticated context with a valid, non-unknown auth source."""

    if isinstance(ctx, DependsParam):
        ctx = None
    if isinstance(context, DependsParam):
        context = None
    if context is not None:
        ctx = context
    if ctx is None:
        ctx = get_request_context()
    if ctx is None:
        raise _unauthorized("Authentication context is required")
    # Only check auth_source validity here, not full validation
    # Full validation (including tenant_id) is checked by require_tenant_context
    if ctx.auth_source == AUTH_SOURCE_UNKNOWN or not ctx.is_auth_source_valid():
        raise _unauthorized({"message": "Authentication context is invalid", "errors": ["auth_source must be one of the approved authentication mechanisms"]})
    return ctx


async def require_tenant(tenant_id: str | None = None, context: RequestContext | None = None) -> RequestContext:
    """Require an authenticated tenant context, optionally matching a tenant ID."""

    ctx = await require_authenticated(context)
    if tenant_id is not None and str(ctx.tenant_id) != str(tenant_id):
        raise _forbidden("Tenant context does not match requested tenant")
    return ctx


async def require_tenant_context(context: RequestContext | None = None) -> RequestContext:
    """Require that a validated request context contains a tenant identifier."""

    ctx = await require_authenticated(context)
    if not ctx.tenant_id:
        raise _bad_request("Tenant context required. Ensure request has passed through GovernanceMiddleware.")
    return ctx


def require_role(*roles: Role | str) -> Callable[[RequestContext | None], object]:
    allowed = {_role_value(role) for role in roles}

    async def dependency(context: RequestContext | None = None) -> RequestContext:
        ctx = await require_authenticated(context)
        if not allowed.intersection(set(ctx.roles or [])):
            raise _forbidden(f"One of these roles is required: {sorted(allowed)}")
        return ctx

    return dependency


def require_permission(permission: Permission | str) -> Callable[[RequestContext | None], object]:
    needed = _permission_value(permission)

    async def dependency(context: RequestContext | None = None) -> RequestContext:
        ctx = await require_authenticated(context)
        if not ctx.has_permission(needed):
            raise _forbidden(f"Permission required: {needed}")
        return ctx

    return dependency


def require_any_permission(*permissions: Permission | str) -> Callable[[RequestContext | None], object]:
    needed = {_permission_value(permission) for permission in permissions}

    async def dependency(context: RequestContext | None = None) -> RequestContext:
        ctx = await require_authenticated(context)
        if ctx.has_any_permission(*needed):
            return ctx
        raise _forbidden(f"One of these permissions is required: {sorted(needed)}")

    return dependency


def require_all_permissions(*permissions: Permission | str) -> Callable[[RequestContext | None], object]:
    needed = {_permission_value(permission) for permission in permissions}

    async def dependency(context: RequestContext | None = None) -> RequestContext:
        ctx = await require_authenticated(context)
        missing = sorted(permission for permission in needed if not ctx.has_permission(permission))
        if missing:
            raise _forbidden(f"Missing required permissions: {missing}")
        return ctx

    return dependency


def require_action(action: str) -> Callable[[RequestContext | None], object]:
    async def dependency(context: RequestContext | None = None) -> RequestContext:
        ctx = await require_authenticated(context)
        return authorize_action(action, ctx)

    return dependency


# Explicit allowlist of administrative permissions. Wildcard patterns (e.g.
# ``startswith("admin:")``) are intentionally rejected to prevent privilege
# escalation if a compromised JWT includes a synthetic permission claim.
_ADMIN_PERMISSION_ALLOWLIST: frozenset[str] = frozenset({
    Permission.ADMIN_MODELS.value,
    Permission.ADMIN_API_KEYS.value,
    Permission.ADMIN_USERS.value,
    Permission.ADMIN_TENANTS.value,
    Permission.ADMIN_SYSTEM.value,
})


async def require_super_admin(context: RequestContext | None = None) -> RequestContext:
    """Require an explicit super-admin role.

    This is stricter than ``require_admin`` (which also accepts tenant-admin
    and content-admin) and lighter than ``require_privileged_access`` (which
    demands an audit-reason header).  Use it for endpoints that only the
    platform super administrator may reach.
    """

    ctx = await require_authenticated(context)
    if not ctx.is_super_admin():
        raise _forbidden("Super admin role is required")
    return ctx


async def require_admin(context: RequestContext | None = None) -> RequestContext:
    """Require an administrative role or explicit administrative permission."""

    ctx = await require_authenticated(context)
    permission_values = {_permission_value(permission) for permission in (ctx.permissions or [])}
    # Reject wildcard "all" and any permission not in the explicit allowlist.
    if "all" in permission_values:
        raise _forbidden(
            "Wildcard permission 'all' is not permitted. Use explicit administrative permissions."
        )
    has_admin_permission = permission_values.intersection(_ADMIN_PERMISSION_ALLOWLIST)
    if not (ctx.has_any_role(Role.SUPER_ADMIN, Role.TENANT_ADMIN, Role.CONTENT_ADMIN) or has_admin_permission):
        raise _forbidden("Administrative role or permission is required")
    return ctx


def require_privileged_access(
    *,
    privilege_reason_header: str = "X-Privileged-Reason",
    require_audit_log: bool = True,
    require_audit_emission: bool | None = None,
):
    """Return a dependency that permits only audited super-admin access.

    The dependency fails closed for unauthenticated contexts, invalid contexts,
    non-super-admin roles, and missing audit reasons when audit logging is
    required.

    Audit emission failures are treated as hard failures by default (F-16):
    if the audit sink is unavailable, privileged access is denied rather than
    proceeding silently without a record. This can be overridden by setting
    ``require_audit_emission=False`` or the env var
    ``PRIVILEGED_ACCESS_REQUIRE_AUDIT=false`` for planned maintenance windows.
    """

    # Resolve whether audit emission failure is a hard block.
    # Order of precedence: explicit kwarg > env var > default True.
    _require_emission: bool
    if require_audit_emission is not None:
        _require_emission = require_audit_emission
    else:
        _env = os.getenv("PRIVILEGED_ACCESS_REQUIRE_AUDIT", "true").strip().lower()
        _require_emission = _env not in {"0", "false", "no", "off"}

    async def _check_privileged(
        request: Request,
        context: RequestContext | None = None,
    ) -> RequestContext:
        if context is None:
            context = await get_current_context(request)
        if context is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Privileged access requires authentication",
            )

        validation_errors = context.validate()
        if validation_errors:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": "INVALID_AUTH_CONTEXT",
                    "message": "Privileged access requires a validated identity context.",
                    "validation_errors": validation_errors,
                },
            )

        if not context.is_super_admin():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Privileged access requires super admin role",
            )

        if require_audit_log:
            reason = _header_value(request, privilege_reason_header)
            if not reason:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Privileged access requires {privilege_reason_header} header with audit reason",
                )

            if context.privileged_session_start is None:
                object.__setattr__(context, "privileged_session_start", time.time())

            try:
                request_url = getattr(request, "url", None)
                request_path = getattr(request_url, "path", None) or "unknown"
                request_client = getattr(request, "client", None)
                ip_address = getattr(request_client, "host", None) if request_client else None
                accessed_tenant_ids = sorted(str(tenant_id) for tenant_id in context.accessed_tenant_ids)
                session_duration = (
                    int(time.time() - context.privileged_session_start)
                    if context.privileged_session_start
                    else 0
                )
                audit_details = PrivilegedAccessDetails(
                    accessed_tenant_ids=accessed_tenant_ids,
                    resource_types=["cross_tenant_query"],
                    session_duration_seconds=session_duration,
                    reason=reason,
                    approval_ticket=_header_value(request, "X-Approval-Ticket"),
                    query_count=len(accessed_tenant_ids),
                )

                await _maybe_await(
                    emit_audit_event(
                        action=AuditAction.CROSS_TENANT_ACCESS,
                        outcome=AuditOutcome.SUCCESS,
                        actor_id=context.user_id,
                        actor_type="super_admin",
                        tenant_id=context.tenant_id,
                        resource_type="privileged_session",
                        resource_id=str(request_path),
                        request_id=context.request_id,
                        ip_address=ip_address,
                        user_agent=_header_value(request, "User-Agent"),
                        details=audit_details.model_dump(),
                    )
                )
            except Exception as exc:
                if _require_emission:
                    # Fail closed: if we cannot record that privileged access
                    # occurred, we must not permit it (F-16).
                    logger.error(
                        "Privileged access denied: audit emission failed. "
                        "Set PRIVILEGED_ACCESS_REQUIRE_AUDIT=false to override "
                        "during planned audit sink maintenance. Error: %s",
                        exc,
                    )
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail=(
                            "Privileged access temporarily unavailable: "
                            "audit logging is required but the audit sink is unreachable."
                        ),
                    ) from exc
                else:
                    # Operator has explicitly opted out of hard failure.
                    logger.warning(
                        "Privileged access proceeding without audit record "
                        "(PRIVILEGED_ACCESS_REQUIRE_AUDIT=false). Error: %s",
                        exc,
                    )

        return context

    return _check_privileged


# Convenience aliases matching canonical shared dependencies.
# NOTE: ``require_super_admin`` is intentionally NOT re-aliased here. The
# explicit ``async def require_super_admin`` defined above uses
# ``ctx.is_super_admin()`` and must remain the exported implementation;
# re-aliasing it to ``require_role(Role.SUPER_ADMIN)`` would silently shadow it.
require_tenant_admin = require_role(Role.SUPER_ADMIN, Role.TENANT_ADMIN)
require_content_admin = require_role(Role.SUPER_ADMIN, Role.TENANT_ADMIN, Role.CONTENT_ADMIN)
require_analyst = require_role(Role.SUPER_ADMIN, Role.TENANT_ADMIN, Role.CONTENT_ADMIN, Role.ANALYST)

__all__ = [
    "get_current_context",
    "get_optional_context",
    "require_authenticated",
    "require_tenant",
    "require_tenant_context",
    "require_role",
    "require_permission",
    "require_any_permission",
    "require_all_permissions",
    "require_action",
    "require_admin",
    "require_privileged_access",
    "require_super_admin",
    "require_tenant_admin",
    "require_content_admin",
    "require_analyst",
    "validate_jwt_config",
]
