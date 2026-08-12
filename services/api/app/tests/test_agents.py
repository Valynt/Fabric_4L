import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.schemas import AgentRun
from app.services.agent_orchestrator import AgentOrchestrator

from .conftest import TENANT_ALPHA, auth_headers
from .test_agent_orchestrator import FakeLayer4Client

HEADERS = auth_headers(TENANT_ALPHA)


@pytest.fixture(autouse=True)
def _in_memory_layer4(monkeypatch):
    """Back the router's orchestrator with an in-memory L4 client.

    These tests exercise the gateway's delegation contract, not L4
    availability: since the orchestration delegation change (V1-ROUTING-001),
    the router fails closed (503/502) when L4 is unreachable, which is what a
    bare TestClient would otherwise hit. L4-down behavior is covered by
    test_agent_orchestrator.py; here the delegation path must run end to end.
    """
    import app.routers.agents as agents_router

    monkeypatch.setattr(
        agents_router,
        "orchestrator",
        AgentOrchestrator(layer4_client=FakeLayer4Client()),
    )


def test_create_agent_run():
    with TestClient(app) as client:
        payload = {
            "workflow_type": "hypothesis_generation",
            "account_id": "acc-allego",
            "input": {"prompt": "Generate hypotheses"},
        }
        response = client.post("/v1/agents/runs", json=payload, headers=HEADERS)
        assert response.status_code == 201
        data = response.json()
        assert data["workflow_type"] == "hypothesis_generation"
        assert data["status"] in ["pending", "running", "completed"]


def _create_run(client: TestClient) -> str:
    payload = {
        "workflow_type": "hypothesis_generation",
        "account_id": "acc-allego",
        "input": {"prompt": "Generate hypotheses"},
    }
    response = client.post("/v1/agents/runs", json=payload, headers=HEADERS)
    assert response.status_code == 201
    return response.json()["id"]


def test_get_agent_run():
    with TestClient(app) as client:
        run_id = _create_run(client)
        response = client.get(f"/v1/agents/runs/{run_id}", headers=HEADERS)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == run_id


def test_cancel_agent_run():
    with TestClient(app) as client:
        run_id = _create_run(client)
        response = client.post(f"/v1/agents/runs/{run_id}/cancel", headers=HEADERS)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"


def test_workflow_compat_routes():
    with TestClient(app) as client:
        create_resp = client.post(
            "/v1/agents/workflows",
            json={"workflow_type": "hypothesis_generation", "inputs": {"prompt": "x"}},
            headers=HEADERS,
        )
        assert create_resp.status_code == 201
        workflow_id = create_resp.json()["workflow_id"]

        active_resp = client.get("/v1/agents/workflows/active", headers=HEADERS)
        assert active_resp.status_code == 200
        assert isinstance(active_resp.json(), list)

        detail_resp = client.get(f"/v1/agents/workflows/{workflow_id}", headers=HEADERS)
        assert detail_resp.status_code == 200
        assert detail_resp.json()["workflow_id"] == workflow_id

        resume_resp = client.post(f"/v1/agents/workflows/{workflow_id}/resume", headers=HEADERS)
        assert resume_resp.status_code == 200

        pause_resp = client.post(f"/v1/agents/workflows/{workflow_id}/pause", headers=HEADERS)
        assert pause_resp.status_code == 200

        events_resp = client.get(f"/v1/agents/workflows/{workflow_id}/events", headers=HEADERS)
        assert events_resp.status_code == 200
        assert events_resp.headers["content-type"].startswith("text/event-stream")

        delete_resp = client.delete(f"/v1/agents/workflows/{workflow_id}", headers=HEADERS)
        assert delete_resp.status_code == 200
        assert delete_resp.json()["status"] == "cancelled"


def test_workflow_events_sse_json_serialization_and_shape():
    with TestClient(app) as client:
        create_resp = client.post(
            "/v1/agents/workflows",
            json={
                "workflow_type": "quote_safety",
                "inputs": {
                    "apostrophe": "it's safe",
                    "double_quote": 'he said "hello"',
                    "nested": {"text": "nested \"quote\" with apostrophe's"},
                    "unicode": "雪だるま ☃️ — café",
                },
            },
            headers=HEADERS,
        )
        assert create_resp.status_code == 201
        workflow_id = create_resp.json()["workflow_id"]

        events_resp = client.get(f"/v1/agents/workflows/{workflow_id}/events", headers=HEADERS)
        assert events_resp.status_code == 200
        assert events_resp.headers["content-type"].startswith("text/event-stream")

        body = events_resp.text
        frames = [frame for frame in body.split("\n\n") if frame.strip()]
        assert len(frames) >= 2

        parsed_events = []
        for frame in frames[:2]:
            assert frame.startswith("data: ")
            parsed_events.append(json.loads(frame.removeprefix("data: ")))

        first_payload = parsed_events[0]["payload"]
        assert first_payload["workflow_id"] == workflow_id
        assert first_payload["input"]["apostrophe"] == "it's safe"
        assert first_payload["input"]["double_quote"] == 'he said "hello"'
        assert first_payload["input"]["nested"]["text"] == 'nested "quote" with apostrophe\'s'
        assert first_payload["input"]["unicode"] == "雪だるま ☃️ — café"

        second_payload = parsed_events[1]["payload"]
        assert second_payload["workflow_id"] == workflow_id
        assert second_payload["status"] in {"pending", "running", "paused", "completed", "failed", "cancelled"}
        assert isinstance(second_payload["updated_at"], str)


def test_workflow_active_route_offloads_refresh_to_threadpool():
    run = AgentRun(
        id="wf-threadpool",
        tenant_id=TENANT_ALPHA,
        account_id="acc-allego",
        workflow_type="hypothesis_generation",
        status="running",
        input={"prompt": "Generate hypotheses"},
        created_at=datetime.now(UTC).isoformat(),
        updated_at=datetime.now(UTC).isoformat(),
    )

    with TestClient(app) as client:
        with (
            patch("app.routers.agents.db.agent_runs.list", return_value=[run]),
            patch("app.routers.agents.orchestrator.get_run") as get_run,
            patch(
                "app.routers.agents.asyncio.to_thread",
                new=AsyncMock(return_value=run),
            ) as to_thread,
        ):
            response = client.get("/v1/agents/workflows/active", headers=HEADERS)

    assert response.status_code == 200
    assert response.json()[0]["workflow_id"] == run.id
    # assert_any_await, not assert_awaited_once: the patched asyncio.to_thread
    # is the stdlib module attribute, so the JWT decode in the auth resolver
    # registers an await on the same mock. What this test proves is that the
    # active-runs refresh itself is offloaded to the threadpool.
    to_thread.assert_any_await(get_run, run.id, tenant_id=TENANT_ALPHA)
