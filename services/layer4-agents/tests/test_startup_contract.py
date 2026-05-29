from __future__ import annotations

from fastapi.testclient import TestClient
import pytest

from layer4_agents.api.app_factory import create_app
from layer4_agents.api.startup import (
    StartupCheckResult,
    check_database_ready,
    check_redis_ready,
    check_vault_ready,
)


@pytest.mark.asyncio
async def test_dependency_checks_contract(monkeypatch):
    async def ok_db():
        return None

    async def ok_ping():
        return True

    class RedisStub:
        async def ping(self):
            return await ok_ping()

    monkeypatch.setattr("layer4_agents.api.startup.init_db", ok_db)
    db_result = await check_database_ready()
    assert isinstance(db_result, StartupCheckResult)
    assert db_result.ok is True

    redis_result = await check_redis_ready(RedisStub())
    assert redis_result.name == "redis"
    assert redis_result.ok is True

    vault_result = await check_vault_ready(environment="development", vault_addr=None)
    assert vault_result.ok is True


@pytest.mark.asyncio
async def test_dependency_checks_fail_contract(monkeypatch):
    async def fail_db():
        raise RuntimeError("db down")

    monkeypatch.setattr("layer4_agents.api.startup.init_db", fail_db)
    db_result = await check_database_ready()
    assert db_result.ok is False
    assert "db down" in (db_result.detail or "")


def test_route_table_integrity_after_refactor():
    app = create_app()
    paths = {route.path for route in app.routes}
    assert "/" in paths
    assert "/health" in paths
    assert "/metrics" in paths
    assert any(p.startswith("/v1/workflows") for p in paths)


def test_request_id_middleware_contract_is_canonical_and_stable(monkeypatch):
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def _noop_lifespan(app):
        yield

    # Bypass all infrastructure startup checks (DB, Redis, checkpoint, etc.)
    monkeypatch.setattr("layer4_agents.api.app_factory.build_lifespan", lambda **_: _noop_lifespan)

    app = create_app()

    middleware_names = [mw.cls.__name__ for mw in app.user_middleware]
    assert middleware_names.count("BaseHTTPMiddleware") == 1

    with TestClient(app) as client:
        response = client.get("/health", headers={"X-Correlation-ID": "corr-layer4-1"})

    assert response.status_code == 200
    assert response.headers.get("X-Request-ID") == "corr-layer4-1"
    assert response.headers.get("X-Correlation-ID") == "corr-layer4-1"
    assert response.headers.get("X-Trace-ID") == "corr-layer4-1"
