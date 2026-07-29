from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from value_fabric.shared.identity.middleware import GovernanceMiddleware
from value_fabric.shared.identity.rate_limiter import RedisRateLimiter
from value_fabric.shared.identity.rate_limiting import RateLimitConfig

from layer4_agents.api.middleware import configure_middleware
from layer4_agents.api.runtime_state import runtime_state


@pytest.mark.asyncio
async def test_configure_middleware_uses_runtime_redis_proxy(monkeypatch) -> None:
    app = FastAPI()
    configure_middleware(app)

    governance = next(
        middleware
        for middleware in app.user_middleware
        if middleware.cls is GovernanceMiddleware
    )
    proxy = governance.options["rate_limiter"]

    sentinel_redis = object()
    original_state_manager = runtime_state.state_manager
    runtime_state.state_manager = SimpleNamespace(redis_client=sentinel_redis)

    observed: dict[str, object] = {}

    async def _fake_check(self, key: str, config: RateLimitConfig):
        observed["redis_client"] = self.redis_client
        observed["key"] = key
        observed["config"] = config
        return "rate-limit-result"

    monkeypatch.setattr(RedisRateLimiter, "check", _fake_check)

    try:
        result = await proxy.check(
            "tenant:read",
            RateLimitConfig(requests_per_minute=60, burst_size=10),
        )
    finally:
        runtime_state.state_manager = original_state_manager

    assert proxy.redis_client is sentinel_redis
    assert observed["redis_client"] is sentinel_redis
    assert observed["key"] == "tenant:read"
    assert result == "rate-limit-result"
