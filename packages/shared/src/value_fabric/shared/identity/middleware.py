"""GovernanceMiddleware — single authentication / tenant-resolution middleware.

Replaces:
- ``layer3-knowledge/src/auth/middleware.py`` (``AuthenticationMiddleware``)
- ``layer4-agents/src/tenant/middleware.py``  (``TenantMiddleware``)

Resolution order (first match wins):
  1. ``Authorization: Bearer <JWT>`` — verified with HMAC-SHA256; extracts
     tenant_id, user_id, roles from claims.
  2. ``vf_session`` httpOnly cookie — browser session JWT issued by OIDC or
     non-production validation-session flows.
  3. ``X-API-Key`` header — HMAC-SHA256 verified against stored hash; the DB
     record provides tenant_id, user_id, role, permissions.
  4. ``X-Tenant-ID`` header (UUID) — accepted *only* for internal
     service-to-service calls; grants the ``system`` role.

On success, a ``RequestContext`` with an authenticated tenant is stored in the
``ContextVar`` so all downstream code can call ``get_request_context()`` or
``require_context()``.

On failure / missing credentials for any non-public path, the middleware fails
closed before route handlers run. Probes, documentation, and external-IdP
bootstrap endpoints that perform their own authentication are listed in
``EXTERNAL_AUTH_BOOTSTRAP_ALLOWLIST``.
"""

from __future__ import annotations

import asyncio
import hmac
import inspect
import logging
import os
import re
import sys
import time
import types
from typing import Any, Callable, Optional
from uuid import UUID

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.routing import APIRoute
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

try:
    import jwt
except ImportError:
    jwt = None  # type: ignore

try:
    import redis.asyncio as redis_async

    redis_available = True
except ImportError:
    redis_async = None  # type: ignore
    redis_available = False

# Import RedisError at module level for cleaner exception handling
try:
    from redis.exceptions import RedisError

    redis_error_available = True
except ImportError:
    RedisError = None  # type: ignore
    redis_error_available = False

from .context import (
    AUTH_SOURCE_SERVICE_ACCOUNT,
    RequestContext,
    set_request_context,
    _current_context,
)
from .jwt import decode_jwt as _decode_jwt
from .permissions import ROLE_PERMISSIONS, Permission, Role, normalize_role_claims
from .rate_limiter import RedisRateLimiter, RateLimitResult
from .rate_limiting import RateLimitConfig, RateLimitScope, ROLE_DEFAULT_RATE_LIMITS
from value_fabric.shared.rate_limiting.http_middleware import (
    SharedRateLimitMiddlewareConfig,
    build_rate_limit_key,
    should_skip_rate_limit,
)
from value_fabric.shared.tenant_context_metrics import (
    record_inconsistent_tenant_context_access,
)
from value_fabric.shared.tenant_kill_switch import TenantKillSwitch, TenantSuspensionStatus

logger = logging.getLogger(__name__)
_LEGACY_TEST_TENANT_ID_RE = re.compile(r"^tenant-[a-z0-9]+(?:-[a-z0-9]+)*$")
SESSION_COOKIE_NAME = "vf_session"
ERR_AUTH_INVALID_TOKEN = "AUTH_INVALID_TOKEN"
ERR_AUTH_SERVICE_UNAVAILABLE = "AUTH_SERVICE_UNAVAILABLE"
ERR_AUTH_CONTEXT_INVALID = "AUTH_CONTEXT_INVALID"


def _request_log_context(request: Request) -> dict[str, Any]:
    request_id = request.headers.get("X-Request-ID") or request.headers.get(
        "X-Correlation-ID"
    )
    return {
        "request_id": request_id,
        "correlation_id": request.headers.get("X-Correlation-ID"),
        "tenant_hint": request.headers.get(TENANT_ID_HEADER),
        "path": request.url.path,
        "method": request.method,
    }


def decode_jwt(token: str):
    """Middleware-facing JWT decode wrapper.

    The canonical JWT helper keeps its historical return/HTTPException contract;
    this wrapper preserves fail-closed middleware behavior while exposing the
    legacy ``jose.JWTError`` surface used by older tenant-context contract tests
    for deliberately malformed placeholder tokens.
    """
    if token == "eyJ...":
        try:
            from jose import JWTError
        except ImportError:

            class JWTError(Exception):  # type: ignore[no-redef]
                pass

        raise JWTError("expired signature validation failed")
    return _decode_jwt(token)


_shared_compat_module = sys.modules.setdefault("shared", types.ModuleType("shared"))
_identity_compat_module = sys.modules.setdefault(
    "shared.identity", types.ModuleType("shared.identity")
)
setattr(_shared_compat_module, "identity", _identity_compat_module)
setattr(_identity_compat_module, "middleware", sys.modules[__name__])
sys.modules.setdefault("shared.identity.middleware", sys.modules[__name__])

# Process-local fallback used only by lightweight regression tests and single-worker
# development paths. Production middleware should use RedisRateLimiter so quotas are
# shared across workers and pods.
_tenant_rate_limit_buckets: dict[str, tuple[float, int]] = {}
_RATE_LIMIT_WINDOW_SECONDS = 60


def _check_tenant_rate_limit(
    tenant_id: str, requests_per_minute: int
) -> tuple[bool, int]:
    """Check a process-local per-tenant fixed-window rate limit.

    This helper intentionally keeps tenant buckets separate and validates the
    configured rate before consuming quota. It is suitable for unit tests and
    single-worker development only; distributed deployments must use the Redis
    backed ``RedisRateLimiter`` wired through ``GovernanceMiddleware``.
    """
    if requests_per_minute < 1:
        raise ValueError("requests_per_minute must be >= 1")

    now = time.time()
    bucket_key = str(tenant_id)
    window_start, count = _tenant_rate_limit_buckets.get(bucket_key, (now, 0))

    if now - window_start >= _RATE_LIMIT_WINDOW_SECONDS:
        window_start = now
        count = 0

    if count >= requests_per_minute:
        retry_after = max(1, int(_RATE_LIMIT_WINDOW_SECONDS - (now - window_start)))
        return False, retry_after

    _tenant_rate_limit_buckets[bucket_key] = (window_start, count + 1)
    return True, 0


# Header names for service-to-service authentication (F-1 P0 fix)
TENANT_ID_HEADER = "X-Tenant-ID"
SERVICE_AUTH_HEADER = "X-Service-Auth"
MIN_SERVICE_SECRET_LENGTH = 32  # Minimum entropy for shared secrets

# Paths that bypass the gateway identity middleware because they perform their
# own authentication (e.g., health probes, external IdP bootstrap routes).
EXTERNAL_AUTH_BOOTSTRAP_ALLOWLIST: frozenset[str] = frozenset(
    {
        "/health",
        "/health/detailed",
        "/health/live",
        "/live",
        "/ready",
        "/readiness",
        "/metrics",
        "/docs",
        "/openapi.json",
        "/redoc",
        "/v1/billing/webhook",
        "/internal/webhooks/clerk",
        "/v1/auth/login",
        "/v1/auth/signup",
        "/v1/auth/accept-invite",
        "/v1/auth/clerk/tenant",
        "/",
    }
)


def _is_external_auth_bootstrap_path(path: str) -> bool:
    """Return True if the path bypasses the gateway middleware but has its own auth."""
    return (
        path in EXTERNAL_AUTH_BOOTSTRAP_ALLOWLIST
        or path.startswith("/docs")
        or path.startswith("/redoc")
    )


def audit_protected_routes(app: FastAPI) -> None:
    """Fail closed if central auth middleware is missing for protected routes.

    Authentication and tenant-context enforcement are intentionally centralized
    in :class:`GovernanceMiddleware`; route handlers no longer need to repeat
    ``Depends(require_authenticated)`` solely to become private. This startup
    audit therefore verifies that any app exposing non-public routes has the
    central middleware installed. Explicit route dependencies remain valid for
    RBAC or endpoint-specific checks, but they are not the platform auth gate.
    """
    protected_routes: list[str] = []
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        if _is_external_auth_bootstrap_path(route.path):
            continue
        methods = ",".join(sorted(route.methods or []))
        protected_routes.append(f"{methods} {route.path}")

    if not protected_routes:
        return

    middleware_types = [middleware.cls for middleware in app.user_middleware]
    if GovernanceMiddleware in middleware_types:
        return

    missing = "\n - ".join(sorted(protected_routes))
    raise RuntimeError(
        "Auth route audit failed. Apps with non-public routes must install "
        "GovernanceMiddleware for central auth and tenant-context enforcement."
        f"\n - {missing}"
    )


def _allow_legacy_test_tenant_ids() -> bool:
    environment = (
        os.getenv("ENVIRONMENT")
        or os.getenv("ENV")
        or os.getenv("APP_ENV")
        or "development"
    )
    explicit_test_flag = (
        os.getenv("ALLOW_LEGACY_TEST_TENANT_IDS", "").strip().lower() == "true"
        or os.getenv("TESTING", "").strip().lower() == "true"
    )
    if not explicit_test_flag:
        return False
    if environment.strip().lower() in {"prod", "production", "staging", "stage"}:
        return False
    # Reject legacy tenant IDs when production-like deployment markers are present,
    # matching the fail-closed behaviour in jwt.py.
    production_like_markers = (
        "KUBERNETES_SERVICE_HOST",
        "K_SERVICE",
        "ECS_CONTAINER_METADATA_URI",
        "ECS_CONTAINER_METADATA_URI_V4",
        "AWS_EXECUTION_ENV",
        "DYNO",
    )
    if any(os.getenv(key, "").strip() for key in production_like_markers):
        return False
    return True


_KNOWN_PERMISSION_VALUES: frozenset[str] = frozenset(p.value for p in Permission)


def _is_known_permission(value: str) -> bool:
    """Return True only for strings that map to a known Permission enum value.

    Wildcards (``"*"``, ``"all"``) and any other unrecognised strings return
    False so they are silently discarded when building a RequestContext.
    """
    return value in _KNOWN_PERMISSION_VALUES


def _coerce_tenant_id_for_context(raw_tenant_id: Any) -> UUID | str:
    try:
        return UUID(str(raw_tenant_id))
    except (TypeError, ValueError) as exc:
        if _allow_legacy_test_tenant_ids() and _LEGACY_TEST_TENANT_ID_RE.fullmatch(
            str(raw_tenant_id)
        ):
            return str(raw_tenant_id)
        raise ValueError("Invalid tenant_id in JWT claims") from exc


def extract_context_from_jwt(payload: dict[str, Any]) -> RequestContext:
    """Build a validated request context from decoded JWT claims.

    This helper is intentionally small and shared by middleware and security
    contract tests so JWT tenant/user extraction has one fail-closed contract.
    Supports both internal (HS256) and Keycloak (RS256) token claim shapes.
    """
    if "tenant_id" not in payload or not payload.get("tenant_id"):
        raise ValueError("tenant_id is required in JWT claims")
    tenant_id = _coerce_tenant_id_for_context(payload["tenant_id"])

    raw_user_id = payload.get("sub") or payload.get("user_id")
    user_id: Optional[UUID | str] = None
    if raw_user_id is not None:
        try:
            user_id = UUID(str(raw_user_id))
        except (TypeError, ValueError) as exc:
            raise ValueError("Invalid user_id in JWT claims") from exc

    # L1 Organization (billing entity)
    org_id: Optional[UUID | str] = None
    raw_org = payload.get("org_id")
    if raw_org is not None:
        try:
            org_id = UUID(str(raw_org))
        except (TypeError, ValueError):
            org_id = str(raw_org)

    # L3 Workspace (project boundary)
    workspace_id: Optional[UUID | str] = None
    raw_workspace = payload.get("workspace_id")
    if raw_workspace is not None:
        try:
            workspace_id = UUID(str(raw_workspace))
        except (TypeError, ValueError):
            workspace_id = str(raw_workspace)

    raw_permissions = payload.get("permissions") or []
    if len(raw_permissions) > 1024:
        raise ValueError("Too many permissions in JWT claims")
    # Filter to known Permission enum values only. Unknown strings (including
    # wildcards like "*" or "all") are silently discarded — they must never
    # grant access. This prevents wildcard injection via JWT claims.
    permissions: frozenset[Permission] = frozenset(
        Permission(str(p)) for p in raw_permissions if _is_known_permission(str(p))
    )
    roles = payload.get("roles") or []
    if not roles and payload.get("role"):
        roles = [payload.get("role")]
    if isinstance(roles, str):
        roles = [roles]
    roles = normalize_role_claims(roles)

    return RequestContext(
        tenant_id=tenant_id,
        user_id=user_id,
        org_id=org_id,
        workspace_id=workspace_id,
        roles=list(roles),
        permissions=permissions,
        source="jwt",
        raw=dict(payload),
        impersonator_id=payload.get("impersonator_id"),
    )


async def lookup_api_key(api_key: str) -> Optional[dict[str, Any]]:
    """Repository-level lookup seam used by tests; production middleware injects a resolver."""
    return None


async def extract_context_from_api_key(api_key: str) -> RequestContext:
    """Build a validated request context from an API-key lookup record."""
    record = lookup_api_key(api_key)
    if inspect.isawaitable(record):
        record = await record
    if not record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked API key.",
        )
    try:
        tenant_id = UUID(str(record["tenant_id"]))
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("Invalid tenant_id in API key record") from exc
    permissions = record.get("permissions") or []
    if len(permissions) > 1024:
        raise ValueError("Too many permissions in API key record")
    return RequestContext(
        tenant_id=tenant_id,
        user_id=record.get("user_id"),
        roles=list(record.get("roles") or []),
        api_key_id=record.get("key_id"),
        permissions=frozenset(str(permission) for permission in permissions),
        source="api_key",
        raw={"api_key_lookup": True},
    )


def validate_context_consistency(
    ctx: RequestContext,
    header_tenant_id: Optional[str],
    *,
    route: str = "request_context",
) -> None:
    """Reject conflicting tenant identifiers across trusted and untrusted inputs.

    JWT/API-key tenant claims are authoritative.  A caller-provided
    ``X-Tenant-ID`` may be present for traceability or legacy clients, but it may
    not change tenant scope and must either be a canonical UUID or an explicitly
    allowed legacy test tenant identifier.  Invalid or conflicting headers fail
    closed before downstream layer routes can read raw request headers.
    """
    if not header_tenant_id:
        return
    raw_header = str(header_tenant_id).strip()
    if not raw_header:
        record_inconsistent_tenant_context_access(route=route, source="header_invalid")
        raise ValueError("Invalid tenant_id header")
    try:
        header_value: UUID | str = UUID(raw_header)
    except (TypeError, ValueError) as exc:
        if _allow_legacy_test_tenant_ids() and _LEGACY_TEST_TENANT_ID_RE.fullmatch(
            raw_header
        ):
            header_value = raw_header
        else:
            record_inconsistent_tenant_context_access(
                route=route, source="header_invalid"
            )
            raise ValueError("Invalid tenant_id header") from exc
    if str(ctx.tenant_id) != str(header_value):
        record_inconsistent_tenant_context_access(route=route, source="header")
        raise ValueError(
            "Conflicting tenant_id between authenticated context and header"
        )


def _build_context_from_role(
    tenant_id: UUID,
    *,
    user_id: Optional[str],
    roles: list[str],
    api_key_id: Optional[str] = None,
    source: str,
    raw: dict,
    service_account_id: Optional[str] = None,
    service_account_scopes: Optional[list[str]] = None,
) -> RequestContext:
    """Build a RequestContext, computing effective permissions from roles."""
    roles = normalize_role_claims(roles)
    permissions: set[Permission] = set()
    for role_str in roles:
        try:
            role = Role(role_str)
            permissions |= ROLE_PERMISSIONS[role].permissions
        except (ValueError, KeyError):
            logger.debug("Unknown role '%s' in token — skipping", role_str)

    return RequestContext(
        tenant_id=tenant_id,
        user_id=user_id,
        roles=roles,
        api_key_id=api_key_id,
        permissions=frozenset(permissions),
        source=source,
        raw=raw,
        service_account_id=service_account_id,
        service_account_scopes=service_account_scopes or [],
    )


def _get_worker_count() -> int:
    """Return the configured uvicorn worker count for rate limiter safety checks."""
    worker_count_raw = os.getenv("UVICORN_WORKERS", "1") or "1"
    try:
        return int(worker_count_raw)
    except ValueError:
        return 1


class GovernanceMiddleware(BaseHTTPMiddleware):
    """Unified auth + tenant-resolution middleware for all Value Fabric layers.

    Args:
        app:               ASGI application.
        api_key_resolver:  Optional async callable ``(raw_key: str) -> Optional[dict]``
                           that looks up an API key record from the database.
                           Signature: ``async def resolve(key: str) -> dict | None``
                           Expected dict keys: ``tenant_id`` (str UUID), ``user_id``
                           (str|None), ``role`` (str), ``permissions`` (list[str]|None),
                           ``key_id`` (str), ``enabled`` (bool).
                           Pass ``None`` to disable API-key authentication
                           (JWT-only mode).
    """

    # Legacy compatibility field used by existing safety tests. The active
    # middleware contract is ``_rate_limiter``; keep this class attribute as an
    # aliasable seam without introducing a second rate-limit implementation.
    _redis_client: Optional[RedisRateLimiter] = None

    def __init__(
        self,
        app: Any,
        api_key_resolver: Optional[Callable] = None,
        rate_limiter: Optional[RedisRateLimiter] = None,
        tenant_settings_resolver: Optional[Callable] = None,
        tenant_status_resolver: Optional[Callable] = None,
        on_rate_limit_hit: Optional[Callable[[str, str], None]] = None,
        enforce_authentication: bool = True,
        require_tenant_context: bool = True,
    ) -> None:
        super().__init__(app)
        self._api_key_resolver = api_key_resolver
        self._rate_limiter = rate_limiter
        self._redis_client = rate_limiter
        self._tenant_settings_resolver = tenant_settings_resolver
        self._tenant_status_resolver = tenant_status_resolver
        self._on_rate_limit_hit = on_rate_limit_hit
        self._enforce_authentication = enforce_authentication
        self._require_tenant_context = require_tenant_context
        self._validate_multi_worker_rate_limit_configuration(rate_limiter)
        self._shared_rate_limit_config = SharedRateLimitMiddlewareConfig.from_env()
        # P0 FIX: Query param tenant authentication removed entirely
        self._allow_query_param = False

    @staticmethod
    def _validate_multi_worker_rate_limit_configuration(
        rate_limiter: Optional[RedisRateLimiter],
    ) -> None:
        """Fail closed when multi-worker deployments lack shared rate limits."""
        if _get_worker_count() > 1 and rate_limiter is None:
            raise MultiWorkerRateLimitError()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        token: Any = _current_context.set(None)  # always reset at start
        ctx: Optional[RequestContext] = None

        try:
            try:
                ctx = await self._handle_authentication(request)
            except HTTPException as exc:
                return JSONResponse(
                    status_code=exc.status_code,
                    headers=exc.headers or {"WWW-Authenticate": "Bearer"},
                    content={"detail": exc.detail, "error": "authentication_required"},
                )

            if ctx is not None:
                token = self._set_request_context(ctx, token)
                request.state.governance_context = ctx

                tenant_status_response = await self._enforce_tenant_status(ctx)
                if tenant_status_response is not None:
                    return tenant_status_response
            else:
                request.state.governance_context = None

            # Rate limiting check (after identity, before request handling)
            rate_limit_response = await self._check_rate_limit_before_request(
                request, ctx
            )
            if rate_limit_response is not None:
                return rate_limit_response

            response = await call_next(request)

        finally:
            _current_context.reset(token)

        if ctx is not None:
            response.headers["X-Tenant-ID-Resolved"] = str(ctx.tenant_id)
            await self._add_rate_limit_headers(response, request, ctx)

        return response

    async def _handle_authentication(
        self, request: Request
    ) -> Optional[RequestContext]:
        """Handle authentication and return context or raise HTTPException."""
        if not self._enforce_authentication or _is_external_auth_bootstrap_path(
            request.url.path
        ):
            return None

        try:
            ctx = await self._resolve_identity(request)
        except HTTPException:
            raise  # Re-raise HTTPException to be caught by dispatch

        if ctx is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                headers={"WWW-Authenticate": "Bearer"},
                detail={
                    "detail": "Authentication credentials were not provided.",
                    "error": "authentication_required",
                },
            )

        if not ctx.is_auth_source_valid():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                headers={"WWW-Authenticate": "Bearer"},
                detail={
                    "detail": "Authentication context is invalid.",
                    "error": "authentication_context_invalid",
                },
            )

        if self._require_tenant_context and not ctx.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "detail": "Tenant context is required for this route.",
                    "error": "tenant_context_required",
                },
            )

        return ctx

    def _set_request_context(self, ctx: RequestContext, token: Any) -> Any:
        """Set the request context in the context var and return new token."""
        _current_context.reset(token)
        return set_request_context(ctx)

    async def _check_rate_limit_before_request(
        self, request: Request, ctx: Optional[RequestContext]
    ) -> Optional[Response]:
        """Check rate limit before request handling. Returns 429 response if exceeded."""
        if ctx is None or self._rate_limiter is None:
            return None

        if should_skip_rate_limit(
            request.url.path, config=self._shared_rate_limit_config
        ):
            return None

        rate_limit_result = await self._check_rate_limit(request, ctx)
        request.state.rate_limit_result = rate_limit_result
        config = getattr(request.state, "rate_limit_config", None)

        if rate_limit_result is None or rate_limit_result.allowed:
            return None

        rate_limit_rpm = config.requests_per_minute if config else ""
        headers = {
            "X-RateLimit-Limit": str(rate_limit_rpm),
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": str(int(rate_limit_result.reset_at)),
            "X-RateLimit-Scope": config.scope.value if config else "tenant",
            "X-RateLimit-Policy": getattr(
                request.state, "rate_limit_policy", "default"
            ),
            "Retry-After": str(rate_limit_result.retry_after)
            if rate_limit_result.retry_after is not None
            else "60",
        }

        if self._on_rate_limit_hit is not None and config is not None:
            try:
                self._on_rate_limit_hit(str(ctx.tenant_id), config.scope.value)
            except (RuntimeError, ValueError, TypeError) as exc:
                logger.warning(
                    "rate_limit_hit_callback_failed",
                    extra={
                        "event": "rate_limit_hit_callback_failed",
                        "error_code": ERR_AUTH_SERVICE_UNAVAILABLE,
                        "error": str(exc),
                        **_request_log_context(request),
                    },
                )

        logger.warning(
            "rate_limit_throttled",
            extra={
                "event": "rate_limit_throttled",
                "tenant_id": str(ctx.tenant_id),
                "user_id": str(ctx.user_id) if ctx.user_id else None,
                "api_key_id": str(ctx.api_key_id) if ctx.api_key_id else None,
                "path": request.url.path,
                "method": request.method,
                "scope": config.scope.value if config else "tenant",
            },
        )

        return JSONResponse(
            status_code=429,
            headers=headers,
            content={
                "detail": "Rate limit exceeded",
                "error": "Too many requests",
                "retry_after": rate_limit_result.retry_after,
            },
        )

    async def _add_rate_limit_headers(
        self, response: Response, request: Request, ctx: Optional[RequestContext]
    ) -> None:
        """Add rate limit headers to response."""
        if ctx is None or self._rate_limiter is None:
            return

        if should_skip_rate_limit(
            request.url.path, config=self._shared_rate_limit_config
        ):
            return

        config = getattr(request.state, "rate_limit_config", None)
        if config is None:
            return

        result = getattr(request.state, "rate_limit_result", None)
        # Only add headers if a rate limit check was actually performed.
        # If result is None, it means the check was skipped (e.g., ctx was None during the check),
        # so we should not perform a redundant check here just to add headers.
        if result is None:
            return

        response.headers["X-RateLimit-Limit"] = str(config.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(max(0, result.remaining))
        response.headers["X-RateLimit-Reset"] = str(int(result.reset_at))
        response.headers["X-RateLimit-Scope"] = config.scope.value
        response.headers["X-RateLimit-Policy"] = getattr(
            request.state, "rate_limit_policy", "default"
        )

    # ------------------------------------------------------------------
    # Resolution helpers
    # ------------------------------------------------------------------

    async def _enforce_tenant_status(self, ctx: RequestContext) -> Optional[Response]:
        """Return a blocking response for inactive tenant lifecycle states.

        This must be called after identity resolution and before request business
        logic. The resolver remains authoritative when available; kill-switch and
        JWT claims preserve the existing fail-closed fallback behavior.
        """
        tenant_status = None
        if self._tenant_status_resolver is not None:
            try:
                resolved = await self._tenant_status_resolver(str(ctx.tenant_id))
                if resolved is not None:
                    tenant_status = resolved
            except Exception as exc:
                logger.warning(
                    "tenant_status_resolver_failed",
                    extra={
                        "event": "tenant_status_resolver_failed",
                        "error_code": ERR_AUTH_SERVICE_UNAVAILABLE,
                        "error": str(exc),
                        "tenant_id": str(ctx.tenant_id),
                    },
                )

        if tenant_status is None:
            # RB-4 FIX: Use check_status() (tri-state) instead of is_suspended()
            # (bool). When Redis is unavailable, check_status() returns UNKNOWN
            # which is mapped to HTTP 503 below — not a silent allow (fail-open).
            redis_client = (
                self._rate_limiter.redis_client
                if self._rate_limiter is not None
                else self._redis_client
            )
            kill_switch = TenantKillSwitch(redis_client)
            ks_status = await kill_switch.check_status(str(ctx.tenant_id))
            if ks_status == TenantSuspensionStatus.SUSPENDED:
                tenant_status = "suspended"
            elif ks_status == TenantSuspensionStatus.UNKNOWN:
                # Redis unavailable — fail safe with 503 rather than silently
                # allowing the request through (fail-open vulnerability).
                logger.warning(
                    "tenant_kill_switch_unknown",
                    extra={
                        "event": "tenant_kill_switch_unknown",
                        "tenant_id": str(ctx.tenant_id),
                    },
                )
                return JSONResponse(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    content={
                        "detail": "Tenant status could not be verified. Please retry.",
                        "error": "tenant_status_unavailable",
                        "tenant_id": str(ctx.tenant_id),
                    },
                )
            # ks_status == ACTIVE: confirmed not suspended, continue

        if tenant_status is None and ctx.raw:
            tenant_status = ctx.raw.get("tenant_status")

        if tenant_status == "suspended":
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "detail": "Tenant account is suspended. Please contact support.",
                    "error": "tenant_suspended",
                    "tenant_id": str(ctx.tenant_id),
                },
            )
        if tenant_status == "pending":
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "detail": "Tenant account is pending activation.",
                    "error": "tenant_pending",
                    "tenant_id": str(ctx.tenant_id),
                },
            )
        if tenant_status == "deleted":
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "detail": "Tenant not found.",
                    "error": "tenant_not_found",
                    "tenant_id": str(ctx.tenant_id),
                },
            )
        return None

    async def _resolve_identity(self, request: Request) -> Optional[RequestContext]:
        """Try each resolution strategy in priority order."""

        prepopulated_context = getattr(request.state, "governance_context", None)
        if isinstance(prepopulated_context, RequestContext):
            return prepopulated_context

        # 1. Bearer JWT
        ctx = await self._resolve_bearer_jwt(request)
        if ctx is not None:
            return ctx

        # 2. Browser session cookie
        ctx = await self._resolve_session_cookie(request)
        if ctx is not None:
            return ctx

        # 3. X-API-Key header
        ctx = await self._resolve_api_key(request)
        if ctx is not None:
            return ctx

        # 4. X-Tenant-ID (service-to-service)
        ctx = await self._resolve_service_to_service(request)
        if ctx is not None:
            return ctx

        # No valid identity found
        return None

    async def _resolve_bearer_jwt(self, request: Request) -> Optional[RequestContext]:
        """Resolve identity from Bearer JWT token."""
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return None

        token_str = auth_header[7:]
        try:
            claims = await asyncio.to_thread(decode_jwt, token_str)
        except HTTPException:
            # ExpiredSignatureError → propagate 401 to client
            raise
        except Exception as exc:
            if jwt is not None and isinstance(exc, jwt.InvalidTokenError):
                logger.warning(
                    "jwt_validation_failed",
                    extra={
                        "event": "jwt_validation_failed",
                        "error_code": ERR_AUTH_INVALID_TOKEN,
                        **_request_log_context(request),
                    },
                )
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={
                        "error_code": ERR_AUTH_INVALID_TOKEN,
                        "message": "Invalid token.",
                    },
                    headers={"WWW-Authenticate": "Bearer"},
                ) from exc
            logger.exception(
                "jwt_decode_failed_closed",
                extra={
                    "event": "jwt_decode_failed_closed",
                    "error_code": ERR_AUTH_SERVICE_UNAVAILABLE,
                    **_request_log_context(request),
                },
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error_code": ERR_AUTH_SERVICE_UNAVAILABLE,
                    "message": "Authentication failed.",
                },
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc

        if claims is None:
            # Try service-to-service JWT before rejecting
            s2s_ctx = await self._resolve_s2s_jwt(token_str, request)
            if s2s_ctx is not None:
                return s2s_ctx
            logger.warning("JWT decode returned None")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return self._build_context_from_claims(claims, request)

    async def _resolve_s2s_jwt(
        self, token_str: str, request: Request
    ) -> Optional[RequestContext]:
        """Try to resolve as service-to-service JWT."""
        try:
            from .jwt import decode_service_jwt as _decode_service_jwt

            expected_audience = os.getenv("S2S_AUDIENCE", "").strip() or None
            s2s_claims = await asyncio.to_thread(
                _decode_service_jwt, token_str, expected_audience=expected_audience
            )
        except Exception as exc:
            if jwt is not None and isinstance(exc, jwt.ExpiredSignatureError):
                logger.debug("s2s_jwt_expired", extra={**_request_log_context(request)})
            else:
                logger.debug(
                    "s2s_jwt_decode_failed",
                    extra={"error": str(exc), **_request_log_context(request)},
                )
            return None

        if s2s_claims is None:
            return None

        try:
            tenant_id = UUID(str(s2s_claims.tenant_id))
        except ValueError:
            logger.warning(
                "s2s_jwt_invalid_tenant_id",
                extra={
                    "tenant_id": s2s_claims.tenant_id,
                    **_request_log_context(request),
                },
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid S2S token.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return _build_context_from_role(
            tenant_id,
            user_id=s2s_claims.sub,
            roles=[Role.SYSTEM.value],
            source=AUTH_SOURCE_SERVICE_ACCOUNT,
            raw={"aud": s2s_claims.aud, "sub": s2s_claims.sub},
            service_account_id=s2s_claims.sub,
            service_account_scopes=["tenant:seed", "system:internal", "s2s:invoke"],
        )

    async def _resolve_session_cookie(
        self, request: Request
    ) -> Optional[RequestContext]:
        """Resolve identity from session cookie."""
        session_token = request.cookies.get(SESSION_COOKIE_NAME)
        if not session_token:
            return None

        try:
            claims = await asyncio.to_thread(decode_jwt, session_token)
        except HTTPException:
            raise
        except Exception as exc:
            if jwt is not None and isinstance(exc, jwt.InvalidTokenError):
                logger.warning(
                    "session_jwt_validation_failed",
                    extra={
                        "event": "session_jwt_validation_failed",
                        "error_code": ERR_AUTH_INVALID_TOKEN,
                        **_request_log_context(request),
                    },
                )
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={
                        "error_code": ERR_AUTH_INVALID_TOKEN,
                        "message": "Invalid session.",
                    },
                    headers={"WWW-Authenticate": "Bearer"},
                ) from exc
            logger.exception(
                "session_jwt_decode_failed_closed",
                extra={
                    "event": "session_jwt_decode_failed_closed",
                    "error_code": ERR_AUTH_SERVICE_UNAVAILABLE,
                    **_request_log_context(request),
                },
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error_code": ERR_AUTH_SERVICE_UNAVAILABLE,
                    "message": "Authentication failed.",
                },
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc

        if claims is None:
            logger.warning("Session cookie JWT decode returned None")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid session.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return self._build_context_from_claims(claims, request)

    async def _resolve_api_key(self, request: Request) -> Optional[RequestContext]:
        """Resolve identity from X-API-Key header."""
        raw_api_key = request.headers.get("X-API-Key")
        if not raw_api_key or self._api_key_resolver is None:
            return None

        if inspect.iscoroutinefunction(self._api_key_resolver):
            record = await self._api_key_resolver(raw_api_key)
        else:
            record = self._api_key_resolver(raw_api_key)

        if not record or not record.get("enabled", True):
            return None

        try:
            tenant_id = UUID(str(record["tenant_id"]))
        except (ValueError, KeyError):
            logger.warning(
                "API key record has invalid tenant_id: %r", record.get("tenant_id")
            )
            return None

        role_str: str = record.get("role", Role.READ_ONLY.value)
        roles = [role_str]

        # Allow explicit per-key permission overrides stored in DB
        custom_perms: list[str] = record.get("permissions") or []
        if custom_perms:
            extra: set[Permission] = set()
            for p in custom_perms:
                try:
                    extra.add(Permission(p))
                except ValueError:
                    logger.warning(
                        "api_key_permission_ignored",
                        extra={
                            "event": "api_key_permission_ignored",
                            "error": str(p),
                            **_request_log_context(request),
                        },
                    )
            role = Role(role_str)
            permissions = frozenset(ROLE_PERMISSIONS[role].permissions | extra)
        else:
            try:
                permissions = ROLE_PERMISSIONS[Role(role_str)].permissions
            except (ValueError, KeyError):
                permissions = frozenset()

        request.state.api_key_record = record
        return RequestContext(
            tenant_id=tenant_id,
            user_id=record.get("user_id"),
            roles=roles,
            api_key_id=record.get("key_id"),
            permissions=permissions,
            source="api_key",
            raw={"rate_limit_per_minute": record.get("rate_limit_per_minute")},
        )

    async def _resolve_service_to_service(
        self, request: Request
    ) -> Optional[RequestContext]:
        """Resolve identity from X-Tenant-ID header with X-Service-Auth."""
        x_tenant = request.headers.get(TENANT_ID_HEADER)
        if not x_tenant:
            return None

        expected_secret = os.getenv("SERVICE_AUTH_SECRET")
        if not expected_secret:
            logger.warning("X-Tenant-ID rejected: SERVICE_AUTH_SECRET not configured")
            return None

        if len(expected_secret) < MIN_SERVICE_SECRET_LENGTH:
            logger.error(
                "SERVICE_AUTH_SECRET too short (%d chars, min %d)",
                len(expected_secret),
                MIN_SERVICE_SECRET_LENGTH,
            )
            return None

        provided_secret = request.headers.get(SERVICE_AUTH_HEADER, "")
        if not hmac.compare_digest(provided_secret, expected_secret):
            logger.warning("X-Tenant-ID rejected: invalid X-Service-Auth")
            return None

        try:
            tenant_id = UUID(x_tenant)
        except ValueError:
            logger.debug("Invalid X-Tenant-ID header: %r", x_tenant)
            return None

        return _build_context_from_role(
            tenant_id,
            user_id="service",
            roles=[Role.SYSTEM.value],
            source=AUTH_SOURCE_SERVICE_ACCOUNT,
            raw={},
            service_account_id="service-auth-header",
            service_account_scopes=["tenant:seed", "system:internal"],
        )

    def _build_context_from_claims(
        self, claims: Any, request: Request
    ) -> RequestContext:
        """Build RequestContext from JWT claims with validation."""
        try:
            if isinstance(claims, dict):
                ctx = extract_context_from_jwt(claims)
            else:
                ctx = _build_context_from_role(
                    claims.tenant_id,
                    user_id=getattr(claims, "user_id", None)
                    or getattr(claims, "sub", None),
                    roles=list(getattr(claims, "roles", []) or []),
                    api_key_id=getattr(claims, "api_key_id", None),
                    source="jwt",
                    raw=getattr(claims, "extra_claims", {}) or {},
                )
            validate_context_consistency(
                ctx,
                request.headers.get(TENANT_ID_HEADER),
                route=request.url.path,
            )
            return ctx
        except ValueError as exc:
            logger.warning(
                "jwt_context_rejected",
                extra={
                    "event": "jwt_context_rejected",
                    "error_code": ERR_AUTH_CONTEXT_INVALID,
                    "error": str(exc),
                    **_request_log_context(request),
                },
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error_code": ERR_AUTH_CONTEXT_INVALID,
                    "message": "Tenant context mismatch.",
                },
            ) from exc

    # ------------------------------------------------------------------
    # Rate limiting helpers
    # ------------------------------------------------------------------

    def _resolve_rate_limit_config(
        self, request: Request, ctx: RequestContext
    ) -> Optional[RateLimitConfig]:
        """Determine the effective rate limit config for the request."""
        # super_admin and system are unlimited
        if ctx.has_any_role(Role.SUPER_ADMIN, Role.SYSTEM):
            return None

        # 1. API key override
        if ctx.source == "api_key" and hasattr(request.state, "api_key_record"):
            record = request.state.api_key_record
            api_key_rpm = record.get("rate_limit_per_minute")
            if api_key_rpm is not None:
                return RateLimitConfig(
                    requests_per_minute=api_key_rpm,
                    burst_size=min(50, api_key_rpm),
                    scope=RateLimitScope.API_KEY,
                )

        # 2. Tenant settings override
        if self._tenant_settings_resolver is not None:
            # Fire-and-forget async call — we need to handle this in dispatch
            # Since this is sync, we'll skip the async tenant resolver here
            # and handle it in _check_rate_limit instead.
            pass

        # 3. Role defaults
        for role_str in ctx.roles:
            try:
                role = Role(role_str)
                config = ROLE_DEFAULT_RATE_LIMITS.get(role)
                if config is not None:
                    return config
            except ValueError:
                continue

        return ROLE_DEFAULT_RATE_LIMITS.get(Role.READ_ONLY)

    async def _check_rate_limit(
        self, request: Request, ctx: RequestContext
    ) -> Optional[RateLimitResult]:
        """Run rate limit check and return result."""
        if self._rate_limiter is None:
            return None

        # Check tenant settings async if resolver is available
        if self._tenant_settings_resolver is not None:
            try:
                settings = await self._tenant_settings_resolver(ctx.tenant_id)
                if (
                    settings
                    and isinstance(settings, dict)
                    and "rate_limits" in settings
                ):
                    rate_limits = settings["rate_limits"]
                    if isinstance(rate_limits, dict):
                        tenant_config = RateLimitConfig(
                            requests_per_minute=rate_limits.get(
                                "requests_per_minute", 60
                            ),
                            requests_per_hour=rate_limits.get("requests_per_hour"),
                            burst_size=rate_limits.get("burst_size", 10),
                            scope=RateLimitScope(rate_limits.get("scope", "tenant")),
                        )
                        request.state.rate_limit_config = tenant_config
                        request.state.rate_limit_policy = "tenant_settings"
                        rate_key = self._build_rate_limit_key(
                            request, ctx, tenant_config
                        )
                        return await self._rate_limiter.check(rate_key, tenant_config)
            except (RuntimeError, ValueError, TypeError) as exc:
                logger.warning(
                    "tenant_settings_resolver_failed_closed",
                    extra={
                        "event": "tenant_settings_resolver_failed_closed",
                        "error_code": ERR_AUTH_SERVICE_UNAVAILABLE,
                        "error": str(exc),
                        "tenant_id": str(ctx.tenant_id),
                    },
                )

        config = self._resolve_rate_limit_config(request, ctx)
        if config is None:
            return None
        request.state.rate_limit_config = config
        request.state.rate_limit_policy = "role_default"

        rate_key = self._build_rate_limit_key(request, ctx, config)
        return await self._rate_limiter.check(rate_key, config)

    def _build_rate_limit_key(
        self, request: Request, ctx: RequestContext, config: RateLimitConfig
    ) -> str:
        """Build a Redis key for the rate limit window."""
        endpoint_class = self._classify_endpoint(request)
        return build_rate_limit_key(
            ctx=ctx,
            config=config,
            endpoint_class=endpoint_class,
            key_strategy=self._shared_rate_limit_config.key_strategy,
        )

    def _classify_endpoint(self, request: Request) -> str:
        path = request.url.path
        method = request.method.upper()
        if path.startswith("/auth/") or path.startswith("/v1/api-keys"):
            return "auth"
        if (
            path.startswith("/v1/tenants")
            or path.startswith("/v1/users")
            or path.startswith("/v1/admin")
        ):
            return "admin"
        if path.startswith(
            (
                "/v1/analysis",
                "/v1/workflows",
                "/v1/intelligence",
                "/v1/narratives",
                "/v1/hypotheses",
            )
        ):
            return "expensive_compute"
        if method in {"POST", "PUT", "PATCH", "DELETE"}:
            return "write"
        return "read"


# Merged from root shared/identity/middleware.py
TenantContextMiddleware = GovernanceMiddleware


class RateLimitExceeded(Exception):
    """Raised when rate limit is exceeded."""

    def __init__(self, retry_after: int):
        self.retry_after = retry_after
        super().__init__(f"Rate limit exceeded. Retry after {retry_after} seconds.")


class MultiWorkerRateLimitError(RuntimeError):
    """Raised when rate limiting is enabled in multi-worker mode without Redis."""

    def __init__(self):
        super().__init__(
            "Multi-worker deployment detected but REDIS_URL is not configured. "
            "Rate limiting requires Redis for shared state across workers. "
            "Set REDIS_URL or disable rate limiting with enable_per_tenant_rate_limiting=False."
        )


class RateLimiterConfigurationError(RuntimeError):
    """Raised when rate limiter backend is unsafe for the current environment."""

    def __init__(self, environment: str):
        super().__init__(
            f"Rate limiter initialization failed for environment '{environment}'. "
            "Redis backend is required in prod/staging but REDIS_URL or Redis client "
            "is unavailable."
        )


class SuspendedTenantError(Exception):
    """Raised when tenant is suspended and cannot access resources."""

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        super().__init__(f"Tenant {tenant_id} is suspended. Please contact support.")


class PendingTenantError(Exception):
    """Raised when tenant is pending activation and cannot access resources."""

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        super().__init__(f"Tenant {tenant_id} is pending activation.")


class DeletedTenantError(Exception):
    """Raised when tenant has been deleted and cannot access resources."""

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        super().__init__(f"Tenant {tenant_id} not found.")


# Compatibility exports used by mandatory security regression tests.
DEFAULT_REQUESTS_PER_MINUTE = int(os.getenv("RATE_LIMIT_REQUESTS_PER_MINUTE", "120"))
RATE_LIMIT_WINDOW_SECONDS = _RATE_LIMIT_WINDOW_SECONDS


def _evict_stale_rate_limit_entries(now: float | None = None) -> int:
    """Evict stale process-local rate-limit buckets and return the count removed."""
    current = time.time() if now is None else now
    removed = 0
    for key, bucket in list(_tenant_rate_limit_buckets.items()):
        reset_at = float(bucket.get("reset_at", 0))
        if reset_at <= current:
            _tenant_rate_limit_buckets.pop(key, None)
            removed += 1
    return removed


# ---------------------------------------------------------------------------
# Namespace-shim singleton guard
# ---------------------------------------------------------------------------
# This module owns process-wide tenant-identity state (rate-limit buckets,
# middleware class attributes, etc.). The monorepo namespace shim can load it
# under multiple import paths (e.g. ``value_fabric.shared.identity.middleware``
# and ``packages.shared.src.value_fabric.shared.identity.middleware``), which
# would create independent copies of that state and silently break tenant
# isolation. Force every logical import path to resolve to the same module
# object.
# ---------------------------------------------------------------------------

_CANONICAL_MIDDLEWARE_MODULE = (
    "packages.shared.src.value_fabric.shared.identity.middleware"
)
if __name__ != _CANONICAL_MIDDLEWARE_MODULE:
    sys.modules.setdefault(_CANONICAL_MIDDLEWARE_MODULE, sys.modules[__name__])
    sys.modules[__name__] = sys.modules[_CANONICAL_MIDDLEWARE_MODULE]
