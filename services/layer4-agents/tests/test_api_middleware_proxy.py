from __future__ import annotations

from contextlib import asynccontextmanager
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi import FastAPI
from value_fabric.shared.identity.middleware import GovernanceMiddleware
from value_fabric.shared.identity.rate_limiter import RedisRateLimiter
from value_fabric.shared.identity.rate_limiting import RateLimitConfig

from layer4_agents.api import middleware as api_middleware
from layer4_agents.api.middleware import configure_middleware
from layer4_agents.api.runtime_state import runtime_state


@pytest.mark.asyncio
async def test_configure_middleware_uses_runtime_redis_proxy(monkeypatch) -> None:
    app = FastAPI()
    configure_middleware(app)

    governance = next(
        middleware for middleware in app.user_middleware if middleware.cls is GovernanceMiddleware
    )
    proxy = governance.kwargs["rate_limiter"]

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
        assert proxy.redis_client is sentinel_redis
        assert observed["redis_client"] is sentinel_redis
        assert observed["key"] == "tenant:read"
        assert result == "rate-limit-result"
    finally:
        runtime_state.state_manager = original_state_manager


@pytest.mark.asyncio
async def test_tenant_settings_lookup_normalizes_tenant_uuid(monkeypatch) -> None:
    observed: dict[str, object] = {}
    sentinel_db = SimpleNamespace(
        get_bind=lambda: SimpleNamespace(dialect=SimpleNamespace(name="postgresql"))
    )

    @asynccontextmanager
    async def _fake_session(context):
        observed["context_tenant_id"] = context.tenant_id
        yield sentinel_db

    async def _fake_settings(db, tenant_id):
        observed["db"] = db
        observed["settings_tenant_id"] = tenant_id
        return {"rate_limit": 60}

    monkeypatch.setattr(api_middleware, "db_session_for_context", _fake_session)
    monkeypatch.setattr(api_middleware, "get_tenant_settings", _fake_settings)

    result = await api_middleware._tenant_settings_lookup("550e8400-e29b-41d4-a716-446655440000")

    assert result == {"rate_limit": 60}
    assert observed["db"] is sentinel_db
    assert observed["settings_tenant_id"] == UUID("550e8400-e29b-41d4-a716-446655440000")


@pytest.mark.asyncio
async def test_tenant_settings_lookup_uses_defaults_for_non_postgres(monkeypatch) -> None:
    sqlite_db = SimpleNamespace(
        get_bind=lambda: SimpleNamespace(dialect=SimpleNamespace(name="sqlite"))
    )

    @asynccontextmanager
    async def _fake_session(context):
        yield sqlite_db

    async def _unexpected_settings_lookup(db, tenant_id):
        raise AssertionError("tenant settings query must not run on non-PostgreSQL")

    monkeypatch.setattr(api_middleware, "db_session_for_context", _fake_session)
    monkeypatch.setattr(
        api_middleware,
        "get_tenant_settings",
        _unexpected_settings_lookup,
    )

    assert (
        await api_middleware._tenant_settings_lookup("550e8400-e29b-41d4-a716-446655440000") is None
    )
