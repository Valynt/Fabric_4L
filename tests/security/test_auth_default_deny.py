from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from value_fabric.shared.fastapi_framework.middleware import add_governance_middleware
from value_fabric.shared.identity.audit import audit_protected_routes
from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.middleware import GovernanceMiddleware

_TENANT_ID = "11111111-1111-4111-8111-111111111111"


def _tenant_context(*, tenant_status: str | None = None) -> RequestContext:
    raw = {"tenant_status": tenant_status} if tenant_status is not None else {}
    return RequestContext(
        tenant_id=_TENANT_ID,
        user_id="user-1",
        roles=["viewer"],
        source="jwt",
        raw=raw,
    )


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

    async def _resolve_active_tenant_status(tenant_id: str) -> str:
        return "active"

    monkeypatch.setattr(GovernanceMiddleware, "_resolve_identity", _resolve_with_tenant)

    app = FastAPI()
    app.add_middleware(
        GovernanceMiddleware,
        tenant_status_resolver=_resolve_active_tenant_status,
        rate_limiter=None,
    )

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


@pytest.mark.parametrize(
    ("tenant_status", "expected_status", "expected_error"),
    [
        ("suspended", 403, "tenant_suspended"),
        ("pending", 403, "tenant_pending"),
        ("deleted", 404, "tenant_not_found"),
    ],
)
def test_tenant_lifecycle_status_blocks_before_route_handler(
    monkeypatch: pytest.MonkeyPatch,
    tenant_status: str,
    expected_status: int,
    expected_error: str,
) -> None:
    async def _resolve_with_status(self: GovernanceMiddleware, request):
        return _tenant_context(tenant_status=tenant_status)

    monkeypatch.setattr(GovernanceMiddleware, "_resolve_identity", _resolve_with_status)

    app = FastAPI()
    add_governance_middleware(app)
    reached_handler = False

    @app.get("/private")
    async def private() -> dict[str, str]:  # pragma: no cover - blocked by middleware
        nonlocal reached_handler
        reached_handler = True
        return {"status": "private"}

    response = TestClient(app).get("/private", headers={"Authorization": "Bearer test"})

    assert response.status_code == expected_status
    assert response.json()["error"] == expected_error
    assert response.json()["tenant_id"] == _TENANT_ID
    assert reached_handler is False


def test_tenant_status_resolver_takes_precedence_over_jwt_claim(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _resolve_active_claim(self: GovernanceMiddleware, request):
        return _tenant_context(tenant_status="active")

    async def _resolve_suspended_status(tenant_id: str) -> str:
        assert tenant_id == _TENANT_ID
        return "suspended"

    monkeypatch.setattr(GovernanceMiddleware, "_resolve_identity", _resolve_active_claim)

    app = FastAPI()
    app.add_middleware(
        GovernanceMiddleware,
        tenant_status_resolver=_resolve_suspended_status,
        rate_limiter=None,
    )

    @app.get("/private")
    async def private() -> dict[str, str]:  # pragma: no cover - blocked by middleware
        return {"status": "private"}

    response = TestClient(app).get("/private", headers={"Authorization": "Bearer test"})

    assert response.status_code == 403
    assert response.json()["error"] == "tenant_suspended"


def test_tenant_status_resolver_failure_falls_back_to_claim_and_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _resolve_suspended_claim(self: GovernanceMiddleware, request):
        return _tenant_context(tenant_status="suspended")

    async def _failing_status_resolver(tenant_id: str) -> str:
        raise RuntimeError("status backend unavailable")

    monkeypatch.setattr(GovernanceMiddleware, "_resolve_identity", _resolve_suspended_claim)

    app = FastAPI()
    app.add_middleware(
        GovernanceMiddleware,
        tenant_status_resolver=_failing_status_resolver,
        rate_limiter=None,
    )

    @app.get("/private")
    async def private() -> dict[str, str]:  # pragma: no cover - blocked by middleware
        return {"status": "private"}

    response = TestClient(app).get("/private", headers={"Authorization": "Bearer test"})

    assert response.status_code == 403
    assert response.json()["error"] == "tenant_suspended"
