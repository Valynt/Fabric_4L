from __future__ import annotations

"""Tests for the Layer 4 Ground Truth proxy route boundary."""

from typing import Any
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from value_fabric.shared.error_handling import register_exception_handlers
from value_fabric.shared.identity.context import RequestContext

from layer4_agents.api.routes import ground_truth_proxy


@pytest.fixture
def ground_truth_app() -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(ground_truth_proxy.router)
    return app


class FakeGroundTruthProxyClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def list_truths(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("list_truths", kwargs))
        return {"items": [{"id": "truth-1"}], "total": 1}

    async def get_truth(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("get_truth", kwargs))
        return {"id": kwargs["truth_id"]}

    async def get_truth_audit(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("get_truth_audit", kwargs))
        return {"events": [{"action": "validated"}]}

    async def validate_truth(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("validate_truth", kwargs))
        return {"truth_object_id": kwargs["truth_id"], "status": "VALIDATED"}

    async def get_freshness_summary(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("get_freshness_summary", kwargs))
        return {"total_count": 1, "fresh_count": 1}

    async def get_stale_truths(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("get_stale_truths", kwargs))
        return {"items": [], "total": 0}

    async def get_maturity_ladder(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("get_maturity_ladder", kwargs))
        return {"levels": []}


@pytest.mark.asyncio
async def test_ground_truth_proxy_uses_route_port_with_tenant(ground_truth_app: FastAPI) -> None:
    fake_client = FakeGroundTruthProxyClient()
    tenant_ctx = RequestContext(tenant_id="tenant-123", user_id="user-123")
    ground_truth_app.dependency_overrides[ground_truth_proxy.require_authenticated] = lambda: tenant_ctx
    ground_truth_app.dependency_overrides[ground_truth_proxy.get_ground_truth_proxy_client] = (
        lambda: fake_client
    )

    async with AsyncClient(transport=ASGITransport(app=ground_truth_app), base_url="http://test") as client:
        response = await client.get("/v1/ground-truth/truths?status=VALIDATED&limit=5")

    assert response.status_code == 200
    assert response.json() == {"items": [{"id": "truth-1"}], "total": 1}
    assert fake_client.calls == [
        (
            "list_truths",
            {
                "tenant_id": "tenant-123",
                "status": "VALIDATED",
                "claim_type": None,
                "min_maturity": None,
                "min_confidence": None,
                "limit": 5,
                "offset": 0,
            },
        )
    ]


@pytest.mark.asyncio
async def test_ground_truth_proxy_missing_tenant_fails_closed(
    ground_truth_app: FastAPI,
) -> None:
    fake_client = FakeGroundTruthProxyClient()
    tenantless_ctx = RequestContext(tenant_id=None, user_id="user-123")
    ground_truth_app.dependency_overrides[ground_truth_proxy.require_authenticated] = (
        lambda: tenantless_ctx
    )
    ground_truth_app.dependency_overrides[ground_truth_proxy.get_ground_truth_proxy_client] = (
        lambda: fake_client
    )

    truth_id = uuid4()
    async with AsyncClient(transport=ASGITransport(app=ground_truth_app), base_url="http://test") as client:
        response = await client.get(f"/v1/ground-truth/truths/{truth_id}")

    assert response.status_code == 401
    assert "tenant" in response.text.lower()
    assert fake_client.calls == []
