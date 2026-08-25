from __future__ import annotations

"""Agent state definitions for LangGraph workflows.

Defines typed state schemas for all workflow types in Layer 4.
"""


from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Annotated, Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator
from value_fabric.shared.models.typed_dict import TypedDictModel

from .reasoning_trace import ReasoningTrace
from .run_envelope import RunEnvelope


class _merge_dictsResult(TypedDictModel):
    pass

class BaseAgentState_get_pause_summaryResult(TypedDictModel):
    paused_at: Any
    paused_by: Any
    reason: Any
    required_inputs: Any
    severity: Any
    title: Any

if TYPE_CHECKING:
    pass


def _last_value(left: Any, right: Any) -> Any:
    """Reducer that keeps the rightmost (last) value.

    Used with Annotated for LangGraph state fields that may receive
    multiple updates per step. Always returns the most recent value.
    """
    return right


def _merge_dicts(left: dict[str, Any] | None, right: dict[str, Any] | None) -> dict[str, Any]:
    """Reducer that merges two dicts, with right values taking precedence.

    Used with Annotated for output_data to accumulate node results.
    """
    return {**(left or {}), **(right or {})}


class WorkflowStatus(str, Enum):
    """Status of a workflow execution."""

    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    INTERRUPTED = "interrupted"  # Pod restart, recoverable
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkflowType(str, Enum):
    """Types of supported workflows per spec."""

    # Existing workflows
    ROI_CALCULATOR = "roi_calculator"
    WHITESPACE_ANALYSIS = "whitespace_analysis"
    BUSINESS_CASE = "business_case"
    ORCHESTRATOR = "orchestrator"

    # Additional spec workflows
    BUSINESS_CASE_GENERATION = "business_case_generation"
    DOCUMENT_INGESTION = "document_ingestion"
    FINANCIAL_EXTRACTION = "financial_extraction"
    VALUE_TREE_PROJECTION = "value_tree_projection"


class WorkflowNodeType(str, Enum):
    """Workflow node/states per spec definition."""

    # Document Ingestion
    DOCUMENT_INGESTION = "DOCUMENT_INGESTION"

    # Financial Extraction
    FINANCIAL_EXTRACTION = "FINANCIAL_EXTRACTION"

    # Value Tree Projection
    VALUE_TREE_PROJECTION = "VALUE_TREE_PROJECTION"

    # Whitespace Analysis
    WHITESPACE_IDENTIFICATION = "WHITESPACE_IDENTIFICATION"
    ACCOUNT_PLAN_GENERATION = "ACCOUNT_PLAN_GENERATION"

    # Business Case Generation
    OPPORTUNITY_EVALUATION = "OPPORTUNITY_EVALUATION"
    FORMULA_RETRIEVAL = "FORMULA_RETRIEVAL"
    METRIC_SUBSTITUTION = "METRIC_SUBSTITUTION"
    ROI_COMPUTATION = "ROI_COMPUTATION"
    SENSITIVITY_ANALYSIS = "SENSITIVITY_ANALYSIS"
    NARRATIVE_SYNTHESIS = "NARRATIVE_SYNTHESIS"
    OUTPUT_GENERATION = "OUTPUT_GENERATION"

    # Provenance
    PROVENANCE_RECORDING = "PROVENANCE_RECORDING"

    # Terminal states
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class TenantMissingError(ValueError):
    """Raised when a workflow is started without required tenant context."""

    pass


class BaseAgentState(BaseModel):
    """Base state shared across all workflows.

    Attributes:
        workflow_id: Unique identifier for this workflow instance
        run_id: Distinct execution identifier (separate from workflow_id)
        trace_id: Cross-layer audit trace identifier
        tenant_id: Owning tenant — required invariant at workflow start
        workflow_type: Type of workflow being executed
        status: Current execution status
        current_node: Name of the currently executing node
        input_data: Initial input parameters
        output_data: Accumulated results
        errors: List of errors encountered
        metadata: Additional execution metadata
        reasoning_trace: Structured reasoning trace for agent outputs
        run_envelope: Canonical run envelope for lifecycle consistency
        pause_point: Structured pause information when status is PAUSED
        paused_by: User who paused the workflow (if applicable)
        paused_at: When the workflow was paused
        resumed_by: User who resumed the workflow
        resumed_at: When the workflow was resumed
    """

    workflow_id: str = Field(default_factory=lambda: str(uuid4()))
    run_id: str = Field(default_factory=lambda: str(uuid4()))
    trace_id: str = Field(default_factory=lambda: str(uuid4()))
    tenant_id: str = Field(..., description="Owning tenant — required at workflow start")
    workflow_type: WorkflowType
    status: Annotated[WorkflowStatus, _last_value] = WorkflowStatus.PENDING
    current_node: Annotated[str | None, _last_value] = None
    input_data: Annotated[dict[str, Any], _merge_dicts] = Field(default_factory=dict)
    output_data: Annotated[dict[str, Any] | None, _merge_dicts] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)
    metadata: Annotated[dict[str, Any], _merge_dicts] = Field(default_factory=dict)
    reasoning_trace: ReasoningTrace | None = Field(
        default=None, description="Structured reasoning trace validated at output"
    )
    run_envelope: RunEnvelope | None = Field(
        default=None, description="Canonical run envelope for lifecycle consistency"
    )
    started_at: datetime | None = None
    completed_at: datetime | None = None

    # Human-in-the-loop fields
    pause_point: dict[str, Any] | None = Field(
        default=None, description="Structured pause point when workflow requires human input"
    )
    paused_by: str | None = Field(default=None, description="User who paused the workflow")
    paused_at: datetime | None = Field(default=None, description="When workflow was paused")
    resumed_by: str | None = Field(default=None, description="User who resumed the workflow")
    resumed_at: datetime | None = Field(default=None, description="When the workflow was resumed")
    pause_count: int = Field(default=0, description="Number of times workflow has been paused")

    model_config = ConfigDict()

    @field_validator("tenant_id")
    @classmethod
    def _tenant_id_required(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("tenant_id is required and must be non-empty")
        return v

    @field_serializer("started_at", "completed_at", "paused_at", "resumed_at")
    def serialize_datetime(self, v: datetime | None, _info) -> str | None:
        return v.isoformat() if v else None

    def is_paused(self) -> bool:
        """Check if workflow is currently paused."""
        return self.status == WorkflowStatus.PAUSED

    def can_resume(self) -> bool:
        """Check if workflow can be resumed."""
        return self.status in [
            WorkflowStatus.PAUSED,
            WorkflowStatus.RUNNING,
            WorkflowStatus.PENDING,
            WorkflowStatus.INTERRUPTED,  # Can resume after pod restart
        ]

    def get_pause_summary(self) -> dict[str, Any] | None:
        """Get summary of current pause point if paused."""
        if not self.is_paused() or not self.pause_point:
            return None
        return BaseAgentState_get_pause_summaryResult.model_validate({
            "title": self.pause_point.get("title"),
            "reason": self.pause_point.get("reason"),
            "severity": self.pause_point.get("severity"),
            "required_inputs": [
                field.get("name") for field in self.pause_point.get("required_inputs", [])
            ],
            "paused_at": self.paused_at.isoformat() if self.paused_at else None,
            "paused_by": self.paused_by,
        })


class ROIInputData(BaseModel):
    """Input data for ROI calculation workflow.

    Attributes:
        prospect_id: CRM identifier for the prospect
        value_driver_ids: Value drivers to calculate ROI for
        prospect_data: Prospect-specific variables
        industry_vertical: Industry for benchmark lookup
        company_size: Company size category
    """

    prospect_id: str
    value_driver_ids: list[str]
    prospect_data: dict[str, float] = Field(default_factory=dict)
    industry_vertical: str | None = None
    company_size: str | None = None
    use_benchmarks: bool = True

    @field_validator("value_driver_ids")
    @classmethod
    def validate_non_empty(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("At least one value_driver_id is required")
        return v

    @field_validator("prospect_id")
    @classmethod
    def validate_prospect_id(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("prospect_id is required")
        return v


class ROIResult(BaseModel):
    """Result of a single ROI calculation.

    Attributes:
        value_driver_id: ID of the value driver calculated
        value_driver_name: Human-readable name
        formula: Formula string used
        substituted_formula: Formula with values substituted
        result: Calculated ROI value
        unit: Unit of measurement (USD, %, etc.)
        confidence: Confidence score 0.0-1.0
        variables_used: Variables and their values
        missing_variables: Variables that couldn't be resolved
    """

    value_driver_id: str
    value_driver_name: str
    formula: str
    substituted_formula: str
    result: float
    unit: str
    confidence: float = Field(ge=0.0, le=1.0)
    variables_used: dict[str, float] = Field(default_factory=dict)
    missing_variables: list[str] = Field(default_factory=list)
    benchmark_comparison: dict[str, Any] | None = None


class ROIAgentState(BaseAgentState):
    """State for ROI Calculator workflow.

    Extends base state with ROI-specific fields.
    """

    workflow_type: WorkflowType = WorkflowType.ROI_CALCULATOR
    roi_input: ROIInputData | None = None
    prospect_data_enriched: dict[str, Any] = Field(default_factory=dict)
    benchmarks_fetched: dict[str, Any] = Field(default_factory=dict)
    calculation_results: list[ROIResult] = Field(default_factory=list)
    aggregated_roi: dict[str, Any] | None = None


class WhitespaceInputData(BaseModel):
    """Input data for whitespace analysis workflow.

    Attributes:
        prospect_id: CRM identifier for the prospect
        prospect_needs: Description of prospect's stated needs
        solution_capabilities: Capabilities to match against
        analysis_depth: Level of analysis detail
    """

    prospect_id: str
    prospect_needs: str = Field(..., min_length=10)
    solution_capabilities: list[str] | None = None
    analysis_depth: str = "standard"  # "quick", "standard", "deep"
    include_competitive: bool = True

    @field_validator("analysis_depth")
    @classmethod
    def validate_depth(cls, v: str) -> str:
        valid = {"quick", "standard", "deep"}
        if v not in valid:
            raise ValueError(f"analysis_depth must be one of {valid}")
        return v


class GapAnalysis(BaseModel):
    """Identified gap between need and capability.

    Attributes:
        need_statement: The prospect need identified
        matched_capability: Best matching capability (if any)
        match_score: Similarity score 0.0-1.0
        gap_type: Type of gap identified
        impact: Business impact assessment
        recommendation: Suggested action
    """

    need_statement: str
    matched_capability: str | None = None
    match_score: float = Field(ge=0.0, le=1.0)
    gap_type: str  # "coverage", "capability", "maturity", "none"
    impact: str = "medium"  # "low", "medium", "high"
    recommendation: str


class WhitespaceAgentState(BaseAgentState):
    """State for Whitespace Analysis workflow."""

    workflow_type: WorkflowType = WorkflowType.WHITESPACE_ANALYSIS
    whitespace_input: WhitespaceInputData | None = None
    extracted_needs: list[str] = Field(default_factory=list)
    capabilities_queried: list[dict[str, Any]] = Field(default_factory=list)
    gap_analysis: list[GapAnalysis] = Field(default_factory=list)
    opportunity_score: float | None = None
    recommendations: list[str] = Field(default_factory=list)


class BusinessCaseSection(BaseModel):
    """Section of a generated business case.

    Attributes:
        title: Section heading
        content: Generated text content
        charts: List of chart data for this section
        tables: List of table data for this section
    """

    title: str
    content: str
    charts: list[dict[str, Any]] = Field(default_factory=list)
    tables: list[dict[str, Any]] = Field(default_factory=list)


class BusinessCaseInputData(BaseModel):
    """Input data for business case generation workflow.

    Attributes:
        account_id: Account UUID identifier
        opportunity_id: CRM opportunity identifier
        sections_requested: Which sections to include
        output_format: Desired output format
    """

    account_id: UUID
    opportunity_id: str | None = None
    sections_requested: list[str] = Field(
        default_factory=lambda: [
            "executive_summary",
            "current_state",
            "proposed_solution",
            "roi_analysis",
            "implementation",
            "next_steps",
        ]
    )
    output_format: str = "pdf"  # "pdf", "docx", "html"
    custom_inputs: dict[str, Any] = Field(default_factory=dict)

    @field_validator("output_format")
    @classmethod
    def validate_format(cls, v: str) -> str:
        valid = {"pdf", "docx", "html", "json"}
        if v not in valid:
            raise ValueError(f"output_format must be one of {valid}")
        return v


class BusinessCaseAgentState(BaseAgentState):
    """State for Business Case Generator workflow."""

    workflow_type: WorkflowType = WorkflowType.BUSINESS_CASE
    case_input: BusinessCaseInputData | None = None
    sections_generated: list[BusinessCaseSection] = Field(default_factory=list)
    roi_results: dict[str, Any] | None = None
    assembled_document: bytes | None = None
    document_url: str | None = None


class OrchestratorAgentState(BaseAgentState):
    """State for Multi-Agent Orchestrator workflow."""

    workflow_type: WorkflowType = WorkflowType.ORCHESTRATOR
    user_intent: str | None = None
    identified_workflows: list[str] = Field(default_factory=list)
    sub_workflow_results: list[dict[str, Any]] = Field(default_factory=list)
    aggregated_response: str | None = None
    suggested_actions: list[str] = Field(default_factory=list)


# Union type for all workflow states
AgentState = ROIAgentState | WhitespaceAgentState | BusinessCaseAgentState | OrchestratorAgentState
