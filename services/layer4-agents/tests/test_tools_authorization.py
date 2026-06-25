from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from value_fabric.shared.identity.context import RequestContext, RequestContextManager
from value_fabric.shared.identity.permissions import Permission

from layer4_agents.api.routes import tools
from layer4_agents.services.agent_tools import AgentToolRegistry
from layer4_agents.tools.registry import BaseTool, ToolCategory, ToolRegistry


class _StubRegistry:
    def has_tool(self, tool_name: str) -> bool:
        return tool_name == "stub_tool"

    def get(self, _tool_name: str):
        return SimpleNamespace(
            get_schema=lambda: SimpleNamespace(
                name="stub_tool",
                category=ToolCategory.UTILITY,
                description="stub",
                input_schema={},
                output_schema={},
                timeout_seconds=15,
                requires_auth=True,
                examples=[],
            )
        )

    def list_tools(self, category=None, search=None):
        return [
            SimpleNamespace(
                name="stub_tool",
                category=ToolCategory.UTILITY,
                description="stub",
                timeout_seconds=15,
                requires_auth=True,
            )
        ]


def _build_app(context: RequestContext) -> TestClient:
    app = FastAPI()
    app.include_router(tools.router, prefix="/v1")
    app.dependency_overrides[tools.get_tool_registry] = lambda: _StubRegistry()
    app.dependency_overrides[tools.require_authenticated] = lambda: context
    return TestClient(app)


def test_list_tools_endpoint_rejects_missing_scope() -> None:
    client = _build_app(
        RequestContext(
            tenant_id="tenant-a",
            user_id="user-1",
            roles=["read_only"],
            permissions=frozenset({Permission.READ_SEARCH}),
            auth_source="jwt_claim",
        )
    )

    response = client.get("/v1/tools")

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "INSUFFICIENT_SCOPE"


def test_list_tools_endpoint_allows_required_scope() -> None:
    client = _build_app(
        RequestContext(
            tenant_id="tenant-a",
            user_id="user-1",
            roles=["analyst"],
            permissions=frozenset({Permission.READ_AGENTS}),
            auth_source="jwt_claim",
        )
    )

    response = client.get("/v1/tools")

    assert response.status_code == 200
    assert response.json()[0]["name"] == "stub_tool"


@pytest.mark.asyncio
async def test_tool_registry_blocks_privileged_tool_without_scope() -> None:
    calls: list[dict] = []

    class _UpdateEntityTool(BaseTool):
        name = "update_entity"
        category = ToolCategory.UTILITY
        description = "update"
        input_schema = None
        output_schema = None
        requires_tenant = True

        def get_tenant_id(self) -> str | None:
            return "tenant-a"

        async def execute(self, input_data):
            calls.append({"executed": True})
            return {"ok": True}

    registry = ToolRegistry()
    registry.register(_UpdateEntityTool())

    with RequestContextManager(
        RequestContext(
            tenant_id="tenant-a",
            user_id="user-1",
            roles=["analyst"],
            permissions=frozenset({Permission.READ_AGENTS}),
            auth_source="jwt_claim",
        )
    ):
        result = await registry.execute("update_entity", {"tenant_id": "tenant-a"})

    assert result.status == "error"
    assert result.error["code"] == "INSUFFICIENT_SCOPE"
    assert not calls


@pytest.mark.asyncio
async def test_agent_tool_registry_blocks_invocation_without_scope() -> None:
    registry = AgentToolRegistry(neo4j_driver=object())

    with pytest.raises(Exception) as exc_info:
        await registry.promote_signal(
            tenant_id="tenant-a",
            account_id="acct-1",
            signal_id="sig-1",
            context=RequestContext(
                tenant_id="tenant-a",
                user_id="user-1",
                roles=["read_only"],
                permissions=frozenset({Permission.READ_SEARCH}),
                auth_source="jwt_claim",
            ),
        )

    assert getattr(exc_info.value, "status_code", None) == 403
