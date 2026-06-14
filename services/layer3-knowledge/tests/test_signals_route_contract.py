from __future__ import annotations

from http import HTTPStatus
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient
from value_fabric.shared.identity import RequestContext

from src.api.routes import signals


class _FakeResult:
    def __init__(self, record: dict[str, Any] | None) -> None:
        self._record = record

    async def single(self) -> dict[str, Any] | None:
        return self._record


class _FakeNeo4jTenantSession:
    tenant_id = "tenant-test"

    async def run(self, _query: str, params: dict[str, Any]) -> _FakeResult:
        signal_node = {
            "id": params["id"],
            "tenant_id": params["tenant_id"],
            "account_id": params["account_id"],
            "type": params["type"],
            "content": params["content"],
            "confidence": params["confidence"],
            "trust_score": params["trust_score"],
            "lifecycle_state": params["lifecycle_state"],
            "impact_area": params["impact_area"],
            "created_at": params["created_at"],
            "updated_at": params["updated_at"],
        }
        return _FakeResult({"s": signal_node})


async def _authenticated_context() -> RequestContext:
    ctx = RequestContext(tenant_id="tenant-test", user_id="user-test")
    ctx.account_id = "acct-1"
    return ctx


async def _neo4j_session() -> _FakeNeo4jTenantSession:
    return _FakeNeo4jTenantSession()


def test_persist_signal_returns_signal_node_contract() -> None:
    app = FastAPI()
    app.include_router(signals.router)
    app.dependency_overrides[signals.require_authenticated] = _authenticated_context
    app.dependency_overrides[signals.get_neo4j_with_tenant] = _neo4j_session

    payload = {
        "id": "signal-1",
        "tenant_id": "ignored-body-tenant",
        "account_id": "acct-1",
        "type": "operational",
        "content": "Warehouse delays are increasing customer escalations.",
        "confidence": 0.91,
        "trust_score": 0.82,
        "lifecycle_state": "validated",
        "impact_area": "operations",
        "created_at": "2026-05-30T00:00:00Z",
        "updated_at": "2026-05-30T00:00:00Z",
    }

    response = TestClient(app).post("/graph/signals", json=payload)

    assert response.status_code == HTTPStatus.CREATED
    assert response.json() == {
        "id": "signal-1",
        "tenant_id": "tenant-test",
        "account_id": "acct-1",
        "type": "operational",
        "content": "Warehouse delays are increasing customer escalations.",
        "confidence": 0.91,
        "trust_score": 0.82,
        "lifecycle_state": "validated",
        "impact_area": "operations",
        "created_at": "2026-05-30T00:00:00Z",
        "updated_at": "2026-05-30T00:00:00Z",
    }
    assert "status" not in response.json()
    assert "signal" not in response.json()


def test_persist_signal_openapi_documents_direct_signal_node_response() -> None:
    app = FastAPI()
    app.include_router(signals.router)

    operation = app.openapi()["paths"]["/graph/signals"]["post"]

    assert operation["responses"]["201"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/SignalNode"
    }
