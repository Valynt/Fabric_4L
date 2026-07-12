from __future__ import annotations

import os
from unittest.mock import patch

import pytest
from value_fabric.shared.identity.authoritative_rate_limiter import (
    AuthoritativeRateLimiter,
    RateLimitDimensions,
)
from value_fabric.shared.identity.rate_limiting import RateLimitConfig


@pytest.mark.asyncio
async def test_redis_outage_fail_closed_protected_route_contract() -> None:
    limiter = AuthoritativeRateLimiter(redis_client=None)

    async def boom(*, key: str, limit: int, window_seconds: int):
        raise RuntimeError("redis unavailable")

    limiter._adapter.check = boom  # type: ignore[method-assign]

    with patch.dict(os.environ, {"RATE_LIMIT_FAIL_MODE": "closed"}, clear=False):
        result = await limiter.evaluate(
            RateLimitDimensions(tenant_id="t1", endpoint_class="read", user_id="u1", source_ip="1.2.3.4"),
            RateLimitConfig(requests_per_minute=60, burst_size=5),
        )

    assert result.allowed is False
    assert result.retry_after is not None
    assert "Retry-After" in result.as_headers()


@pytest.mark.asyncio
async def test_burst_traffic_degraded_safe_cap_is_conservative() -> None:
    limiter = AuthoritativeRateLimiter(redis_client=None)

    async def boom(*, key: str, limit: int, window_seconds: int):
        raise RuntimeError("redis unavailable")

    limiter._adapter.check = boom  # type: ignore[method-assign]

    with patch.dict(os.environ, {"RATE_LIMIT_FAIL_MODE": "local_fallback"}, clear=False):
        outcomes = [
            await limiter.evaluate(
                RateLimitDimensions(tenant_id="t1", endpoint_class="read", api_key_id="k1"),
                RateLimitConfig(requests_per_minute=200, burst_size=20),
            )
            for _ in range(6)
        ]

    assert all(item.allowed for item in outcomes[:5])
    assert outcomes[5].allowed is False


@pytest.mark.asyncio
async def test_multi_worker_dimension_consistency_uses_most_restrictive_dimension() -> None:
    limiter = AuthoritativeRateLimiter(redis_client=None)
    config = RateLimitConfig(requests_per_minute=2, burst_size=1)

    dim_a = RateLimitDimensions(tenant_id="tenant-a", endpoint_class="read", user_id="u1", source_ip="10.0.0.1")
    dim_b = RateLimitDimensions(tenant_id="tenant-a", endpoint_class="read", user_id="u1", source_ip="10.0.0.1")

    a1 = await limiter.evaluate(dim_a, config)
    b1 = await limiter.evaluate(dim_b, config)
    a2 = await limiter.evaluate(dim_a, config)

    assert a1.allowed is True
    assert b1.allowed is True
    assert a2.allowed is False
