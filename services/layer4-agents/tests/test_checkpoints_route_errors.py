from __future__ import annotations

"""Regression tests for checkpoint query failure handling."""


from types import SimpleNamespace

from fastapi.testclient import TestClient

from layer4_agents.api.main import app
from layer4_agents.api.routes.checkpoints import get_executor


class _FailingConn:
    async def fetch(self, *_args, **_kwargs):
        raise RuntimeError("db down")


class _EmptyConn:
    async def fetch(self, *_args, **_kwargs):
        return []


def _override_executor():
    saver = SimpleNamespace(conn=_FailingConn())
    return SimpleNamespace(checkpoint_saver=saver)


def _override_executor_empty():
    saver = SimpleNamespace(conn=_EmptyConn())
    return SimpleNamespace(checkpoint_saver=saver)


def test_list_checkpoints_returns_structured_500_on_query_failure() -> None:
    app.dependency_overrides[get_executor] = _override_executor
    try:
        client = TestClient(app)
        response = client.get("/v1/workflows/wf-123/checkpoints")
    finally:
        app.dependency_overrides.pop(get_executor, None)

    assert response.status_code == 500
    payload = response.json()
    assert payload["detail"]["code"] == "CHECKPOINT_QUERY_FAILED"
    assert payload["detail"]["message"] == "Failed to retrieve checkpoints"
    assert payload["detail"]["workflow_id"] == "wf-123"


def test_list_checkpoints_returns_empty_200_when_no_checkpoints_exist() -> None:
    app.dependency_overrides[get_executor] = _override_executor_empty
    try:
        client = TestClient(app)
        response = client.get("/v1/workflows/wf-empty/checkpoints")
    finally:
        app.dependency_overrides.pop(get_executor, None)

    assert response.status_code == 200
    payload = response.json()
    assert payload["workflow_id"] == "wf-empty"
    assert payload["checkpoints"] == []
    assert payload["total_count"] == 0
