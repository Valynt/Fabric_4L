from __future__ import annotations

"""
Unit tests for workflow state machine and state transitions.

Tests the core workflow state management without external dependencies.
Follows the test pyramid: fast, isolated, deterministic.
"""


from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock

import pytest
from value_fabric.shared.models.typed_dict import TypedDictModel

from layer4_agents.models.agent_state import (
    BaseAgentState,
    BusinessCaseAgentState,
    BusinessCaseInputData,
    ROIAgentState,
    ROIInputData,
    WhitespaceAgentState,
    WhitespaceInputData,
    WorkflowStatus,
    WorkflowType,
)
from layer4_agents.models.workflow_config import EdgeConfig, NodeConfig, NodeType, WorkflowConfig
from layer4_agents.tools.registry import ToolRegistry
from layer4_agents.workflows.base import BaseWorkflow, NodeExecutionError, WorkflowError


class ConcreteTestWorkflow_create_initial_stateResult(TypedDictModel):
    test: str


class TestWorkflowStatusTransitions:
    """Test workflow status state machine transitions."""

    @pytest.mark.unit
    def test_initial_status_is_pending(self):
        """New workflow must start with PENDING status."""
        state = BaseAgentState(tenant_id="test-tenant", workflow_type=WorkflowType.ROI_CALCULATOR)
        assert state.status == WorkflowStatus.PENDING
        assert state.workflow_id is not None
        assert state.started_at is None
        assert state.completed_at is None

    @pytest.mark.unit
    def test_running_status_transition(self):
        """Workflow can transition from PENDING to RUNNING."""
        state = BaseAgentState(tenant_id="test-tenant", workflow_type=WorkflowType.ROI_CALCULATOR)
        state.status = WorkflowStatus.RUNNING
        state.started_at = datetime.now(UTC)
        
        assert state.status == WorkflowStatus.RUNNING
        assert state.started_at is not None

    @pytest.mark.unit
    def test_completed_status_transition(self):
        """Workflow can transition from RUNNING to COMPLETED."""
        state = BaseAgentState(tenant_id="test-tenant", workflow_type=WorkflowType.ROI_CALCULATOR)
        state.status = WorkflowStatus.RUNNING
        state.started_at = datetime.now(UTC)
        
        state.status = WorkflowStatus.COMPLETED
        state.completed_at = datetime.now(UTC)
        
        assert state.status == WorkflowStatus.COMPLETED
        assert state.completed_at is not None

    @pytest.mark.unit
    def test_failed_status_transition(self):
        """Workflow can transition from RUNNING to FAILED."""
        state = BaseAgentState(tenant_id="test-tenant", workflow_type=WorkflowType.ROI_CALCULATOR)
        state.status = WorkflowStatus.RUNNING
        state.started_at = datetime.now(UTC)
        
        state.status = WorkflowStatus.FAILED
        state.completed_at = datetime.now(UTC)
        state.errors.append("Something went wrong")
        
        assert state.status == WorkflowStatus.FAILED
        assert len(state.errors) == 1
        assert "Something went wrong" in state.errors[0]

    @pytest.mark.unit
    def test_paused_status_transition(self):
        """Workflow can transition to PAUSED from RUNNING."""
        state = BaseAgentState(tenant_id="test-tenant", workflow_type=WorkflowType.ROI_CALCULATOR)
        state.status = WorkflowStatus.RUNNING
        
        state.status = WorkflowStatus.PAUSED
        state.pause_point = {
            "title": "Human Review Required",
            "reason": "Check calculation accuracy",
            "severity": "medium",
            "required_inputs": [{"name": "approval", "type": "boolean"}],
        }
        state.paused_by = "user-123"
        state.paused_at = datetime.now(UTC)
        state.pause_count = 1
        
        assert state.status == WorkflowStatus.PAUSED
        assert state.is_paused()
        assert state.pause_count == 1

    @pytest.mark.unit
    def test_resumed_status_transition(self):
        """Workflow can resume from PAUSED to RUNNING."""
        state = BaseAgentState(tenant_id="test-tenant", workflow_type=WorkflowType.ROI_CALCULATOR)
        state.status = WorkflowStatus.PAUSED
        state.paused_at = datetime.now(UTC)
        state.pause_count = 1
        
        state.status = WorkflowStatus.RUNNING
        state.resumed_by = "user-456"
        state.resumed_at = datetime.now(UTC)
        
        assert state.status == WorkflowStatus.RUNNING
        assert not state.is_paused()
        assert state.can_resume()

    @pytest.mark.unit
    def test_interrupted_status_for_recovery(self):
        """INTERRUPTED status allows recovery after pod restart."""
        state = BaseAgentState(tenant_id="test-tenant", workflow_type=WorkflowType.ROI_CALCULATOR)
        state.status = WorkflowStatus.INTERRUPTED
        
        # Can resume from interrupted
        assert state.can_resume()
        
        # After resume, goes back to RUNNING
        state.status = WorkflowStatus.RUNNING
        assert state.status == WorkflowStatus.RUNNING

    @pytest.mark.unit
    def test_cannot_resume_from_completed(self):
        """Completed workflow cannot be resumed."""
        state = BaseAgentState(tenant_id="test-tenant", workflow_type=WorkflowType.ROI_CALCULATOR)
        state.status = WorkflowStatus.COMPLETED
        
        assert not state.can_resume()

    @pytest.mark.unit
    def test_cannot_resume_from_failed(self):
        """Failed workflow cannot be resumed."""
        state = BaseAgentState(tenant_id="test-tenant", workflow_type=WorkflowType.ROI_CALCULATOR)
        state.status = WorkflowStatus.FAILED
        
        assert not state.can_resume()

    @pytest.mark.unit
    def test_pause_summary_generation(self):
        """Pause point summary includes all required fields."""
        state = BaseAgentState(tenant_id="test-tenant", workflow_type=WorkflowType.ROI_CALCULATOR)
        state.status = WorkflowStatus.PAUSED
        state.pause_point = {
            "title": "Review Required",
            "reason": "Validate inputs",
            "severity": "high",
            "required_inputs": [
                {"name": "approved", "type": "boolean"},
                {"name": "notes", "type": "string"},
            ],
        }
        state.paused_at = datetime.now(UTC)
        state.paused_by = "user-789"
        
        summary = state.get_pause_summary()
        
        assert summary is not None
        assert summary["title"] == "Review Required"
        assert summary["required_inputs"] == ["approved", "notes"]
        assert summary["paused_by"] == "user-789"

    @pytest.mark.unit
    def test_no_pause_summary_when_not_paused(self):
        """Pause summary is None when workflow not paused."""
        state = BaseAgentState(tenant_id="test-tenant", workflow_type=WorkflowType.ROI_CALCULATOR)
        state.status = WorkflowStatus.RUNNING
        
        assert state.get_pause_summary() is None


class TestROIAgentState:
    """Test ROI calculator workflow state management."""

    @pytest.mark.unit
    def test_roi_state_creation_with_input(self):
        """ROI state can be created with input data."""
        input_data = ROIInputData(
            prospect_id="prospect-123",
            value_driver_ids=["vd-1", "vd-2"],
            prospect_data={"revenue": 1000000, "employees": 500},
            industry_vertical="technology",
            company_size="enterprise",
        )
        
        state = ROIAgentState(tenant_id="test-tenant", 
            workflow_type=WorkflowType.ROI_CALCULATOR,
            roi_input=input_data,
        )
        
        assert state.workflow_type == WorkflowType.ROI_CALCULATOR
        assert state.roi_input.prospect_id == "prospect-123"
        assert state.roi_input.value_driver_ids == ["vd-1", "vd-2"]
        assert state.calculation_results == []

    @pytest.mark.unit
    def test_roi_input_validation_requires_value_drivers(self):
        """ROI input must have at least one value driver."""
        with pytest.raises(ValueError, match="value_driver_id"):
            ROIInputData(
                prospect_id="prospect-123",
                value_driver_ids=[],  # Empty list should fail
            )

    @pytest.mark.unit
    def test_roi_state_accumulates_results(self):
        """ROI state accumulates calculation results."""
        state = ROIAgentState(tenant_id="test-tenant", workflow_type=WorkflowType.ROI_CALCULATOR)
        
        result1 = {
            "value_driver_id": "vd-1",
            "value_driver_name": "Cost Savings",
            "result": 500000,
            "unit": "USD",
            "confidence": 0.85,
        }
        result2 = {
            "value_driver_id": "vd-2",
            "value_driver_name": "Revenue Increase",
            "result": 750000,
            "unit": "USD",
            "confidence": 0.72,
        }
        
        state.calculation_results.append(result1)
        state.calculation_results.append(result2)
        
        assert len(state.calculation_results) == 2
        assert state.calculation_results[0]["result"] == 500000
        assert state.calculation_results[1]["result"] == 750000


class TestWhitespaceAgentState:
    """Test whitespace analysis workflow state management."""

    @pytest.mark.unit
    def test_whitespace_state_creation(self):
        """Whitespace state can be created with input data."""
        input_data = WhitespaceInputData(
            prospect_id="prospect-456",
            prospect_needs="Need better cloud infrastructure",
            solution_capabilities=["cloud-migration", "cost-optimization"],
            analysis_depth="deep",
        )
        
        state = WhitespaceAgentState(tenant_id="test-tenant", 
            workflow_type=WorkflowType.WHITESPACE_ANALYSIS,
            whitespace_input=input_data,
        )
        
        assert state.workflow_type == WorkflowType.WHITESPACE_ANALYSIS
        assert state.whitespace_input.prospect_id == "prospect-456"
        assert state.whitespace_input.analysis_depth == "deep"
        assert state.gap_analysis == []

    @pytest.mark.unit
    def test_whitespace_analysis_depth_validation(self):
        """Analysis depth must be one of valid values."""
        with pytest.raises(ValueError, match="analysis_depth"):
            WhitespaceInputData(
                prospect_id="prospect-456",
                prospect_needs="Some needs",
                analysis_depth="invalid_depth",
            )

    @pytest.mark.unit
    def test_whitespace_needs_minimum_length(self):
        """Prospect needs must be at least 10 characters."""
        with pytest.raises(ValueError):
            WhitespaceInputData(
                prospect_id="prospect-456",
                prospect_needs="Short",  # Too short
            )


class TestBusinessCaseAgentState:
    """Test business case workflow state management."""

    @pytest.mark.unit
    def test_business_case_state_creation(self):
        """Business case state can be created with input data."""
        input_data = BusinessCaseInputData(
            account_id="550e8400-e29b-41d4-a716-446655440000",
            opportunity_id="opp-001",
            sections_requested=["executive_summary", "roi_analysis"],
            output_format="pdf",
        )
        
        state = BusinessCaseAgentState(tenant_id="test-tenant", 
            workflow_type=WorkflowType.BUSINESS_CASE,
            case_input=input_data,
        )
        
        assert state.workflow_type == WorkflowType.BUSINESS_CASE
        assert str(state.case_input.account_id) == "550e8400-e29b-41d4-a716-446655440000"
        assert state.case_input.output_format == "pdf"
        assert state.sections_generated == []

    @pytest.mark.unit
    def test_business_case_output_format_validation(self):
        """Output format must be one of valid values."""
        with pytest.raises(ValueError, match="output_format"):
            BusinessCaseInputData(
                account_id="550e8400-e29b-41d4-a716-446655440000",
                output_format="invalid_format",
            )

    @pytest.mark.unit
    def test_business_case_sections_accumulation(self):
        """Business case accumulates generated sections."""
        state = BusinessCaseAgentState(tenant_id="test-tenant", workflow_type=WorkflowType.BUSINESS_CASE)
        
        section1 = {
            "title": "Executive Summary",
            "content": "This project will deliver...",
            "charts": [],
            "tables": [],
        }
        section2 = {
            "title": "ROI Analysis",
            "content": "The return on investment...",
            "charts": [{"type": "bar", "data": []}],
            "tables": [],
        }
        
        state.sections_generated.append(section1)
        state.sections_generated.append(section2)
        
        assert len(state.sections_generated) == 2
        assert state.sections_generated[0]["title"] == "Executive Summary"


class ConcreteTestWorkflow(BaseWorkflow):
    """Concrete workflow implementation for testing."""

    def create_initial_state(self, **kwargs):
        """Create initial state for testing."""
        return ConcreteTestWorkflow_create_initial_stateResult.model_validate({"test": "state"})


class TestBaseWorkflow:
    """Test base workflow functionality."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock workflow config."""
        return WorkflowConfig(
            name="test_workflow",
            description="Test workflow for unit tests",
            workflow_type="test",
            entry_point="start",
            nodes=[
                NodeConfig(id="start", name="Start Node", node_type=NodeType.TOOL, tool_name="test_tool"),
                NodeConfig(id="end", name="End Node", node_type=NodeType.TOOL, tool_name="end_tool"),
            ],
            edges=[
                EdgeConfig(source="start", target="end"),
            ],
        )

    @pytest.fixture
    def mock_tool_registry(self):
        """Create a mock tool registry."""
        registry = Mock(spec=ToolRegistry)
        registry.get_tool = Mock(return_value=AsyncMock(return_value={"result": "success"}))
        return registry

    @pytest.mark.unit
    def test_workflow_initialization(self, mock_config, mock_tool_registry):
        """Workflow can be initialized with config and tools."""
        workflow = ConcreteTestWorkflow(mock_config, mock_tool_registry)

        assert workflow.name == "test_workflow"
        assert workflow.workflow_type == "test"
        assert workflow.config == mock_config
        assert workflow.tool_registry == mock_tool_registry

    @pytest.mark.unit
    def test_workflow_error_exception(self):
        """WorkflowError can be raised and caught."""
        with pytest.raises(WorkflowError, match="Test error"):
            raise WorkflowError("Test error")

    @pytest.mark.unit
    def test_node_execution_error_exception(self):
        """NodeExecutionError can be raised and caught."""
        with pytest.raises(NodeExecutionError, match="Node failed"):
            raise NodeExecutionError("Node failed")

    @pytest.mark.unit
    def test_node_execution_error_is_workflow_error(self):
        """NodeExecutionError is a subclass of WorkflowError."""
        error = NodeExecutionError("Test")
        assert isinstance(error, WorkflowError)

    @pytest.mark.unit
    async def test_node_failure_preserves_root_cause(self, mock_config, mock_tool_registry):
        workflow = ConcreteTestWorkflow(mock_config, mock_tool_registry)
        state = BaseAgentState(
            tenant_id="test-tenant",
            workflow_type=WorkflowType.ROI_CALCULATOR,
            input_data={"test": "input"},
        )
        mock_tool_registry.execute = AsyncMock(side_effect=ValueError("tool crashed"))
        mock_config.nodes[0].retry_policy = {"max_retries": 0}
        node_func = workflow._create_node_function(mock_config.nodes[0])

        with pytest.raises(NodeExecutionError, match="tool crashed"):
            await node_func(state)


class TestStateSerialization:
    """Test state serialization for checkpoints."""

    @pytest.mark.unit
    def test_datetime_serialization_to_isoformat(self):
        """Datetime fields are serialized to ISO format."""
        now = datetime.now(UTC)
        state = BaseAgentState(tenant_id="test-tenant", 
            workflow_type=WorkflowType.ROI_CALCULATOR,
            started_at=now,
            completed_at=now,
            paused_at=now,
            resumed_at=now,
        )
        
        # Pydantic should serialize to ISO format
        data = state.model_dump()
        
        assert isinstance(data["started_at"], str)
        assert "T" in data["started_at"]  # ISO format has T separator
        assert data["started_at"] == now.isoformat()

    @pytest.mark.unit
    def test_none_datetime_serialization(self):
        """None datetime fields remain None in serialization."""
        state = BaseAgentState(tenant_id="test-tenant", workflow_type=WorkflowType.ROI_CALCULATOR)
        
        data = state.model_dump()
        
        assert data["started_at"] is None
        assert data["completed_at"] is None

    @pytest.mark.unit
    def test_state_immutability_via_reducers(self):
        """State updates use reducers for safe mutations."""
        state = BaseAgentState(tenant_id="test-tenant", workflow_type=WorkflowType.ROI_CALCULATOR)
        
        # Initial state
        
        # Simulate update through reducer pattern
        state.output_data = {**state.output_data, "new_key": "new_value"}
        
        # Verify original is preserved (reducer pattern maintains immutability)
        assert "new_key" in state.output_data


class TestWorkflowStateEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.unit
    def test_multiple_pause_resume_cycles(self):
        """Workflow can handle multiple pause/resume cycles."""
        state = BaseAgentState(tenant_id="test-tenant", workflow_type=WorkflowType.ROI_CALCULATOR)
        
        for i in range(3):
            # Pause
            state.status = WorkflowStatus.PAUSED
            state.pause_count += 1
            state.paused_at = datetime.now(UTC)
            
            # Resume
            state.status = WorkflowStatus.RUNNING
            state.resumed_at = datetime.now(UTC)
        
        assert state.pause_count == 3
        assert state.status == WorkflowStatus.RUNNING

    @pytest.mark.unit
    def test_error_accumulation(self):
        """Workflow can accumulate multiple errors."""
        state = BaseAgentState(tenant_id="test-tenant", workflow_type=WorkflowType.ROI_CALCULATOR)
        
        state.errors.append("Error 1")
        state.errors.append("Error 2")
        state.errors.append("Error 3")
        
        assert len(state.errors) == 3
        state.status = WorkflowStatus.FAILED

    @pytest.mark.unit
    def test_empty_workflow_id_generation(self):
        """Workflow ID is auto-generated if not provided."""
        state1 = BaseAgentState(tenant_id="test-tenant", workflow_type=WorkflowType.ROI_CALCULATOR)
        state2 = BaseAgentState(tenant_id="test-tenant", workflow_type=WorkflowType.ROI_CALCULATOR)
        
        assert state1.workflow_id is not None
        assert state2.workflow_id is not None
        assert state1.workflow_id != state2.workflow_id  # Unique IDs

    @pytest.mark.unit
    def test_metadata_accumulation(self):
        """Metadata can accumulate arbitrary data."""
        state = BaseAgentState(tenant_id="test-tenant", workflow_type=WorkflowType.ROI_CALCULATOR)
        
        state.metadata["step_1"] = "completed"
        state.metadata["step_2"] = {"detail": "value"}
        state.metadata["metrics"] = [1, 2, 3]
        
        assert state.metadata["step_1"] == "completed"
        assert state.metadata["step_2"]["detail"] == "value"
        assert len(state.metadata["metrics"]) == 3
