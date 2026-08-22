from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest
from pydantic import BaseModel
from value_fabric.shared.identity.context import RequestContext, RequestContextManager
from value_fabric.shared.identity.permissions import Permission

import layer4_agents.tools.registry as registry_module
from layer4_agents.models.tool_schemas import ToolCategory
from layer4_agents.tools.registry import (
    BaseTool,
    ToolNotFoundError,
    ToolRegistry,
    ToolResult,
    _extract_auth_error_info,
    _record_tool_auth_failure_metric,
)


class DummyInput(BaseModel):
    name: str = "test"


class DummyOutput(BaseModel):
    result: str


class SafeTool(BaseTool):
    name = "safe_tool"
    category = ToolCategory.UTILITY
    description = "Safe utility tool"
    input_schema = DummyInput
    output_schema = DummyOutput

    async def execute(self, input_data: DummyInput) -> DummyOutput:
        return DummyOutput(result=f"processed_{input_data.name}")


class MutationTool(BaseTool):
    name = "mutate_record"
    category = ToolCategory.CALCULATION
    description = "Tool needing approval"
    input_schema = DummyInput
    output_schema = DummyOutput

    async def execute(self, input_data: DummyInput) -> DummyOutput:
        return DummyOutput(result=f"mutated_{input_data.name}")


class AuthHttpException(Exception):
    def __init__(self, status_code: int, detail: Any):
        super().__init__(str(detail))
        self.status_code = status_code
        self.detail = detail


def test_extract_auth_error_info_status_codes():
    # 401 status code
    exc_401 = AuthHttpException(status_code=401, detail={"message": "Token expired"})
    code, msg, detail = _extract_auth_error_info(exc_401)
    assert code == "AUTHENTICATION_REQUIRED"
    assert msg == "Token expired"
    assert detail == {"message": "Token expired"}

    # 403 status code with string detail
    exc_403 = AuthHttpException(status_code=403, detail="Forbidden action")
    code, msg, detail = _extract_auth_error_info(exc_403)
    assert code == "INSUFFICIENT_SCOPE"
    assert msg == "Forbidden action"
    assert detail == "Forbidden action"

    # Generic exception with no status_code and no detail
    exc_generic = ValueError("Boom")
    code, msg, detail = _extract_auth_error_info(exc_generic)
    assert code == "INSUFFICIENT_SCOPE"
    assert msg == "ValueError"
    assert detail is None


def test_record_tool_auth_failure_metric_cancellation():
    with patch("layer4_agents.metrics.prometheus_metrics.get_metrics") as mock_metrics:
        mock_instance = MagicMock()
        mock_instance.increment_tool_auth_failure.side_effect = asyncio.CancelledError()
        mock_metrics.return_value = mock_instance

        with pytest.raises(asyncio.CancelledError):
            _record_tool_auth_failure_metric("tool1", "tenant-1")


def test_record_tool_auth_failure_metric_swallows_other_exceptions():
    with patch("layer4_agents.metrics.prometheus_metrics.get_metrics") as mock_metrics:
        mock_metrics.side_effect = RuntimeError("metrics not initialized")
        # Must not raise
        _record_tool_auth_failure_metric("tool1", "tenant-1")


@pytest.mark.asyncio
async def test_authorize_tool_or_fail_cancellation():
    registry = ToolRegistry()
    with patch("layer4_agents.tools.registry.authorize_action") as mock_auth:
        mock_auth.side_effect = asyncio.CancelledError()
        with pytest.raises(asyncio.CancelledError):
            await registry._authorize_tool_or_fail(
                tool_action="some_action",
                request_context=None,
                tenant_id="tenant-1",
                tool_name="test_tool",
                trace_id="tr-1",
            )


@pytest.mark.asyncio
async def test_authorize_tool_or_fail_denial_result():
    registry = ToolRegistry()
    with patch("layer4_agents.tools.registry.authorize_action") as mock_auth:
        mock_auth.side_effect = AuthHttpException(status_code=403, detail="Not allowed")
        result = await registry._authorize_tool_or_fail(
            tool_action="some_action",
            request_context=None,
            tenant_id="tenant-1",
            tool_name="test_tool",
            trace_id="tr-1",
        )
        assert result is not None
        assert result.is_error()
        assert result.error["code"] == "INSUFFICIENT_SCOPE"
        assert result.error["message"] == "Not allowed"


def test_enforce_approval_policy():
    registry = ToolRegistry()
    registry._approval_required_categories = {ToolCategory.CALCULATION}

    # Category not in approval list -> None
    res = registry._enforce_approval_policy(
        tool_name="safe",
        tool_category=ToolCategory.UTILITY,
        input_dict={},
        workflow_id="wf-1",
        tenant_id="tenant-1",
        user_id="user-1",
        trace_id="tr-1",
    )
    assert res is None

    # Category requires approval but decision not approved -> failure
    res = registry._enforce_approval_policy(
        tool_name="mutate",
        tool_category=ToolCategory.CALCULATION,
        input_dict={"approval_decision": "rejected"},
        workflow_id="wf-1",
        tenant_id="tenant-1",
        user_id="user-1",
        trace_id="tr-1",
    )
    assert res is not None
    assert res.is_error()
    assert res.error["code"] == "APPROVAL_REQUIRED"

    # Category requires approval and decision approved -> None
    res = registry._enforce_approval_policy(
        tool_name="mutate",
        tool_category=ToolCategory.CALCULATION,
        input_dict={"approval_decision": "approved"},
        workflow_id="wf-1",
        tenant_id="tenant-1",
        user_id="user-1",
        trace_id="tr-1",
    )
    assert res is None


@pytest.mark.asyncio
async def test_execute_approval_and_idempotency_workflow():
    registry = ToolRegistry()
    registry._approval_required_categories = {ToolCategory.CALCULATION}
    registry.register(MutationTool())
    tenant_id = "00000000-0000-0000-0000-000000000001"

    req_ctx = RequestContext(
        tenant_id=UUID(tenant_id),
        user_id=UUID(int=1),
        roles=["analyst"],
        permissions=frozenset({Permission.READ_AGENTS, Permission.WRITE_AGENTS}),
        auth_source="jwt_claim",
    )

    with RequestContextManager(req_ctx):
        # Missing idempotency key for approval-required tool
        res = await registry.execute(
            "mutate_record",
            {"name": "test", "tenant_id": tenant_id, "approval_decision": "approved"},
        )
        assert res.is_error()
        assert res.error["code"] == "IDEMPOTENCY_KEY_REQUIRED"

        # Unapproved execution
        res = await registry.execute(
            "mutate_record",
            {
                "name": "test",
                "tenant_id": tenant_id,
                "idempotency_key": "idem-1",
                "approval_decision": "pending",
            },
        )
        assert res.is_error()
        assert res.error["code"] == "APPROVAL_REQUIRED"

        # Approved execution with idempotency key
        res = await registry.execute(
            "mutate_record",
            {
                "name": "test",
                "tenant_id": tenant_id,
                "idempotency_key": "idem-1",
                "approval_decision": "approved",
            },
        )
        assert res.is_success()
        assert res.data == {"result": "mutated_test"}

        # Cached idempotency replay returns cached result
        cached_res = await registry.execute(
            "mutate_record",
            {
                "name": "test_different",
                "tenant_id": tenant_id,
                "idempotency_key": "idem-1",
                "approval_decision": "approved",
            },
        )
        assert cached_res.is_success()
        assert cached_res.data == {"result": "mutated_test"}
