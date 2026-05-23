from __future__ import annotations

import pytest

from value_fabric.layer3.api.rate_limiter import RateLimiter, TenantRateLimiter


@pytest.mark.asyncio
async def test_layer3_tenant_rate_limiter_headers_and_reset_semantics() -> None:
    limiter = TenantRateLimiter(redis_client=None)

    allowed_1, headers_1 = await limiter.check(tenant_id="t1", tier="free", window_seconds=60)
    allowed_2, headers_2 = await limiter.check(tenant_id="t1", tier="free", window_seconds=60)

    assert allowed_1 is True
    assert allowed_2 is True
    assert {"limit", "remaining", "reset"} <= set(headers_1.keys())
    assert headers_2["remaining"] <= headers_1["remaining"]
    assert headers_2["reset"] >= headers_1["reset"]


class _Req:
    def __init__(self) -> None:
        self.headers = {}
        self.client = type("C", (), {"host": "127.0.0.1"})()
        self.url = type("U", (), {"path": "/v1/search"})()


@pytest.mark.asyncio
async def test_layer3_api_rate_limiter_standardized_contract() -> None:
    limiter = RateLimiter(requests_per_window=2, window_seconds=60)
    req = _Req()

    allowed_1, info_1 = await limiter.is_allowed(req)
    allowed_2, info_2 = await limiter.is_allowed(req)
    allowed_3, info_3 = await limiter.is_allowed(req)

    assert allowed_1 is True
    assert allowed_2 is True
    assert allowed_3 is False
    assert {"limit", "remaining", "reset", "retry_after"} <= set(info_3.keys())
    assert info_2["remaining"] <= info_1["remaining"]
    assert info_3["retry_after"] >= 0
