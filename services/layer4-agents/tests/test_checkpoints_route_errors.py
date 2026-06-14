from __future__ import annotations

"""Regression tests for checkpoint query failure handling."""


from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from layer4_agents.api.routes import checkpoints
from value_fabric.shared.error_handling import register_exception_handlers
from value_fabric.shared.identity.context import RequestContext


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


def _build_app(executor_override):
    app = FastAPI()
    app.include_router(checkpoints.checkpoint_router, prefix="/v1")
    register_exception_handlers(app)
    app.dependency_overrides[checkpoints.get_executor] = executor_override
    app.dependency_overrides[checkpoints.require_authenticated] = lambda: RequestContext(
        tenant_id="tenant-a",
        user_id="user-a",
    )
    return app


def test_list_checkpoints_returns_structured_500_on_query_failure() -> None:
    client = TestClient(_build_app(_override_executor))
    response = client.get("/v1/workflows/wf-123/checkpoints")

    assert response.status_code == 503
    payload = response.json()
    assert payload["error"]["details"]["code"] == "CHECKPOINT_QUERY_FAILED"
    assert payload["error"]["message"] == "Failed to retrieve checkpoints"
    assert payload["error"]["details"]["workflow_id"] == "wf-123"


def test_list_checkpoints_returns_empty_200_when_no_checkpoints_exist() -> None:
    client = TestClient(_build_app(_override_executor_empty))
    response = client.get("/v1/workflows/wf-empty/checkpoints")

    assert response.status_code == 200
    payload = response.json()
    assert payload["workflow_id"] == "wf-empty"
    assert payload["checkpoints"] == []
    assert payload["total_count"] == 0
