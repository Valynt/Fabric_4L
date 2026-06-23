from __future__ import annotations

import pytest

from layer4_agents.engine.output_contract import validate_final_output
from layer4_agents.models.agent_state import (
    BusinessCaseAgentState,
    ROIAgentState,
    WhitespaceAgentState,
    WorkflowStatus,
)
from layer4_agents.models.reasoning_trace import ReasoningTrace, ToolCallTrace


def _valid_trace(run_id: str, trace_id: str) -> ReasoningTrace:
    return ReasoningTrace(
        inputs_used=["prospect_id"],
        tools_called=[ToolCallTrace(tool_name="mock_tool", invocation_id="inv-1")],
        evidence_considered=["evidence:1"],
        assumptions=["assumption:1"],
        confidence=0.8,
        output_object_ids=["obj-1"],
        run_id=run_id,
        trace_id=trace_id,
    )


@pytest.mark.parametrize(
    "state_factory",
    [
        lambda: ROIAgentState(
            tenant_id="tenant-1",
            workflow_id="wf-roi-1",
            run_id="run-roi-1",
            trace_id="trace-roi-1",
            status=WorkflowStatus.COMPLETED,
            input_data={"prospect_id": "p-1", "value_driver_ids": ["vd-1"]},
            output_data={"roi": {"net_value": 10}},
            reasoning_trace=_valid_trace("run-roi-1", "trace-roi-1"),
        ),
        lambda: WhitespaceAgentState(
            tenant_id="tenant-1",
            workflow_id="wf-ws-1",
            run_id="run-ws-1",
            trace_id="trace-ws-1",
            status=WorkflowStatus.COMPLETED,
            input_data={"prospect_id": "p-1", "prospect_needs": "Need automation"},
            output_data={"gaps": []},
            reasoning_trace=_valid_trace("run-ws-1", "trace-ws-1"),
        ),
        lambda: BusinessCaseAgentState(
            tenant_id="tenant-1",
            workflow_id="wf-bc-1",
            run_id="run-bc-1",
            trace_id="trace-bc-1",
            status=WorkflowStatus.COMPLETED,
            input_data={"account_id": "550e8400-e29b-41d4-a716-446655440000"},
            output_data={"document": {"title": "Case"}},
            reasoning_trace=_valid_trace("run-bc-1", "trace-bc-1"),
        ),
    ],
)
def test_output_envelope_valid_outputs_pass(state_factory) -> None:
    state = state_factory()
    result = validate_final_output(state)
    assert result.valid is True
    assert result.errors == []


@pytest.mark.parametrize(
    "state_factory",
    [
        lambda: ROIAgentState(
            tenant_id="tenant-1",
            workflow_id="wf-roi-bad",
            run_id="run-roi-bad",
            trace_id="trace-roi-bad",
            status=WorkflowStatus.COMPLETED,
            input_data={"prospect_id": "p-1", "value_driver_ids": ["vd-1"]},
            output_data={"roi": {"net_value": 10}},
            reasoning_trace=None,
        ),
        lambda: WhitespaceAgentState(
            tenant_id="tenant-1",
            workflow_id="wf-ws-bad",
            run_id="run-ws-bad",
            trace_id="trace-ws-bad",
            status=WorkflowStatus.COMPLETED,
            input_data={"prospect_id": "p-1", "prospect_needs": "Need automation"},
            output_data={"gaps": []},
            reasoning_trace=None,
        ),
        lambda: BusinessCaseAgentState(
            tenant_id="tenant-1",
            workflow_id="wf-bc-bad",
            run_id="run-bc-bad",
            trace_id="trace-bc-bad",
            status=WorkflowStatus.COMPLETED,
            input_data={"account_id": "550e8400-e29b-41d4-a716-446655440000"},
            output_data={"document": {"title": "Case"}},
            reasoning_trace=None,
        ),
    ],
)
def test_output_envelope_invalid_outputs_fail(state_factory) -> None:
    state = state_factory()
    result = validate_final_output(state)
    assert result.valid is False
    assert any("reasoning_trace" in err for err in result.errors)
