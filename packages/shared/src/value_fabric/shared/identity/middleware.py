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

import logging
from contextvars import Token
from typing import Callable, Optional
from uuid import UUID

from fastapi import HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from value_fabric.shared.tenant_kill_switch import (
    TenantKillSwitch,
    TenantSuspensionStatus,
)

from .audit import audit_protected_routes
from .compat import register_middleware_module
from .constants import (
    _LEGACY_TEST_TENANT_ID_RE,
    _RATE_LIMIT_WINDOW_SECONDS,
    DEFAULT_REQUESTS_PER_MINUTE,
    ERR_AUTH_CONTEXT_INVALID,
    ERR_AUTH_INVALID_TOKEN,
    ERR_AUTH_SERVICE_UNAVAILABLE,
    EXTERNAL_AUTH_BOOTSTRAP_ALLOWLIST,
    MIN_SERVICE_SECRET_LENGTH,
    RATE_LIMIT_WINDOW_SECONDS,
    SERVICE_AUTH_HEADER,
    SESSION_COOKIE_NAME,
    TENANT_ID_HEADER,
    _is_external_auth_bootstrap_path,
)
from .context import (
    RequestContext,
    _current_context,
    set_request_context,
)
from .context_builders import (
    _KNOWN_PERMISSION_VALUES,
    _allow_legacy_test_tenant_ids,
    _coerce_tenant_id_for_context,
    _is_known_permission,
    extract_context_from_api_key,
    extract_context_from_jwt,
    lookup_api_key,
    validate_context_consistency,
)
from .context_builders import (
    build_context_from_role as _build_context_from_role,
)
from value_fabric.shared.tenant_context_metrics import record_inconsistent_tenant_context_access
from .exceptions import (
    DeletedTenantError,
    MultiWorkerRateLimitError,
    PendingTenantError,
    RateLimiterConfigurationError,
    RateLimitExceeded,
    SuspendedTenantError,
)
from .jwt_wrapper import decode_jwt
from .logging_helpers import _request_log_context
from .rate_limit_handler import (
    RateLimitHandler,
    _check_tenant_rate_limit,
    _evict_stale_rate_limit_entries,
    _get_worker_count,
    _tenant_rate_limit_buckets,
    _validate_multi_worker_rate_limit_configuration,
)
from .rate_limiter import RateLimitResult, RedisRateLimiter
from .rate_limiting import ROLE_DEFAULT_RATE_LIMITS, RateLimitConfig, RateLimitScope
from .resolvers import (
    build_context_from_claims,
    resolve_api_key,
    resolve_bearer_jwt,
    resolve_identity,
    resolve_s2s_jwt,
    resolve_service_to_service,
    resolve_session_cookie,
)
from .tenant_status import enforce_tenant_status

logger = logging.getLogger(__name__)

# Register this module under canonical and compat import paths.
register_middleware_module(__name__)


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
        app: ASGIApp,
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
        _validate_multi_worker_rate_limit_configuration(rate_limiter)
        self._rate_limit_handler = RateLimitHandler(
            rate_limiter=rate_limiter,
            tenant_settings_resolver=tenant_settings_resolver,
            on_rate_limit_hit=on_rate_limit_hit,
        )
        # P0 FIX: Query param tenant authentication removed entirely
        self._allow_query_param = False

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        token: Token[RequestContext | None] = _current_context.set(None)  # always reset at start
        ctx: Optional[RequestContext] = None

        try:
            try:
                ctx = await self._handle_authentication(request)
            except HTTPException as exc:
                error = "authentication_required"
                if isinstance(exc.detail, dict):
                    error = str(exc.detail.get("error") or error)
                return JSONResponse(
                    status_code=exc.status_code,
                    headers=exc.headers or {"WWW-Authenticate": "Bearer"},
                    content={"detail": exc.detail, "error": error},
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
            rate_limit_response = (
                await self._rate_limit_handler.check_rate_limit_before_request(
                    request, ctx
                )
            )
            if rate_limit_response is not None:
                return rate_limit_response

            response = await call_next(request)

        finally:
            _current_context.reset(token)

        if ctx is not None:
            response.headers["X-Tenant-ID-Resolved"] = str(ctx.tenant_id)
            await self._rate_limit_handler.add_rate_limit_headers(
                response, request, ctx
            )

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

    def _set_request_context(
        self, ctx: RequestContext, token: Token[RequestContext | None]
    ) -> Token[RequestContext | None]:
        """Set the request context in the context var and return new token."""
        _current_context.reset(token)
        return set_request_context(ctx)

    # ------------------------------------------------------------------
    # Resolution helpers — delegate to resolvers module but keep as methods
    # for backward compatibility with tests that call them directly.
    # ------------------------------------------------------------------

    async def _resolve_identity(self, request: Request) -> Optional[RequestContext]:
        raw_tenant_header = request.headers.get(TENANT_ID_HEADER)
        if raw_tenant_header is not None:
            try:
                UUID(raw_tenant_header)
            except ValueError:
                return None
        return await resolve_identity(request, self._api_key_resolver)

    async def _resolve_bearer_jwt(self, request: Request) -> Optional[RequestContext]:
        return await resolve_bearer_jwt(request)

    async def _resolve_s2s_jwt(
        self, token_str: str, request: Request
    ) -> Optional[RequestContext]:
        return await resolve_s2s_jwt(token_str, request)

    async def _resolve_session_cookie(
        self, request: Request
    ) -> Optional[RequestContext]:
        return await resolve_session_cookie(request)

    async def _resolve_api_key(self, request: Request) -> Optional[RequestContext]:
        return await resolve_api_key(request, self._api_key_resolver)

    async def _resolve_service_to_service(
        self, request: Request
    ) -> Optional[RequestContext]:
        return await resolve_service_to_service(request)

    def _build_context_from_claims(
        self, claims: object, request: Request
    ) -> RequestContext:
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

    async def _enforce_tenant_status(
        self, ctx: RequestContext
    ) -> Optional[Response]:
        """Return a blocking response for inactive tenant lifecycle states."""
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

        if tenant_status is None and ctx.raw:
            raw_tenant_status = ctx.raw.get("tenant_status")
            if raw_tenant_status in {"suspended", "pending", "deleted"}:
                tenant_status = raw_tenant_status

        if tenant_status is None:
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

    # ------------------------------------------------------------------
    # Rate limiting helpers — delegate to RateLimitHandler
    # ------------------------------------------------------------------

    async def _check_rate_limit_before_request(
        self, request: Request, ctx: Optional[RequestContext]
    ) -> Optional[Response]:
        self._rate_limit_handler._rate_limiter = self._rate_limiter
        return await self._rate_limit_handler.check_rate_limit_before_request(
            request, ctx
        )

    async def _add_rate_limit_headers(
        self, response: Response, request: Request, ctx: Optional[RequestContext]
    ) -> None:
        self._rate_limit_handler._rate_limiter = self._rate_limiter
        await self._rate_limit_handler.add_rate_limit_headers(response, request, ctx)

    def _resolve_rate_limit_config(
        self, request: Request, ctx: RequestContext
    ) -> Optional[RateLimitConfig]:
        self._rate_limit_handler._rate_limiter = self._rate_limiter
        return self._rate_limit_handler._resolve_rate_limit_config(request, ctx)

    async def _check_rate_limit(
        self, request: Request, ctx: RequestContext
    ) -> Optional[RateLimitResult]:
        self._rate_limit_handler._rate_limiter = self._rate_limiter
        return await self._rate_limit_handler._check_rate_limit(request, ctx)

    def _build_rate_limit_key(
        self, request: Request, ctx: RequestContext, config: RateLimitConfig
    ) -> str:
        return self._rate_limit_handler._build_rate_limit_key(request, ctx, config)

    def _classify_endpoint(self, request: Request) -> str:
        return self._rate_limit_handler._classify_endpoint(request)

    @staticmethod
    def _validate_multi_worker_rate_limit_configuration(
        rate_limiter: Optional[RedisRateLimiter],
    ) -> None:
        _validate_multi_worker_rate_limit_configuration(rate_limiter)


# Merged from root shared/identity/middleware.py
TenantContextMiddleware = GovernanceMiddleware
