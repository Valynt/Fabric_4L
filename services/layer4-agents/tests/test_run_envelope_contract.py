from __future__ import annotations

"""Tests for canonical run envelope across workflows, logs, and checkpoints."""


import pytest

from layer4_agents.models.run_envelope import RunEnvelope
from layer4_agents.workflows.roi_calculator import ROICalculatorWorkflow
from layer4_agents.tools.registry import ToolRegistry


class TestRunEnvelopeContract:
    def test_run_envelope_requires_all_ids(self) -> None:
        with pytest.raises(ValueError, match="required"):
            RunEnvelope(
                run_id="",
                workflow_id="wf_123",
                trace_id="trace_123",
                tenant_id="tenant_a",
                workflow_type="roi_calculator",
            )

    def test_run_envelope_requires_tenant(self) -> None:
        with pytest.raises(ValueError, match="tenant_id is required"):
            RunEnvelope(
                run_id="run_123",
                workflow_id="wf_123",
                trace_id="trace_123",
                tenant_id="",
                workflow_type="roi_calculator",
            )

    def test_run_envelope_distinct_ids(self) -> None:
        envelope = RunEnvelope(
            run_id="run_123",
            workflow_id="wf_123",
            trace_id="trace_123",
            tenant_id="tenant_a",
            workflow_type="roi_calculator",
        )
        assert envelope.run_id == "run_123"
        assert envelope.workflow_id == "wf_123"
        assert envelope.trace_id == "trace_123"
        assert envelope.run_id != envelope.workflow_id

    def test_run_envelope_with_checkpoint(self) -> None:
        envelope = RunEnvelope(
            run_id="run_123",
            workflow_id="wf_123",
            trace_id="trace_123",
            tenant_id="tenant_a",
            workflow_type="roi_calculator",
        )
        updated = envelope.with_checkpoint("chk_456")
        assert updated.checkpoint_id == "chk_456"
        assert updated.run_id == envelope.run_id

    def test_workflow_initial_state_has_envelope(self) -> None:
        registry = ToolRegistry()
        workflow = ROICalculatorWorkflow(registry)

        state = workflow.create_initial_state(
            {"prospect_id": "p1", "value_driver_ids": ["vd1"]},
            tenant_id="tenant-123",
            run_id="run_abc",
            trace_id="trace_def",
            workflow_id="wf_ghi",
        )
        assert state.run_envelope is not None
        assert state.run_envelope.run_id == "run_abc"
        assert state.run_envelope.trace_id == "trace_def"
        assert state.run_envelope.workflow_id == "wf_ghi"
        assert state.run_id == "run_abc"
        assert state.trace_id == "trace_def"
        assert state.workflow_id == "wf_ghi"

    def test_run_envelope_log_context(self) -> None:
        envelope = RunEnvelope(
            run_id="run_123",
            workflow_id="wf_123",
            trace_id="trace_123",
            checkpoint_id="chk_456",
            tenant_id="tenant_a",
            workflow_type="roi_calculator",
        )
        ctx = envelope.to_log_context()
        assert ctx["run_id"] == "run_123"
        assert ctx["workflow_id"] == "wf_123"
        assert ctx["trace_id"] == "trace_123"
        assert ctx["checkpoint_id"] == "chk_456"
        assert ctx["tenant_id"] == "tenant_a"
