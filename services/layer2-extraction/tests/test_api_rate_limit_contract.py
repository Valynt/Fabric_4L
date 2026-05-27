from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from value_fabric.shared.identity.api_key_stub import reject_api_key_unsupported
from value_fabric.shared.identity.middleware import GovernanceMiddleware


class _StubRateLimiter:
    def __init__(self) -> None:
        self.calls = 0

    async def check(self, key: str, config):
        self.calls += 1
        now = 1_700_000_000
        if self.calls == 1:
            return type("_Result", (), {"allowed": True, "remaining": 0, "reset_at": now + 60, "retry_after": None})()
        return type("_Result", (), {"allowed": False, "remaining": 0, "reset_at": now + 60, "retry_after": 60})()


def _build_contract_app(monkeypatch: pytest.MonkeyPatch) -> tuple[TestClient, _StubRateLimiter]:
    tenant_id = str(uuid4())
    user_id = str(uuid4())
    monkeypatch.setattr(
        "value_fabric.shared.identity.middleware.decode_jwt",
        lambda token: {"tenant_id": tenant_id, "sub": user_id, "roles": ["viewer"]},
    )

    app = FastAPI()
    limiter = _StubRateLimiter()
    app.add_middleware(
        GovernanceMiddleware,
        api_key_resolver=reject_api_key_unsupported,
        rate_limiter=limiter,
        enforce_authentication=True,
    )

    @app.get("/v1/protected")
    async def protected():
        return {"ok": True}

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    return TestClient(app), limiter


def test_repeated_authenticated_requests_return_429_with_stable_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    client, _ = _build_contract_app(monkeypatch)
    headers = {"Authorization": "Bearer test-token"}

    first = client.get("/v1/protected", headers=headers)
    assert first.status_code == 200

    second = client.get("/v1/protected", headers=headers)
    assert second.status_code == 429
    assert second.headers["X-RateLimit-Limit"].isdigit()
    assert second.headers["X-RateLimit-Remaining"] == "0"
    assert second.headers["X-RateLimit-Reset"].isdigit()
    assert second.headers["X-RateLimit-Scope"] in {"tenant", "user", "api_key"}
    assert second.headers["Retry-After"] == "60"
    assert second.json() == {
        "detail": "Rate limit exceeded",
        "error": "Too many requests",
        "retry_after": 60,
    }


def test_health_route_is_explicitly_exempt_from_rate_limiting(monkeypatch: pytest.MonkeyPatch) -> None:
    client, limiter = _build_contract_app(monkeypatch)

    health = client.get("/health")
    assert health.status_code == 200
    assert limiter.calls == 0
