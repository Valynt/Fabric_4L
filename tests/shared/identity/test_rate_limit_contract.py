from __future__ import annotations

import pytest
from value_fabric.shared.identity.rate_limiter import RedisRateLimiter
from value_fabric.shared.identity.rate_limiting import RateLimitConfig


@pytest.mark.asyncio
async def test_identity_rate_limiter_contract_fields_and_reset_semantics() -> None:
    limiter = RedisRateLimiter(redis_client=None)
    config = RateLimitConfig(requests_per_minute=2, burst_size=1)

    first = await limiter.check("tenant:abc", config)
    second = await limiter.check("tenant:abc", config)
    third = await limiter.check("tenant:abc", config)

    assert first.allowed is True
    assert second.allowed is True
    assert third.allowed is False
    assert isinstance(third.retry_after, int)
    assert third.retry_after >= 0
    assert third.reset_at >= first.reset_at
    assert {"allowed", "remaining", "reset_at", "retry_after"} <= set(third.__dict__.keys())
