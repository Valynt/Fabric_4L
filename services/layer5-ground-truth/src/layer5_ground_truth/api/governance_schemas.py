from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ErrorEnvelope(BaseModel):
    """Standard error response envelope."""

    error: str = Field(..., description="Error type/category")
    message: str = Field(..., description="Human-readable error message")
    details: dict[str, Any] | None = Field(None, description="Additional error details")


class PaginatedResponse(BaseModel):
    """Standard paginated response envelope."""

    items: list[Any]
    total: int
    page: int
    page_size: int
    has_next: bool


class FormulaParameterCreate(BaseModel):
    """Schema for creating a formula parameter."""

    name: str = Field(..., max_length=128)
    display_name: str | None = Field(None, max_length=128)
    parameter_type: str = Field(..., description="number, string, boolean, currency, percentage, date, duration")
    description: str | None = None
    required: bool = True
    default_value: Any = None
    min_value: Any = None
    max_value: Any = None
    allowed_values: list[Any] | None = None


class FormulaCreate(BaseModel):
    """Schema for creating a formula."""

    name: str = Field(..., max_length=128)
    slug: str = Field(..., max_length=128)
    formula_type: str = Field(..., description="roi_calculation, cost_savings, revenue_impact, efficiency_gain, risk_reduction, custom")
    description: str | None = None
    expression: str = Field(..., description="Formula expression")
    expression_language: str = Field(default="python", description="python, javascript, etc.")
    input_schema: dict[str, Any] = Field(..., description="JSON Schema for input validation")
    output_schema: dict[str, Any] = Field(..., description="JSON Schema for output validation")
    parameters: list[FormulaParameterCreate] = Field(default_factory=list)


class FormulaResponse(BaseModel):
    """Schema for formula response."""

    id: UUID
    tenant_id: UUID
    name: str
    slug: str
    formula_type: str
    description: str | None
    current_version: str | None
    latest_version: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    is_active: bool
    deprecated_at: datetime | None
    deprecation_reason: str | None
    created_at: datetime
    updated_at: datetime


class FormulaVersionCreate(BaseModel):
    """Schema for creating a formula version."""

    version: str = Field(..., description="Semver version string")
    expression: str = Field(..., description="Formula expression")
    expression_language: str = Field(default="python")
    change_description: str | None = None


class FormulaVersionResponse(BaseModel):
    """Schema for formula version response."""

    id: UUID
    tenant_id: UUID
    formula_id: UUID
    version: str
    expression: str
    expression_language: str
    status: str
    validation_errors: dict[str, Any] | None
    test_results: dict[str, Any] | None
    change_description: str | None
    changed_by: str | None
    approved_by: str | None
    approved_at: datetime | None
    created_at: datetime


class BenchmarkCreate(BaseModel):
    """Schema for creating a benchmark."""

    name: str = Field(..., max_length=128)
    slug: str = Field(..., max_length=128)
    benchmark_type: str = Field(..., description="industry_standard, competitive, historical, customer_reference, internal, third_party")
    description: str | None = None
    source_name: str = Field(..., max_length=128)
    source_url: str | None = None
    source_type: str = Field(..., description="research, survey, internal, external")
    source_date: datetime | None = None
    collection_methodology: str | None = None
    confidence_level: str = Field(default="medium", description="high, medium, low")
    sample_size: int | None = None
    margin_of_error: dict[str, Any] | None = None
    data_quality_notes: str | None = None


class BenchmarkResponse(BaseModel):
    """Schema for benchmark response."""

    id: UUID
    tenant_id: UUID
    name: str
    slug: str
    benchmark_type: str
    description: str | None
    current_version: str
    latest_version: str
    source_name: str
    source_url: str | None
    source_type: str
    source_date: datetime | None
    confidence_level: str
    sample_size: int | None
    is_active: bool
    deprecated_at: datetime | None
    created_at: datetime
    updated_at: datetime


class BenchmarkVersionCreate(BaseModel):
    """Schema for creating a benchmark version."""

    version: str = Field(..., description="Semver version string")
    data: dict[str, Any] = Field(..., description="Benchmark data")
    data_schema: dict[str, Any] = Field(..., description="JSON Schema for data structure")
    effective_from: datetime = Field(..., description="Effective start date")
    effective_until: datetime | None = None
    change_description: str | None = None


class BenchmarkCreateWithVersion(BaseModel):
    """Schema for creating a benchmark with initial version."""

    name: str = Field(..., max_length=128)
    slug: str = Field(..., max_length=128)
    benchmark_type: str = Field(..., description="industry_standard, competitive, historical, customer_reference, internal, third_party")
    description: str | None = None
    source_name: str = Field(..., max_length=128)
    source_url: str | None = None
    source_type: str = Field(..., description="research, survey, internal, external")
    source_date: datetime | None = None
    collection_methodology: str | None = None
    confidence_level: str = Field(default="medium", description="high, medium, low")
    sample_size: int | None = None
    margin_of_error: dict[str, Any] | None = None
    data_quality_notes: str | None = None
    # Initial version data
    data: dict[str, Any] = Field(..., description="Benchmark data")
    data_schema: dict[str, Any] = Field(..., description="JSON Schema for data structure")
    effective_from: datetime = Field(..., description="Effective start date")
    effective_until: datetime | None = None
    version: str = Field(default="1.0.0", description="Initial version")


class PolicyRuleCreate(BaseModel):
    """Schema for creating a policy rule."""

    rule_name: str = Field(..., max_length=128)
    rule_type: str = Field(..., description="validation, constraint, business_rule, security, compliance")
    condition: dict[str, Any] = Field(..., description="Rule condition")
    action: str = Field(..., description="Action to take if condition is met")
    severity: str = Field(default="medium", description="high, medium, low")
    description: str | None = None


class PolicyCreate(BaseModel):
    """Schema for creating a policy."""

    name: str = Field(..., max_length=128)
    slug: str = Field(..., max_length=128)
    policy_type: str = Field(..., description="validation, approval, access_control, data_quality, compliance, security, custom")
    description: str = Field(..., description="Policy description")
    rules: list[PolicyRuleCreate] = Field(..., description="List of policy rules")
    severity: str = Field(default="medium", description="high, medium, low")
    scope: dict[str, Any] | None = None


class PolicyResponse(BaseModel):
    """Schema for policy response."""

    id: UUID
    tenant_id: UUID
    name: str
    slug: str
    policy_type: str
    description: str
    current_version: str | None
    latest_version: str
    severity: str
    scope: dict[str, Any] | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class PolicyEvaluationRequest(BaseModel):
    """Schema for policy evaluation request."""

    entity_id: UUID
    entity_type: str = Field(..., description="formula, benchmark, assumption, value_entry, etc.")
    context: dict[str, Any] = Field(..., description="Evaluation context")


class PolicyEvaluationResponse(BaseModel):
    """Schema for policy evaluation response."""

    policy_id: UUID
    entity_id: UUID
    entity_type: str
    is_compliant: bool
    passed_rules: list[dict[str, Any]]
    failed_rules: list[dict[str, Any]]
    evaluation_id: UUID
    evaluated_at: datetime


class AssumptionCreate(BaseModel):
    """Schema for creating an assumption."""

    name: str = Field(..., max_length=128)
    slug: str = Field(..., max_length=128)
    assumption_type: str = Field(..., description="market_growth, pricing, cost_structure, timeline, resource_availability, competitive_response, customer_behavior, technical_feasibility, regulatory, custom")
    description: str = Field(..., description="Detailed description of the assumption")
    value: dict[str, Any] = Field(..., description="Assumption value")
    value_type: str = Field(..., description="number, percentage, currency, string, boolean, date, duration")
    impact_level: str = Field(..., description="low, medium, high, critical")
    truth_object_id: UUID | None = None
    applies_to_opportunity_id: UUID | None = None
    applies_to_formula_id: UUID | None = None


class AssumptionResponse(BaseModel):
    """Schema for assumption response."""

    id: UUID
    tenant_id: UUID
    name: str
    slug: str
    assumption_type: str
    description: str
    value: dict[str, Any]
    value_type: str
    impact_level: str
    sensitivity_analysis: dict[str, Any] | None
    truth_object_id: UUID | None
    evidence_count: int
    status: str
    is_active: bool
    approval_request_id: UUID | None
    approved_by: str | None
    approved_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AssumptionEvidenceCreate(BaseModel):
    """Schema for adding evidence to an assumption."""

    evidence_type: str = Field(..., description="truth_object, external_source")
    truth_object_id: UUID | None = None
    source_url: str | None = None
    source_title: str | None = None
    excerpt: str | None = None
    confidence: str = Field(default="medium", description="high, medium, low")
    relevance: str = Field(default="medium", description="high, medium, low")
    notes: str | None = None


class ValueRealizationEntryCreate(BaseModel):
    """Schema for creating a value realization entry."""

    entry_type: str = Field(..., description="roi, cost_savings, revenue_impact, efficiency_gain, time_savings, risk_reduction, custom")
    entry_name: str = Field(..., max_length=128)
    description: str | None = None
    current_value: float = Field(..., description="Current value of the metric")
    value_unit: str | None = None
    value_currency: str | None = Field(default=None, max_length=3, description="ISO currency code")
    formula_id: UUID | None = None
    formula_version: str | None = None
    benchmark_id: UUID | None = None
    benchmark_version: str | None = None
    assumption_ids: list[UUID] | None = None
    opportunity_id: UUID | None = None
    account_id: UUID | None = None
    business_case_id: UUID | None = None


class ValueRealizationEntryResponse(BaseModel):
    """Schema for value realization entry response."""

    id: UUID
    tenant_id: UUID
    entry_type: str
    entry_name: str
    description: str | None
    current_value: float
    value_unit: str | None
    value_currency: str | None
    formula_id: UUID | None
    formula_version: str | None
    benchmark_id: UUID | None
    benchmark_version: str | None
    assumption_ids: list[UUID] | None
    opportunity_id: UUID | None
    account_id: UUID | None
    business_case_id: UUID | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ValueRealizationUpdateCreate(BaseModel):
    """Schema for creating a value realization update."""

    new_value: float = Field(..., description="New value after update")
    update_reason: str = Field(..., description="new_calculation, data_refresh, formula_change, benchmark_update, assumption_change, correction, revalidation, manual_override, other")
    update_notes: str | None = None
    formula_id_at_update: UUID | None = None
    formula_version_at_update: str | None = None
    benchmark_id_at_update: UUID | None = None
    benchmark_version_at_update: str | None = None
    assumption_ids_at_update: list[UUID] | None = None
    calculation_metadata: dict[str, Any] | None = None


class ApprovalRequestResponse(BaseModel):
    """Schema for approval request response."""

    id: UUID
    tenant_id: UUID
    entity_type: str
    entity_id: UUID
    entity_version: str | None
    status: str
    requested_by: str
    requested_at: datetime
    request_reason: str | None
    request_metadata: dict[str, Any] | None
    reviewed_by: str | None
    reviewed_at: datetime | None
    review_notes: str | None
    approved_at: datetime | None
    rejected_at: datetime | None
    created_at: datetime
    updated_at: datetime


