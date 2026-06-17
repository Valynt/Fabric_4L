from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from layer4_agents.api.routes.tools import router
from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.dependencies import require_authenticated


def _make_auth_context() -> RequestContext:
    return RequestContext(
        tenant_id=uuid4(),
        user_id="user-1",
        roles=["layer4.tools.invoke"],
    )


def test_invoke_tool_routes_through_gateway() -> None:
    app = FastAPI()
    app.dependency_overrides[require_authenticated] = _make_auth_context
    app.include_router(router, prefix="/v1")

    mock_abom = MagicMock()
    mock_abom.manifest_hash.return_value = "a" * 64

    mock_gateway_cls = MagicMock()
    mock_gateway = mock_gateway_cls.return_value
    mock_gateway.execute = AsyncMock(return_value={"result": 42})

    with patch(
        "layer4_agents.api.routes.tools.get_tool_registry",
        return_value=MagicMock(),
    ), patch(
        "layer4_agents.api.routes.tools.authorize_action",
        return_value=None,
    ), patch(
        "layer4_agents.api.routes.tools.AgentBillOfMaterials",
        mock_abom,
    ), patch(
        "layer4_agents.api.routes.tools.ToolGateway",
        mock_gateway_cls,
    ):
        client = TestClient(app)
        response = client.post(
            "/v1/tools/invoke",
            json={"tool_name": "calculate_roi", "input_data": {"investment": 100}},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["result"] == {"result": 42}
    mock_gateway.execute.assert_called_once_with("calculate_roi", {"investment": 100})
