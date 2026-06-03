"""Allowed service-local exception for Layer 3 service wrapper.

Owner: layer3-knowledge
Removal/migration target: 2026-09-30
Reason: Layer 3 request-limiting adapters and middleware.

Canonical sliding-window state math is implemented in
``value_fabric.shared.rate_limiting.tenant_rate_limiter``. This module must
only compose endpoint/client keys and map canonical decisions into HTTP
headers and response payload fields.
"""

import os
from typing import Any

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from value_fabric.shared.identity.authoritative_rate_limiter import (
    AuthoritativeRateLimiter,
    RateLimitDimensions,
)
from value_fabric.shared.models.typed_dict import TypedDictModel
from value_fabric.shared.rate_limiting.tenant_rate_limiter import SlidingWindowAdapter

from logging_config import get_logger

logger = get_logger(__name__)


class RateLimitMiddleware_get_statsResult(TypedDictModel):
    active_clients: Any
    endpoint_limits: Any
    total_requests: Any


class RateLimiter:
    """Rate limiter adapter that delegates counting to canonical state math."""

    def __init__(
        self,
        requests_per_window: int = 100,
        window_seconds: int = 60,
        redis_client: Any | None = None,
    ):
        self.requests_per_window = requests_per_window
        self.window_seconds = window_seconds
        self.endpoint_limits: dict[str, tuple[int, int]] = {}
        self._adapter = SlidingWindowAdapter(redis_client)
        self._clients_seen: set[str] = set()
        self._total_allowed_requests = 0

    def set_endpoint_limit(self, endpoint: str, requests: int, seconds: int) -> None:
        self.endpoint_limits[endpoint] = (requests, seconds)
        logger.info(f"Set rate limit for {endpoint}: {requests}/{seconds}s")

    def _get_client_key(self, request: Request) -> str:
        """Return a rate-limit key that resists IP spoofing.

        Priority:
          1. Authenticated identity (API key ID → tenant_id → governance_context.tenant_id)
          2. IP-based key ONLY when TRUSTED_PROXY_COUNT is configured and validated
          3. Direct connection IP as last resort
        """
        # 1. Prefer authenticated identity — never spoofable
        api_key = getattr(request.state, "authenticated_api_key", None)
        if api_key is not None:
            key_id = getattr(api_key, "key_id", None)
            if key_id:
                return f"key:{key_id}"

        tenant_id = getattr(request.state, "tenant_id", None)
        if tenant_id:
            return f"tenant:{tenant_id}"

        gov_ctx = getattr(request.state, "governance_context", None)
        if gov_ctx is not None:
            gov_tenant = getattr(gov_ctx, "tenant_id", None)
            if gov_tenant:
                return f"tenant:{gov_tenant}"

        # 2. IP-based fallback only when trusted proxy count is configured
        trusted_proxy_count_raw = os.getenv("TRUSTED_PROXY_COUNT", "").strip()
        if trusted_proxy_count_raw:
            try:
                trusted_proxy_count = int(trusted_proxy_count_raw)
            except ValueError:
                trusted_proxy_count = 0

            if trusted_proxy_count > 0:
                forwarded_for = request.headers.get("X-Forwarded-For")
                if forwarded_for:
                    # Parse from the right: take the Nth from last, where N = trusted_proxy_count
                    ips = [ip.strip() for ip in forwarded_for.split(",")]
                    if len(ips) >= trusted_proxy_count:
                        candidate = ips[-trusted_proxy_count]
                        if candidate:
                            return candidate

                real_ip = request.headers.get("X-Real-IP")
                if real_ip:
                    return real_ip.strip()

        # 3. Last resort: direct connection IP
        return request.client.host if request.client else "unknown"

    def _get_endpoint_limit(self, path: str) -> tuple[int, int]:
        for endpoint_pattern, (requests, seconds) in self.endpoint_limits.items():
            if endpoint_pattern in path:
                return requests, seconds

        return self.requests_per_window, self.window_seconds

    async def is_allowed(self, request: Request) -> tuple[bool, dict[str, int]]:
        client_key = self._get_client_key(request)
        path = request.url.path
        requests_limit, window_seconds = self._get_endpoint_limit(path)

        decision = await self._adapter.check(
            key=f"ratelimit:layer3:{client_key}:{path}:{window_seconds}",
            limit=requests_limit,
            window_seconds=window_seconds,
        )

        self._clients_seen.add(client_key)
        if decision.allowed:
            self._total_allowed_requests += 1

        return decision.allowed, {
            "limit": decision.limit,
            "remaining": decision.remaining,
            "reset": decision.reset_epoch,
            "retry_after": decision.retry_after or window_seconds,
        }


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware for FastAPI applications."""

    def __init__(
        self,
        app,
        requests_per_minute: int = 100,
        burst_size: int = 200,
        enabled: bool = True,
    ):
        super().__init__(app)
        self.enabled = enabled
        self.rate_limiter = RateLimiter(requests_per_window=burst_size, window_seconds=60)
        self.rate_limiter.set_endpoint_limit("*", requests_per_minute, 60)
        self._configure_endpoint_limits()

    def _configure_endpoint_limits(self) -> None:
        # Route-class policy: auth endpoints (tight limits, low burst).
        self.rate_limiter.set_endpoint_limit("/v1/auth", 30, 60)
        self.rate_limiter.set_endpoint_limit("/auth", 30, 60)
        # Route-class policy: write-heavy endpoints (moderate sustained throughput).
        self.rate_limiter.set_endpoint_limit("/v1/ingest", 80, 60)
        self.rate_limiter.set_endpoint_limit("/v1/sync", 40, 60)
        self.rate_limiter.set_endpoint_limit("/v1/schema/init", 12, 60)
        # Route-class policy: export/report endpoints (expensive operations, tighter ceiling).
        self.rate_limiter.set_endpoint_limit("/v1/export", 20, 60)
        self.rate_limiter.set_endpoint_limit("/v1/report", 20, 60)

        self.rate_limiter.set_endpoint_limit("/health", 300, 60)
        self.rate_limiter.set_endpoint_limit("/health/detailed", 60, 60)
        self.rate_limiter.set_endpoint_limit("/v1/schema/status", 60, 60)
        self.rate_limiter.set_endpoint_limit("/v1/schema/statistics", 30, 60)
        self.rate_limiter.set_endpoint_limit("/v1/search", 200, 60)
        self.rate_limiter.set_endpoint_limit("/v1/graphrag", 100, 60)
        self.rate_limiter.set_endpoint_limit("/v1/analytics", 30, 60)
        self.rate_limiter.set_endpoint_limit("/v1/similarity", 50, 60)
        logger.info("Rate limiting configured for all endpoints")

    @staticmethod
    def _apply_rate_limit_headers(response: Response, rate_limit_info: dict[str, int], *, remaining: int | None = None) -> None:
        remaining_value = rate_limit_info["remaining"] if remaining is None else remaining
        response.headers["X-RateLimit-Limit"] = str(rate_limit_info["limit"])
        response.headers["X-RateLimit-Remaining"] = str(remaining_value)
        response.headers["X-RateLimit-Reset"] = str(rate_limit_info["reset"])

    async def dispatch(self, request: Request, call_next) -> Response:
        if not self.enabled:
            return await call_next(request)

        is_allowed, rate_limit_info = await self.rate_limiter.is_allowed(request)
        if not is_allowed:
            logger.warning(
                "Rate limit exceeded",
                extra={
                    "client_ip": self.rate_limiter._get_client_key(request),
                    "path": request.url.path,
                    "limit": rate_limit_info["limit"],
                    "retry_after": rate_limit_info["retry_after"],
                },
            )
            response = JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded",
                    "error": "Too many requests",
                    "retry_after": rate_limit_info["retry_after"],
                },
            )
            response.headers["Retry-After"] = str(rate_limit_info["retry_after"])
            self._apply_rate_limit_headers(response, rate_limit_info, remaining=0)
            return response

        response = await call_next(request)
        self._apply_rate_limit_headers(response, rate_limit_info)
        return response

    def enable(self) -> None:
        self.enabled = True
        logger.info("Rate limiting enabled")

    def disable(self) -> None:
        self.enabled = False
        logger.info("Rate limiting disabled")

    def get_stats(self) -> dict[str, int]:
        return RateLimitMiddleware_get_statsResult.model_validate(
            {
                "active_clients": len(self.rate_limiter._clients_seen),
                "total_requests": self.rate_limiter._total_allowed_requests,
                "endpoint_limits": len(self.rate_limiter.endpoint_limits),
            }
        )


def add_rate_limiting(
    app,
    requests_per_minute: int = 100,
    burst_size: int = 200,
    enabled: bool = True,
) -> RateLimitMiddleware:
    middleware = RateLimitMiddleware(
        app,
        requests_per_minute=requests_per_minute,
        burst_size=burst_size,
        enabled=enabled,
    )

    logger.info(
        "Rate limiting middleware added",
        extra={
            "requests_per_minute": requests_per_minute,
            "burst_size": burst_size,
            "enabled": enabled,
        },
    )

    return middleware


TIER_RATE_LIMITS: dict[str, int] = {
    "free": 60,
    "pro": 600,
    "enterprise": 6000,
    "system": 100_000,
}


class TenantRateLimiter:
    """Layer 3 compatibility adapter over authoritative identity rate limiter."""

    def __init__(self, redis_client=None) -> None:
        self._authoritative = AuthoritativeRateLimiter(redis_client)

    async def check(
        self,
        *,
        tenant_id,
        tier: str = "free",
        api_key_id: str | None = None,
        key_limit: int | None = None,
        window_seconds: int = 60,
    ) -> tuple[bool, dict[str, int]]:
        from value_fabric.shared.identity.rate_limiting import RateLimitConfig

        tenant_limit = key_limit or TIER_RATE_LIMITS.get(tier, TIER_RATE_LIMITS["free"])
        decision = await self._authoritative.evaluate(
            RateLimitDimensions(
                tenant_id=str(tenant_id),
                endpoint_class="layer3",
                api_key_id=api_key_id,
            ),
            RateLimitConfig(requests_per_minute=tenant_limit, burst_size=max(1, tenant_limit // 10)),
        )
        headers = {
            "limit": decision.limit,
            "remaining": decision.remaining,
            "reset": decision.reset_epoch,
            "retry_after": decision.retry_after or 0,
        }
        return decision.allowed, headers
