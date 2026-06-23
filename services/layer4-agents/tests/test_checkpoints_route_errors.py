from __future__ import annotations

"""Regression tests for checkpoint query failure handling."""


from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
from value_fabric.shared.error_handling.handlers import register_exception_handlers
from value_fabric.shared.identity.context import RequestContext

from layer4_agents.api.routes import checkpoints


class _FailingConn:
    async def fetch(self, *_args, **_kwargs):
        raise RuntimeError("db down")


class _EmptyConn:
    async def fetch(self, *_args, **_kwargs):
        return []


def _override_executor():
    saver = SimpleNamespace(conn=_FailingConn())
    return _FakeExecutor(saver)


def _override_executor_empty():
    saver = SimpleNamespace(conn=_EmptyConn())
    return _FakeExecutor(saver)


class _FakeExecutor:
    def __init__(self, saver):
        self.checkpoint_saver = saver

    async def get_workflow_status(self, _workflow_id: str):
        return {"tenant_id": "tenant-test"}


async def _override_auth():
    return RequestContext(user_id="test-user", tenant_id="tenant-test")


def _build_app(executor_override):
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(checkpoints.checkpoint_router, prefix="/v1")
    app.dependency_overrides[checkpoints.get_executor] = executor_override
    app.dependency_overrides[checkpoints.require_authenticated] = _override_auth
    return app


def test_list_checkpoints_returns_structured_500_on_query_failure() -> None:
    app = _build_app(_override_executor)
    client = TestClient(app)
    response = client.get("/v1/workflows/wf-123/checkpoints")

    assert response.status_code == 503
    payload = response.json()
    assert payload["error"]["code"] == "SERVICE_UNAVAILABLE"
    assert payload["error"]["message"] == "Failed to retrieve checkpoints"


def test_list_checkpoints_returns_empty_200_when_no_checkpoints_exist() -> None:
    app = _build_app(_override_executor_empty)
    client = TestClient(app)
    response = client.get("/v1/workflows/wf-empty/checkpoints")

    assert response.status_code == 200
    payload = response.json()
    assert payload["workflow_id"] == "wf-empty"
    assert payload["checkpoints"] == []
    assert payload["total_count"] == 0
