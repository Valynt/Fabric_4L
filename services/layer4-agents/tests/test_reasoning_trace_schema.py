"""Tests for structured reasoning trace schema enforcement."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from value_fabric.layer4.models.reasoning_trace import (
    ReasoningTrace,
    ToolCallTrace,
    validate_reasoning_trace,
)


class TestReasoningTraceSchema:
    def test_valid_reasoning_trace(self) -> None:
        trace = ReasoningTrace(
            inputs_used=["prospect_id", "value_driver_ids"],
            tools_called=[
                ToolCallTrace(tool_name="get_prospect_data", invocation_id="inv_1"),
            ],
            evidence_considered=["evidence_1"],
            assumptions=["assumption_1"],
            confidence=0.85,
            output_object_ids=["output_1"],
            run_id="run_123",
            trace_id="trace_123",
        )
        validate_reasoning_trace(trace, strict=True)

    def test_missing_inputs_used_fails_strict(self) -> None:
        trace = ReasoningTrace(
            inputs_used=[],
            tools_called=[ToolCallTrace(tool_name="t1", invocation_id="inv_1")],
            evidence_considered=["e1"],
            assumptions=["a1"],
            confidence=0.85,
            output_object_ids=["o1"],
            run_id="run_123",
            trace_id="trace_123",
        )
        with pytest.raises(ValueError, match="inputs_used"):
            validate_reasoning_trace(trace, strict=True)

    def test_missing_tools_called_fails_strict(self) -> None:
        trace = ReasoningTrace(
            inputs_used=["i1"],
            tools_called=[],
            evidence_considered=["e1"],
            assumptions=["a1"],
            confidence=0.85,
            output_object_ids=["o1"],
            run_id="run_123",
            trace_id="trace_123",
        )
        with pytest.raises(ValueError, match="tools_called"):
            validate_reasoning_trace(trace, strict=True)

    def test_missing_evidence_fails_strict(self) -> None:
        trace = ReasoningTrace(
            inputs_used=["i1"],
            tools_called=[ToolCallTrace(tool_name="t1", invocation_id="inv_1")],
            evidence_considered=[],
            assumptions=["a1"],
            confidence=0.85,
            output_object_ids=["o1"],
            run_id="run_123",
            trace_id="trace_123",
        )
        with pytest.raises(ValueError, match="evidence_considered"):
            validate_reasoning_trace(trace, strict=True)

    def test_missing_assumptions_fails_strict(self) -> None:
        trace = ReasoningTrace(
            inputs_used=["i1"],
            tools_called=[ToolCallTrace(tool_name="t1", invocation_id="inv_1")],
            evidence_considered=["e1"],
            assumptions=[],
            confidence=0.85,
            output_object_ids=["o1"],
            run_id="run_123",
            trace_id="trace_123",
        )
        with pytest.raises(ValueError, match="assumptions"):
            validate_reasoning_trace(trace, strict=True)

    def test_missing_output_object_ids_fails_strict(self) -> None:
        trace = ReasoningTrace(
            inputs_used=["i1"],
            tools_called=[ToolCallTrace(tool_name="t1", invocation_id="inv_1")],
            evidence_considered=["e1"],
            assumptions=["a1"],
            confidence=0.85,
            output_object_ids=[],
            run_id="run_123",
            trace_id="trace_123",
        )
        with pytest.raises(ValueError, match="output_object_ids"):
            validate_reasoning_trace(trace, strict=True)

    def test_none_trace_fails(self) -> None:
        with pytest.raises(ValueError, match="REASONING_TRACE_MISSING"):
            validate_reasoning_trace(None)

    def test_confidence_out_of_range(self) -> None:
        with pytest.raises(ValueError, match="confidence"):
            ReasoningTrace(
                inputs_used=["i1"],
                tools_called=[ToolCallTrace(tool_name="t1", invocation_id="inv_1")],
                evidence_considered=["e1"],
                assumptions=["a1"],
                confidence=1.5,
                output_object_ids=["o1"],
                run_id="run_123",
                trace_id="trace_123",
            )

    def test_non_strict_allows_empty_lists(self) -> None:
        trace = ReasoningTrace(
            inputs_used=[],
            tools_called=[],
            evidence_considered=[],
            assumptions=[],
            confidence=0.5,
            output_object_ids=[],
            run_id="run_123",
            trace_id="trace_123",
        )
        validate_reasoning_trace(trace, strict=False)

    def test_reasoning_trace_serialization(self) -> None:
        trace = ReasoningTrace(
            inputs_used=["i1"],
            tools_called=[ToolCallTrace(tool_name="t1", invocation_id="inv_1")],
            evidence_considered=["e1"],
            assumptions=["a1"],
            confidence=0.85,
            output_object_ids=["o1"],
            run_id="run_123",
            trace_id="trace_123",
        )
        data = trace.model_dump(mode="json")
        assert data["run_id"] == "run_123"
        assert data["trace_id"] == "trace_123"
        assert data["confidence"] == 0.85
