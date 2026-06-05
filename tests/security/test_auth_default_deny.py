from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from value_fabric.shared.fastapi_framework.middleware import add_governance_middleware
from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.middleware import GovernanceMiddleware, audit_protected_routes


def test_non_public_routes_default_to_auth_enforcement() -> None:
    app = FastAPI()
    add_governance_middleware(app)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/private")
    async def private() -> dict[str, str]:
        return {"status": "private"}

    client = TestClient(app)

    public_response = client.get("/health")
    assert public_response.status_code == 200

    private_response = client.get("/private")
    assert private_response.status_code == 401
    assert private_response.json()["error"] == "authentication_required"


def test_non_public_routes_require_tenant_context_centrally(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _resolve_without_tenant(self: GovernanceMiddleware, request):
        return RequestContext(user_id="user-1", roles=["viewer"], source="jwt")

    monkeypatch.setattr(GovernanceMiddleware, "_resolve_identity", _resolve_without_tenant)

    app = FastAPI()
    add_governance_middleware(app)

    @app.get("/private")
    async def private() -> dict[str, str]:  # pragma: no cover - blocked by middleware
        return {"status": "private"}

    response = TestClient(app).get("/private", headers={"Authorization": "Bearer test"})

    assert response.status_code == 403
    assert response.json()["error"] == "tenant_context_required"


def test_non_public_routes_with_tenant_context_reach_handler(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _resolve_with_tenant(self: GovernanceMiddleware, request):
        return RequestContext(tenant_id="11111111-1111-4111-8111-111111111111", user_id="user-1", roles=["viewer"], source="jwt")

    monkeypatch.setattr(GovernanceMiddleware, "_resolve_identity", _resolve_with_tenant)

    app = FastAPI()
    add_governance_middleware(app)

    @app.get("/private")
    async def private() -> dict[str, str]:
        return {"status": "private"}

    response = TestClient(app).get("/private", headers={"Authorization": "Bearer test"})

    assert response.status_code == 200
    assert response.json() == {"status": "private"}
    assert response.headers["X-Tenant-ID-Resolved"] == "11111111-1111-4111-8111-111111111111"


def test_route_audit_fails_when_central_governance_middleware_missing() -> None:
    app = FastAPI()

    @app.get("/oops")
    async def oops() -> dict[str, str]:
        return {"status": "oops"}

    with pytest.raises(RuntimeError, match="GovernanceMiddleware"):
        audit_protected_routes(app)


def test_route_audit_allows_centrally_protected_routes() -> None:
    app = FastAPI()
    add_governance_middleware(app)

    @app.get("/protected")
    async def protected() -> dict[str, str]:
        return {"status": "protected"}

    audit_protected_routes(app)
