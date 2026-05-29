from __future__ import annotations

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
import pytest

from layer4_agents.api.routes import narratives
from layer4_agents.services.narrative_builder_service import (
    NarrativeBuilderService,
    NarrativeRequest,
)


@pytest.mark.asyncio
async def test_generate_rejects_hostile_payload_tenant_id(monkeypatch):
    app = FastAPI()
    app.include_router(narratives.router, prefix="/v1")

    class _Driver:
        pass

    app.state.neo4j_driver = _Driver()
    app.dependency_overrides[narratives.get_verified_tenant_id] = lambda: "trusted-tenant"

    called = {"value": False}

    class _Svc:
        async def generate_narrative(self, *args, **kwargs):
            called["value"] = True
            return {"id": "n1"}

    monkeypatch.setattr(narratives, "NarrativeBuilderService", lambda *_args, **_kwargs: _Svc(), raising=False)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/v1/narratives/generate",
            json={
                "account_id": "acct-1",
                "tenant_id": "hostile-tenant",
            },
        )

    assert response.status_code == 422
    assert called["value"] is False


@pytest.mark.asyncio
async def test_generate_narrative_rejects_mismatched_request_tenant_for_persistence():
    class _Driver:
        pass

    class _HostileNarrativeRequest(NarrativeRequest):
        tenant_id: str = "victim-tenant"

    svc = NarrativeBuilderService(_Driver())
    hostile_request = _HostileNarrativeRequest(account_id="acct-1")

    with pytest.raises(ValueError, match="does not match trusted tenant context"):
        await svc.generate_narrative(
            hostile_request,
            tenant_id="trusted-tenant",
        )
