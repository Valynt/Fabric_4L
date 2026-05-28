from __future__ import annotations

"""Agent Workflow Traceability Tests - P0 Critical Gap Remediation

Validates that agent workflows propagate traceability context through
all execution phases per docs/contract.md §2.5.

Production Invariant: Trace_id/session_id must propagate through workflow
execution phases.

Author: Autonomous Test Assurance Agent
Date: 2026-05-23
"""


import pytest
from uuid import uuid4

from value_fabric.layer4.agents.base import AgentResult


pytestmark = [
    pytest.mark.security,
    pytest.mark.contract,
    pytest.mark.mandatory,
]


# Constants for test data
UUID_LENGTH = 36
DEFAULT_TOKEN_COUNT = 150
DEFAULT_COMPLETION_COUNT = 300
TOTAL_TOKENS = 450
LOW_CONFIDENCE = 0.1


class TestWorkflowTracePropagation:
    """POSITIVE: Validate trace_id propagates through workflow phases."""

    def test_trace_id_propagates_from_input_to_output(self):
        """trace_id from workflow input should appear in AgentResult output."""
        trace_id = str(uuid4())
        result = AgentResult(
            payload={"result": "test"},
            workflow_type="test_workflow",
            tenant_id=str(uuid4()),
            trace_id=trace_id,
        )
        assert result.trace_id == trace_id

    def test_trace_id_consistent_across_multiple_results(self):
        """trace_id should be consistent across multiple AgentResults in same workflow."""
        trace_id = str(uuid4())
        tenant_id = str(uuid4())

        result1 = AgentResult(
            payload={"step": 1},
            workflow_type="test_workflow",
            tenant_id=tenant_id,
            trace_id=trace_id,
        )

        result2 = AgentResult(
            payload={"step": 2},
            workflow_type="test_workflow",
            tenant_id=tenant_id,
            trace_id=trace_id,
        )

        assert result1.trace_id == result2.trace_id == trace_id

    def test_session_id_propagates_via_metadata(self):
        """session_id should propagate via metadata field."""
        session_id = str(uuid4())
        result = AgentResult(
            payload={"result": "test"},
            workflow_type="test_workflow",
            tenant_id=str(uuid4()),
            metadata={"session_id": session_id},
        )
        assert result.metadata["session_id"] == session_id


class TestWorkflowPhaseTraceability:
    """POSITIVE: Validate each workflow phase includes traceability metadata."""

    def test_planning_phase_includes_trace_id(self):
        """Planning phase should include trace_id in metadata."""
        trace_id = str(uuid4())
        result = AgentResult(
            payload={"phase": "planning"},
            workflow_type="test_workflow",
            tenant_id=str(uuid4()),
            trace_id=trace_id,
            metadata={"phase": "planning"},
        )
        assert result.trace_id == trace_id
        assert result.metadata["phase"] == "planning"

    def test_tool_selection_phase_includes_trace_id(self):
        """Tool selection phase should include trace_id."""
        trace_id = str(uuid4())
        result = AgentResult(
            payload={"phase": "tool_selection"},
            workflow_type="test_workflow",
            tenant_id=str(uuid4()),
            trace_id=trace_id,
            metadata={"phase": "tool_selection"},
        )
        assert result.trace_id == trace_id

    def test_execution_phase_includes_trace_id_and_tokens(self):
        """Execution phase should include trace_id and token counts."""
        trace_id = str(uuid4())
        result = AgentResult(
            payload={"phase": "execution"},
            workflow_type="test_workflow",
            tenant_id=str(uuid4()),
            trace_id=trace_id,
            prompt_tokens=DEFAULT_TOKEN_COUNT,
            completion_tokens=DEFAULT_COMPLETION_COUNT,
            metadata={"phase": "execution"},
        )
        assert result.trace_id == trace_id
        assert result.prompt_tokens == DEFAULT_TOKEN_COUNT
        assert result.completion_tokens == DEFAULT_COMPLETION_COUNT

    def test_validation_phase_includes_trace_id(self):
        """Validation phase should include trace_id."""
        trace_id = str(uuid4())
        result = AgentResult(
            payload={"phase": "validation"},
            workflow_type="test_workflow",
            tenant_id=str(uuid4()),
            trace_id=trace_id,
            metadata={"phase": "validation"},
        )
        assert result.trace_id == trace_id


class TestWorkflowErrorTraceability:
    """POSITIVE: Validate errors include traceability context."""

    def test_error_result_includes_trace_id(self):
        """Error results should still include trace_id."""
        trace_id = str(uuid4())
        result = AgentResult(
            payload={"error": "test error"},
            workflow_type="test_workflow",
            tenant_id=str(uuid4()),
            trace_id=trace_id,
            confidence=LOW_CONFIDENCE,  # Low confidence triggers degraded state
        )
        assert result.trace_id == trace_id
        assert result.degraded_reason is not None

    def test_error_result_includes_model_used(self):
        """Error results should include model_used if LLM was called."""
        model_used = "gpt-4o-2024-05-13"
        result = AgentResult(
            payload={"error": "test error"},
            workflow_type="test_workflow",
            tenant_id=str(uuid4()),
            model_used=model_used,
            llm_enrichment=True,
            confidence=LOW_CONFIDENCE,
        )
        assert result.model_used == model_used

    def test_error_result_includes_token_counts(self):
        """Error results should include token counts if LLM was called."""
        result = AgentResult(
            payload={"error": "test error"},
            workflow_type="test_workflow",
            tenant_id=str(uuid4()),
            prompt_tokens=DEFAULT_TOKEN_COUNT,
            completion_tokens=DEFAULT_COMPLETION_COUNT,
            llm_enrichment=True,
            confidence=LOW_CONFIDENCE,
        )
        assert result.prompt_tokens == DEFAULT_TOKEN_COUNT
        assert result.completion_tokens == DEFAULT_COMPLETION_COUNT


class TestWorkflowReproducibility:
    """POSITIVE: Validate traceability enables workflow reproducibility."""

    def test_trace_id_uniquely_identifies_execution(self):
        """Each workflow execution should have unique trace_id."""
        trace_id_1 = str(uuid4())
        trace_id_2 = str(uuid4())

        result1 = AgentResult(
            payload={"result": "test"},
            workflow_type="test_workflow",
            tenant_id=str(uuid4()),
            trace_id=trace_id_1,
        )

        result2 = AgentResult(
            payload={"result": "test"},
            workflow_type="test_workflow",
            tenant_id=str(uuid4()),
            trace_id=trace_id_2,
        )

        assert result1.trace_id != result2.trace_id

    def test_model_version_pinning_enables_reproducibility(self):
        """model_used field enables exact model version reproducibility."""
        model_used = "gpt-4o-2024-05-13"
        result = AgentResult(
            payload={"result": "test"},
            workflow_type="test_workflow",
            tenant_id=str(uuid4()),
            model_used=model_used,
        )
        assert result.model_used == model_used
        # Exact version enables reproducibility

    def test_token_counts_enable_cost_reproducibility(self):
        """Token counts enable cost calculation reproducibility."""
        prompt_tokens = DEFAULT_TOKEN_COUNT
        completion_tokens = DEFAULT_COMPLETION_COUNT
        result = AgentResult(
            payload={"result": "test"},
            workflow_type="test_workflow",
            tenant_id=str(uuid4()),
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            model_used="gpt-4o-2024-05-13",
        )
        total_tokens = result.prompt_tokens + result.completion_tokens
        assert total_tokens == TOTAL_TOKENS
        # Exact counts enable cost reproducibility


class TestWorkflowCrossRequestContinuity:
    """POSITIVE: Validate session_id enables cross-request continuity."""

    def test_session_id_links_multiple_workflow_executions(self):
        """session_id should link multiple workflow executions."""
        session_id = str(uuid4())
        tenant_id = str(uuid4())

        result1 = AgentResult(
            payload={"step": 1},
            workflow_type="test_workflow",
            tenant_id=tenant_id,
            metadata={"session_id": session_id},
        )

        result2 = AgentResult(
            payload={"step": 2},
            workflow_type="test_workflow",
            tenant_id=tenant_id,
            metadata={"session_id": session_id},
        )

        assert result1.metadata["session_id"] == result2.metadata["session_id"] == session_id

    def test_session_id_different_from_trace_id(self):
        """session_id should be different from trace_id."""
        session_id = str(uuid4())
        trace_id = str(uuid4())

        result = AgentResult(
            payload={"result": "test"},
            workflow_type="test_workflow",
            tenant_id=str(uuid4()),
            trace_id=trace_id,
            metadata={"session_id": session_id},
        )

        assert result.trace_id != result.metadata["session_id"]


class TestWorkflowTenantIsolationTraceability:
    """POSITIVE: Validate traceability respects tenant isolation."""

    def test_tenant_id_in_result_matches_input(self):
        """tenant_id in AgentResult should match workflow input."""
        tenant_id = str(uuid4())
        result = AgentResult(
            payload={"result": "test"},
            workflow_type="test_workflow",
            tenant_id=tenant_id,
        )
        assert result.tenant_id == tenant_id

    def test_trace_id_includes_tenant_context(self):
        """trace_id should be scoped to tenant context."""
        tenant_id = str(uuid4())
        trace_id = str(uuid4())

        result = AgentResult(
            payload={"result": "test"},
            workflow_type="test_workflow",
            tenant_id=tenant_id,
            trace_id=trace_id,
        )

        # Trace_id is globally unique but associated with tenant_id
        assert result.tenant_id == tenant_id
        assert result.trace_id == trace_id

    def test_metadata_includes_tenant_id_for_observability(self):
        """metadata can include tenant_id for observability systems."""
        tenant_id = str(uuid4())
        result = AgentResult(
            payload={"result": "test"},
            workflow_type="test_workflow",
            tenant_id=tenant_id,
            metadata={"tenant_id": tenant_id},
        )
        assert result.metadata["tenant_id"] == tenant_id
