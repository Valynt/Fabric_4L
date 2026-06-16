from __future__ import annotations

"""Tool input/output schemas.

Pydantic models defining the interface for all 24 tools in the registry.
"""


from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class ToolCategory(str, Enum):
    """Categories of tools."""

    KNOWLEDGE = "knowledge"
    CALCULATION = "calculation"
    CRM = "crm"
    GENERATION = "generation"
    INTEGRATION = "integration"
    UTILITY = "utility"


class ToolSchema(BaseModel):
    """Schema definition for a tool.

    Attributes:
        name: Tool identifier
        category: Tool category
        description: Human-readable description
        input_schema: Input parameter schema
        output_schema: Output result schema
        examples: Example inputs/outputs
    """

    name: str
    category: ToolCategory
    description: str
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    examples: list[dict[str, Any]] = Field(default_factory=list)
    timeout_seconds: int = 30
    requires_auth: bool = False


# ============================================================================
# KNOWLEDGE TOOLS (6)
# ============================================================================


class QueryGraphInput(BaseModel):
    """Input for query_graph tool."""

    cypher_query: str = Field(..., description="Cypher query to execute")
    parameters: dict[str, Any] = Field(default_factory=dict)
    read_only: bool = True
    tenant_id: str | None = Field(default=None, description="Owning tenant for queries run outside a request context")


class QueryGraphOutput(BaseModel):
    """Output from query_graph tool."""

    results: list[dict[str, Any]] = Field(default_factory=list)
    columns: list[str] = Field(default_factory=list)
    row_count: int = 0
    execution_time_ms: int = 0
    error: str | None = None


class SemanticSearchInput(BaseModel):
    """Input for semantic_search tool."""

    query: str = Field(..., min_length=1)
    entity_types: list[str] | None = None
    top_k: int = Field(default=10, ge=1, le=100)
    similarity_threshold: float = Field(default=0.7, ge=0.0, le=1.0)


class SemanticSearchOutput(BaseModel):
    """Output from semantic_search tool."""

    results: list[dict[str, Any]] = Field(default_factory=list)
    total_matches: int = 0
    query_embedding_time_ms: int = 0


class GetEntityInput(BaseModel):
    """Input for get_entity tool."""

    entity_id: str
    include_relationships: bool = True
    depth: int = Field(default=1, ge=0, le=3)


class GetEntityOutput(BaseModel):
    """Output from get_entity tool."""

    entity: dict[str, Any] | None = None
    relationships: list[dict[str, Any]] = Field(default_factory=list)
    found: bool = False


class GetRelationshipsInput(BaseModel):
    """Input for get_relationships tool."""

    entity_id: str
    predicate: str | None = None
    direction: Literal["outgoing", "incoming", "both"] = "both"
    limit: int = Field(default=50, ge=1, le=500)


class GetRelationshipsOutput(BaseModel):
    """Output from get_relationships tool."""

    relationships: list[dict[str, Any]] = Field(default_factory=list)
    total_count: int = 0


class TraverseTreeInput(BaseModel):
    """Input for traverse_tree tool."""

    start_entity_id: str
    path_pattern: str  # e.g., "(Capability)-[:ENABLES]->(UseCase)"
    max_depth: int = Field(default=3, ge=1, le=10)


class TraverseTreeOutput(BaseModel):
    """Output from traverse_tree tool."""

    paths: list[list[dict[str, Any]]] = Field(default_factory=list)
    nodes_discovered: int = 0


class FindPathsInput(BaseModel):
    """Input for find_paths tool."""

    source_id: str
    target_id: str
    max_length: int = Field(default=6, ge=1, le=10)
    relationship_types: list[str] | None = None


class FindPathsOutput(BaseModel):
    """Output from find_paths tool."""

    paths: list[dict[str, Any]] = Field(default_factory=list)
    shortest_path_length: int | None = None


# ============================================================================
# CALCULATION TOOLS (4)
# ============================================================================


class EvaluateFormulaInput(BaseModel):
    """Input for evaluate_formula tool."""

    formula: str = Field(..., min_length=1)
    variables: dict[str, float] = Field(default_factory=dict)
    unit: str = "USD"

    @model_validator(mode="before")
    @classmethod
    def accept_legacy_expression_alias(cls, data: Any) -> Any:
        if isinstance(data, dict) and "formula" not in data and "expression" in data:
            data = dict(data)
            data["formula"] = data["expression"]
        return data

    @field_validator("formula")
    @classmethod
    def validate_formula_chars(cls, v: str) -> str:
        allowed = set("0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_+-*/().{} ")
        invalid = set(v) - allowed
        if invalid:
            raise ValueError(f"Invalid characters in formula: {invalid}")
        return v


class EvaluateFormulaOutput(BaseModel):
    """Output from evaluate_formula tool."""

    result: float | None = None
    substituted_formula: str = ""
    error: str | None = None
    success: bool = False


class CalculateROIInput(BaseModel):
    """Input for calculate_roi tool."""

    investment: float = Field(..., ge=0)
    returns: list[float] = Field(default_factory=list)
    time_periods: int = Field(default=3, ge=1)
    discount_rate: float = Field(default=0.1, ge=0.0, le=1.0)

    @model_validator(mode="before")
    @classmethod
    def accept_legacy_benefit_cost_shape(cls, data: Any) -> Any:
        if not isinstance(data, dict) or "investment" in data:
            return data

        costs = data.get("costs")
        benefits = data.get("benefits")
        if costs is None and benefits is None:
            return data

        def _amounts(items: Any) -> list[float]:
            amounts: list[float] = []
            if isinstance(items, list):
                for item in items:
                    if isinstance(item, dict) and item.get("amount") is not None:
                        amounts.append(float(item["amount"]))
            return amounts

        normalized = dict(data)
        normalized["investment"] = sum(_amounts(costs))
        normalized["returns"] = _amounts(benefits)
        if data.get("timeframe_months"):
            normalized["time_periods"] = max(1, int(data["timeframe_months"]) // 12)
        return normalized


class CalculateROIOutput(BaseModel):
    """Output from calculate_roi tool."""

    simple_roi_percent: float
    npv: float
    irr: float | None = None
    payback_period_months: float | None = None
    total_return: float


class CompareBenchmarksInput(BaseModel):
    """Input for compare_benchmarks tool."""

    metric_name: str
    value: float
    industry: str | None = None
    company_size: str | None = None
    region: str | None = None


class CompareBenchmarksOutput(BaseModel):
    """Output from compare_benchmarks tool."""

    percentile: float = Field(ge=0.0, le=100.0)
    industry_average: float | None = None
    comparison_text: str
    confidence: float = Field(ge=0.0, le=1.0)


class SensitivityAnalysisInput(BaseModel):
    """Input for sensitivity_analysis tool."""

    base_formula: str
    base_variables: dict[str, float]
    variable_ranges: dict[str, tuple]  # {"var": (min, max, steps)}


class SensitivityAnalysisOutput(BaseModel):
    """Output from sensitivity_analysis tool."""

    scenarios: list[dict[str, Any]] = Field(default_factory=list)
    tornado_data: list[dict[str, Any]] = Field(default_factory=list)
    optimal_variables: dict[str, float] | None = None


# ============================================================================
# CRM TOOLS (4)
# ============================================================================


class GetProspectDataInput(BaseModel):
    """Input for get_prospect_data tool."""

    prospect_id: str
    data_types: list[str] = Field(
        default_factory=lambda: ["profile", "interactions", "opportunities"]
    )
    prospect_data: dict[str, Any] = Field(default_factory=dict)


class GetProspectDataOutput(BaseModel):
    """Output from get_prospect_data tool."""

    profile: dict[str, Any] = Field(default_factory=dict)
    interactions: list[dict[str, Any]] = Field(default_factory=list)
    opportunities: list[dict[str, Any]] = Field(default_factory=list)
    custom_fields: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class UpdateOpportunityInput(BaseModel):
    """Input for update_opportunity tool."""

    opportunity_id: str
    updates: dict[str, Any]
    notify_owner: bool = True


class UpdateOpportunityOutput(BaseModel):
    """Output from update_opportunity tool."""

    success: bool
    opportunity_id: str
    updated_fields: list[str] = Field(default_factory=list)
    error: str | None = None


class FetchInteractionHistoryInput(BaseModel):
    """Input for fetch_interaction_history tool."""

    prospect_id: str
    interaction_types: list[str] | None = None
    since_date: str | None = None
    limit: int = Field(default=50, ge=1, le=200)


class FetchInteractionHistoryOutput(BaseModel):
    """Output from fetch_interaction_history tool."""

    interactions: list[dict[str, Any]] = Field(default_factory=list)
    total_count: int = 0
    summary: str = ""


class ScoreLeadInput(BaseModel):
    """Input for score_lead tool."""

    prospect_id: str
    scoring_model: str = "default"
    factors: list[str] | None = None


class ScoreLeadOutput(BaseModel):
    """Output from score_lead tool."""

    score: float = Field(ge=0.0, le=100.0)
    grade: str  # "A", "B", "C", "D", "F"
    factors: dict[str, float] = Field(default_factory=dict)
    recommendations: list[str] = Field(default_factory=list)


# ============================================================================
# GENERATION TOOLS (4)
# ============================================================================


class GenerateSectionInput(BaseModel):
    """Input for generate_section tool."""

    section_type: str  # "executive_summary", "roi_analysis", etc.
    context: dict[str, Any] = Field(default_factory=dict)
    tone: str = "professional"
    max_length: int = Field(default=500, ge=100, le=2000)


class GenerateSectionOutput(BaseModel):
    """Output from generate_section tool."""

    content: str
    word_count: int
    key_points: list[str] = Field(default_factory=list)
    error: str | None = None


class CreateChartInput(BaseModel):
    """Input for create_chart tool."""

    chart_type: Literal["bar", "line", "pie", "table", "funnel"]
    data: list[dict[str, Any]]
    title: str
    config: dict[str, Any] = Field(default_factory=dict)


class CreateChartOutput(BaseModel):
    """Output from create_chart tool."""

    chart_data: dict[str, Any] = Field(default_factory=dict)
    image_data: bytes | None = None
    image_url: str | None = None


class FormatTableInput(BaseModel):
    """Input for format_table tool."""

    headers: list[str]
    rows: list[list[Any]]
    format: Literal["html", "markdown", "csv"] = "html"
    sort_column: int | None = None


class FormatTableOutput(BaseModel):
    """Output from format_table tool."""

    formatted: str
    row_count: int


class AssembleDocumentInput(BaseModel):
    """Input for assemble_document tool."""

    sections: list[dict[str, Any]]
    template: str = "business_case"
    output_format: Literal["pdf", "docx", "html", "json"] = "pdf"
    branding: dict[str, Any] | None = None


class AssembleDocumentOutput(BaseModel):
    """Output from assemble_document tool."""

    document_bytes: bytes | None = None
    document_url: str | None = None
    page_count: int = 0
    file_size_bytes: int = 0


class ExportDocumentInput(BaseModel):
    """Input for export_document tool."""

    document_type: Literal["business_case", "audit_report", "roi_analysis"] = "business_case"
    business_case_data: dict[str, Any] = Field(
        default_factory=dict,
        description="Structured business case data with title, organization, use_cases, etc.",
    )
    template: str | None = Field(None, description="Optional custom HTML template string")
    branding: dict[str, str] | None = Field(
        None, description="Branding config: logo_url, primary_color, company_name"
    )


class ExportDocumentOutput(BaseModel):
    """Output from export_document tool."""

    pdf_bytes: bytes | None = None
    content_type: str = "application/pdf"
    filename: str = "document.pdf"
    success: bool = False
    error: str | None = None
    file_size_bytes: int = 0


# ============================================================================
# INTEGRATION TOOLS (4)
# ============================================================================


class SendNotificationInput(BaseModel):
    """Input for send_notification tool."""

    channel: Literal["email", "slack", "teams"]
    recipients: list[str]
    subject: str
    message: str
    attachments: list[dict[str, Any]] | None = None


class SendNotificationOutput(BaseModel):
    """Output from send_notification tool."""

    success: bool
    message_id: str | None = None
    error: str | None = None


class CreateTaskInput(BaseModel):
    """Input for create_task tool."""

    title: str
    description: str
    assignee: str | None = None
    due_date: str | None = None
    priority: Literal["low", "medium", "high"] = "medium"
    related_to: dict[str, str] | None = None


class CreateTaskOutput(BaseModel):
    """Output from create_task tool."""

    task_id: str | None = None
    success: bool
    url: str | None = None


class ScheduleMeetingInput(BaseModel):
    """Input for schedule_meeting tool."""

    title: str
    attendees: list[str]
    duration_minutes: int = Field(default=30, ge=15, le=240)
    preferred_times: list[str] | None = None
    description: str | None = None


class ScheduleMeetingOutput(BaseModel):
    """Output from schedule_meeting tool."""

    meeting_id: str | None = None
    scheduled_time: str | None = None
    calendar_link: str | None = None
    success: bool


class ExportToCRMInput(BaseModel):
    """Input for export_to_crm tool."""

    entity_type: Literal["note", "document", "activity"]
    entity_data: dict[str, Any]
    prospect_id: str


class ExportToCRMOutput(BaseModel):
    """Output from export_to_crm tool."""

    crm_record_id: str | None = None
    success: bool
    url: str | None = None


# ============================================================================
# UTILITY TOOLS (2)
# ============================================================================


class ValidateInputInput(BaseModel):
    """Input for validate_input tool."""

    data: dict[str, Any]
    schema_name: str
    strict: bool = True


class ValidateInputOutput(BaseModel):
    """Output from validate_input tool."""

    valid: bool
    errors: list[str] = Field(default_factory=list)
    normalized: dict[str, Any] = Field(default_factory=dict)


class FormatCurrencyInput(BaseModel):
    """Input for format_currency tool."""

    amount: float
    currency: str = "USD"
    locale: str = "en_US"
    decimals: int = 0


class FormatCurrencyOutput(BaseModel):
    """Output from format_currency tool."""

    formatted: str
    numeric: float
    currency: str
