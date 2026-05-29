from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from jsonschema import Draft202012Validator

from layer4_agents.api.routes import workflows


class _Ctx:
    tenant_id = "tenant-1"


class _Executor:
    async def list_workflows(self, tenant_id: str):
        return [
            {
                "workflow_id": "wf-1",
                "workflow_type": "roi_calculator",
                "status": "running",
                "progress_percentage": 35.0,
                "tenant_id": tenant_id,
            },
            {
                "workflow_id": "wf-complete",
                "workflow_type": "business_case",
                "status": "completed",
                "progress_percentage": 100.0,
                "tenant_id": tenant_id,
            },
        ]

    async def list_active_workflows(self, tenant_id: str):
        return [{"workflow_id": "wf-1", "workflow_type": "roi_calculator", "status": "running", "progress_percentage": 35.0}]

    async def get_workflow_status(self, workflow_id: str):
        return {"workflow_id": workflow_id, "workflow_type": "roi_calculator", "status": "running", "progress_percentage": 35.0, "tenant_id": "tenant-1"}


def _load_schema(name: str) -> dict:
    root = Path(__file__).resolve().parents[3]
    return json.loads((root / "contracts" / "jsonschema" / "workflows" / name).read_text())


def _build_app() -> FastAPI:
    app = FastAPI()
    app.include_router(workflows.router, prefix="/v1")
    app.dependency_overrides[workflows.require_authenticated] = lambda: _Ctx()
    app.dependency_overrides[workflows.get_executor] = lambda: _Executor()
    return app


@pytest.mark.asyncio
async def test_workflow_list_and_detail_match_canonical_schemas():
    app = _build_app()
    list_schema = _load_schema("workflow-list.json")
    detail_schema = _load_schema("workflow-detail.json")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        list_resp = (await client.get("/v1/workflows/active")).json()
        detail_resp = (await client.get("/v1/workflows/wf-1")).json()

    Draft202012Validator(list_schema).validate(list_resp)
    Draft202012Validator(detail_schema).validate(detail_resp)


@pytest.mark.asyncio
async def test_workflow_list_requires_include_completed_for_terminal_cases():
    app = _build_app()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        default_resp = (await client.get("/v1/workflows?type=business_case")).json()
        completed_resp = (await client.get("/v1/workflows?type=business_case&include_completed=true")).json()

    assert default_resp["items"] == []
    assert [item["id"] for item in completed_resp["items"]] == ["wf-complete"]
