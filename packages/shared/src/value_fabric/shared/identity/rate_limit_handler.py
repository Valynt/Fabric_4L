"""Rate limiting handler for the governance middleware.

Encapsulates rate limit checking, response building, header management,
endpoint classification, and process-local fallback buckets.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Callable, Optional

from fastapi import Request, Response
from fastapi.responses import JSONResponse

from .constants import ERR_AUTH_SERVICE_UNAVAILABLE, _RATE_LIMIT_WINDOW_SECONDS
from .context import RequestContext
from .exceptions import MultiWorkerRateLimitError
from .logging_helpers import _request_log_context
from .permissions import Role
from .rate_limiter import RateLimitResult, RedisRateLimiter
from .rate_limiting import RateLimitConfig, RateLimitScope, ROLE_DEFAULT_RATE_LIMITS
from value_fabric.shared.rate_limiting.http_middleware import (
    SharedRateLimitMiddlewareConfig,
    build_rate_limit_key,
    should_skip_rate_limit,
)

logger = logging.getLogger(__name__)

# Process-local fallback used only by lightweight regression tests and single-worker
# development paths. Production middleware should use RedisRateLimiter so quotas are
# shared across workers and pods.
_tenant_rate_limit_buckets: dict[str, tuple[float, int]] = {}


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


def _get_worker_count() -> int:
    """Return the configured uvicorn worker count for rate limiter safety checks."""
    worker_count_raw = os.getenv("UVICORN_WORKERS", "1") or "1"
    try:
        return int(worker_count_raw)
    except ValueError:
        return 1


def _validate_multi_worker_rate_limit_configuration(
    rate_limiter: Optional[RedisRateLimiter],
) -> None:
    """Fail closed when multi-worker deployments lack shared rate limits."""
    if _get_worker_count() > 1 and rate_limiter is None:
        raise MultiWorkerRateLimitError()


class RateLimitHandler:
    """Encapsulates rate limit checking, response building, and header management."""

    def __init__(
        self,
        rate_limiter: Optional[RedisRateLimiter] = None,
        tenant_settings_resolver: Optional[Callable] = None,
        on_rate_limit_hit: Optional[Callable[[str, str], None]] = None,
    ) -> None:
        self._rate_limiter = rate_limiter
        self._tenant_settings_resolver = tenant_settings_resolver
        self._on_rate_limit_hit = on_rate_limit_hit
        self._shared_rate_limit_config = SharedRateLimitMiddlewareConfig.from_env()

    async def check_rate_limit_before_request(
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

    async def add_rate_limit_headers(
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
