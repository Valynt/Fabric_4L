"""Shared Identity adapter over canonical runtime request limiting.

Canonical module decision: ``value_fabric.shared.rate_limiting.tenant_rate_limiter``
is the only location that owns sliding-window counter semantics.

Canonical state math lives in ``value_fabric.shared.rate_limiting.tenant_rate_limiter``.
This module keeps identity-facing config/result shapes while delegating checks
through a narrow adapter interface.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any

from .rate_limiting import RateLimitConfig, RateLimitFailMode, get_rate_limit_fail_mode
from ..rate_limiting.tenant_rate_limiter import SlidingWindowAdapter

logger = logging.getLogger(__name__)

_LOCAL_FALLBACK_LIMIT = 5
_FALLBACK_EVENTS_COUNTER = 0


@dataclass
class RateLimitResult:
    """Outcome of a rate limit check."""

    allowed: bool
    remaining: int
    reset_at: float
    retry_after: int | None


class _LocalFallbackRateLimiter:
    """Strict bounded fallback adapter for Redis outage conditions."""

    def __init__(self) -> None:
        self._adapter = SlidingWindowAdapter(redis_client=None)

    async def check(self, key: str, window_seconds: int) -> RateLimitResult:
        decision = await self._adapter.check(
            key=key,
            limit=_LOCAL_FALLBACK_LIMIT,
            window_seconds=window_seconds,
        )
        return RateLimitResult(
            allowed=decision.allowed,
            remaining=decision.remaining,
            reset_at=float(decision.reset_epoch),
            retry_after=decision.retry_after,
        )


class RedisRateLimiter:
    """Identity adapter that delegates sliding-window math to the canonical module."""

    def __init__(self, redis_client: Any | None = None, *, fail_open: bool | None = None) -> None:
        self._adapter = SlidingWindowAdapter(redis_client)
        self._fallback_limiter = _LocalFallbackRateLimiter()
        self._legacy_fail_open = fail_open

    @property
    def redis_client(self) -> Any | None:
        """Return the underlying Redis client for shared infrastructure adapters."""
        return self._adapter._redis

    async def check(self, key: str, config: RateLimitConfig) -> RateLimitResult:
        """Check whether a request is allowed under the given config."""
        if config.requests_per_hour is not None:
            window = 3600
            limit = config.requests_per_hour
        else:
            window = 60
            limit = config.requests_per_minute

        try:
            decision = await self._adapter.check(key=key, limit=limit, window_seconds=window)
            return RateLimitResult(
                allowed=decision.allowed,
                remaining=decision.remaining,
                reset_at=float(decision.reset_epoch),
                retry_after=decision.retry_after,
            )
        except Exception as exc:
            if self._legacy_fail_open is True:
                now = time.time()
                return RateLimitResult(
                    allowed=True,
                    remaining=-1,
                    reset_at=now + window,
                    retry_after=None,
                )
            if self._legacy_fail_open is False:
                now = time.time()
                return RateLimitResult(
                    allowed=False,
                    remaining=0,
                    reset_at=now + window,
                    retry_after=window,
                )

            fail_mode = get_rate_limit_fail_mode()
            self._record_fallback_activation(key=key, mode=fail_mode, error=exc)
            if fail_mode is RateLimitFailMode.LOCAL_FALLBACK:
                return await self._fallback_limiter.check(key=key, window_seconds=window)

            now = time.time()
            retry_after = max(1, min(window, 60))
            return RateLimitResult(
                allowed=False,
                remaining=0,
                reset_at=now + retry_after,
                retry_after=retry_after,
            )

    def _record_fallback_activation(self, *, key: str, mode: RateLimitFailMode, error: Exception) -> None:
        global _FALLBACK_EVENTS_COUNTER
        _FALLBACK_EVENTS_COUNTER += 1
        logger.error(
            "rate_limit_backend_failure",
            extra={
                "event": "rate_limit_backend_failure",
                "severity": "critical",
                "counter": _FALLBACK_EVENTS_COUNTER,
                "fallback_mode": mode.value,
                "rate_limit_key": key,
                "alert": "RATE_LIMIT_FALLBACK_ACTIVATED",
                "error_type": type(error).__name__,
            },
        )
