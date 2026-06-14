from __future__ import annotations

from uuid import UUID

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from value_fabric.shared.identity.context import RequestContext

from layer4_agents.api.routes import signals


@pytest.fixture
def app() -> FastAPI:
    app = FastAPI()
    app.include_router(signals.router, prefix="/v1")
    app.dependency_overrides[signals.require_authenticated] = lambda: RequestContext(
        tenant_id=UUID("12345678-1234-1234-1234-123456789abc"),
        user_id="reviewer-123",
    )
    return app


class _FakeNeo4jSession:
    def __init__(self, calls: list[tuple[str, dict]]) -> None:
        self.calls = calls

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def run(self, query: str, params: dict) -> None:
        self.calls.append((query, params))


class _FakeNeo4jDriver:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def session(self) -> _FakeNeo4jSession:
        return _FakeNeo4jSession(self.calls)


@pytest.mark.asyncio
async def test_signal_review_approve_reject_roundtrip_and_persistence_reload(app: FastAPI, monkeypatch: pytest.MonkeyPatch) -> None:
    persisted: dict[str, dict] = {}

    class FakeLayer3Client:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def review_signal(self, signal_id: str, account_id: str, review_status: str, reviewer_id: str, decision_note=None, tenant_id=None):
            persisted[signal_id] = {
                "signal_id": signal_id,
                "account_id": account_id,
                "review_status": review_status,
                "reviewed_by": reviewer_id,
                "reviewed_at": "2026-05-07T00:00:00Z",
                "decision_note": decision_note,
                "tenant_id": str(tenant_id),
            }
            return persisted[signal_id]

    monkeypatch.setattr("layer4_agents.integration.layer3_client.Layer3Client", FakeLayer3Client)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        approve = await client.patch("/v1/signals/sig-1/review", json={"account_id": "acct-1", "review_status": "approved"})
        assert approve.status_code == 200
        assert approve.json()["review_status"] == "approved"

        reject = await client.patch("/v1/signals/sig-1/review", json={"account_id": "acct-1", "review_status": "rejected", "decision_note": "insufficient evidence"})
        assert reject.status_code == 200
        assert reject.json()["review_status"] == "rejected"
        assert persisted["sig-1"]["decision_note"] == "insufficient evidence"


@pytest.mark.asyncio
async def test_evidence_attach_writes_driver_relation(app: FastAPI) -> None:
    fake_driver = _FakeNeo4jDriver()
    app.state.neo4j_driver = fake_driver

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/v1/evidence/ev-1/decisions",
            json={
                "account_id": "acct-1",
                "case_id": "case-1",
                "decision": "attached_to_driver",
                "driver_id": "drv-1",
                "decision_note": "attach for model",
            },
        )

    assert response.status_code == 200
    assert response.json()["decision"] == "attached_to_driver"
    assert len(fake_driver.calls) == 1
    _, params = fake_driver.calls[0]
    assert params["evidence_id"] == "ev-1"
    assert params["driver_id"] == "drv-1"
