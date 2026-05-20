"""
Pydantic request/response schemas for the Layer 5 Ground Truth API.

Follows the same style as Layer 3's src/api/models.py:
  - Separate Request / Response models
  - Strict field validation with Field() descriptors
  - Enum imports from models (single source of truth)
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, JsonValue, field_validator, model_validator
from value_fabric.shared.models.typed_dict import TypedDictModel

# Re-export enums so API consumers only need to import from schemas
from ..services.freshness_contracts import (
    FreshnessCheckResponse,
    FreshnessCounts,
    FreshnessSummaryResponse,
)
from ..models.truth_object import (
    ClaimType,
    DisputeReason,
    MaturityLevel,
    SourceType,
    TruthStatus,
)

__all__ = [
    # Enums
    "ClaimType",
    "DeploymentEnvironment",
    "DeploymentStatus",
    "DisputeReason",
    "MaturityLevel",
    "ModelCapability",
    "ModelProvider",
    "SourceType",
    "TruthStatus",
    # Request models
    "TruthSourceCreate",
    "TruthValue",
    "TruthAppliesTo",
    "TruthObjectCreate",
    "ValidateRequest",
    "AddSourceRequest",
    "ModelVersionCreate",
    "ModelDeploymentCreate",
    "PromoteModelRequest",
    "RollbackModelRequest",
    "ModelEvaluationCreate",
    # Response models
    "TruthSourceResponse",
    "ValidationEventResponse",
    "MaturityHistoryResponse",
    "TruthObjectResponse",
    "TruthObjectSummary",
    "TruthObjectListResponse",
    "StaleTruthsResponse",
    "FreshnessCheckResponse",
    "FreshnessCounts",
    "FreshnessSummaryResponse",
    "SyncToKgResponse",
    "ValidateResponse",
    "HealthResponse",
    "MaturityLadderResponse",
    "ModelVersionResponse",
    "ModelVersionSummary",
    "ModelVersionListResponse",
    "ModelDeploymentResponse",
    "ModelDeploymentListResponse",
    "PromoteModelResponse",
    "RollbackModelResponse",
    "ModelEvaluationResponse",
    "ModelEvaluationListResponse",
]



JsonObject = dict[str, JsonValue]


class TruthValue(BaseModel):
    """Structured value payload attached to a truth claim."""

    amount: float | str | None = None
    unit: str | None = None
    currency: str | None = None
    period: str | None = None
    model_config = {"extra": "allow"}


class TruthAppliesTo(BaseModel):
    """Scope metadata for where a truth claim applies."""

    opportunity_id: str | None = None
    account_id: str | None = None
    industry: str | None = None
    product_line: str | None = None
    geography: str | None = None
    model_config = {"extra": "allow"}


class SyncToKgResponse(TypedDictModel):
    synced: int
    failed: int
    total_pending: int


# ---------------------------------------------------------------------------
# Source schemas
# ---------------------------------------------------------------------------


class TruthSourceCreate(BaseModel):
    """Schema for creating a new TruthSource."""

    source_type: SourceType = Field(
        default=SourceType.OTHER,
        description="Category of evidence",
    )
    source_url: str | None = Field(
        default=None,
        max_length=2048,
        description="URL or URI of the source document",
    )
    source_id: str | None = Field(
        default=None,
        max_length=255,
        description="Internal document / asset ID",
    )
    source_title: str | None = Field(
        default=None,
        max_length=512,
        description="Human-readable title of the source",
    )
    excerpt: str | None = Field(
        default=None,
        description="Verbatim excerpt supporting the claim",
    )
    excerpt_location: str | None = Field(
        default=None,
        max_length=255,
        description='Location within source, e.g. "page 3, paragraph 2"',
    )
    confidence_contribution: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Contribution to overall confidence (0.0–1.0)",
    )
    source_date: datetime | None = Field(
        default=None,
        description="Date the source was published or captured",
    )
    metadata: JsonObject = Field(default_factory=dict)


class TruthSourceResponse(TruthSourceCreate):
    """Schema for a TruthSource in API responses."""

    id: UUID
    truth_object_id: UUID
    tenant_id: UUID
    created_at: datetime
    created_by: str | None = None
    # Map from SQLAlchemy's extra_metadata column
    metadata: JsonObject = Field(default_factory=dict, alias="extra_metadata")

    model_config = {"from_attributes": True, "populate_by_name": True}

    @field_validator("metadata", mode="before")
    @classmethod
    def extract_metadata(cls, v: Any) -> JsonObject:
        """Handle both dict values and SQLAlchemy MetaData objects."""
        if isinstance(v, dict):
            return v
        if v is None:
            return TruthSourceResponse_extract_metadataResult.model_validate({})
        # Handle case where SQLAlchemy's MetaData is returned instead
        return TruthSourceResponse_extract_metadataResult.model_validate({})


# ---------------------------------------------------------------------------
# Validation event schemas
# ---------------------------------------------------------------------------


class ValidationEventResponse(BaseModel):
    """Schema for a ValidationEvent in API responses."""

    id: UUID
    from_status: str | None = None
    to_status: str
    from_maturity: int | None = None
    to_maturity: int
    actor: str | None = None
    actor_type: str
    confidence_at_transition: float | None = None
    source_count_at_transition: int | None = None
    notes: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Maturity history schemas
# ---------------------------------------------------------------------------


class MaturityHistoryResponse(BaseModel):
    """Schema for a MaturityHistory entry in API responses."""

    id: UUID
    from_level: int | None = None
    to_level: int
    trigger: str | None = None
    triggered_by: str | None = None
    context: JsonObject | None = None
    recorded_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# TruthObject create schema
# ---------------------------------------------------------------------------


class TruthObjectCreate(BaseModel):
    """
    Schema for POST /truths — create a new TruthObject.

    The tenant_id is injected from the auth context in the router;
    it is not accepted from the request body.
    """

    claim: str = Field(
        ...,
        min_length=5,
        max_length=2000,
        description='Natural-language claim, e.g. "20 hrs/month reconciling invoices"',
        examples=["Manual reporting costs 12 hours/week per analyst"],
    )
    claim_type: ClaimType = Field(
        default=ClaimType.OTHER,
        description="Semantic category of the claim",
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Extraction model confidence score",
        examples=[0.82],
    )
    value: TruthValue | None = Field(
        default=None,
        description=(
            "Structured value: {amount, unit, currency, period} "
            "e.g. {amount: 20, unit: 'hours', period: 'month'}"
        ),
        examples=[{"amount": 20, "unit": "hours", "period": "month"}],
    )
    applies_to: TruthAppliesTo | None = Field(
        default=None,
        description="Scope: {opportunity_id, account_id, industry, product_line, geography}",
        examples=[{"opportunity_id": "opp-123", "account_id": "acct-456"}],
    )
    extraction_job_id: str | None = Field(
        default=None,
        max_length=255,
        description="Layer 2 extraction job that produced this claim",
    )
    extraction_model: str | None = Field(
        default=None,
        max_length=128,
        description="LLM / model version used for extraction",
    )
    raw_extraction_data: JsonObject | None = Field(
        default=None,
        description="Original extraction payload for reproducibility",
    )
    sources: list[TruthSourceCreate] = Field(
        default_factory=list,
        description="Initial evidence sources (optional — can be added later via POST /truths/{id}/sources)",
    )

    @field_validator("claim")
    @classmethod
    def claim_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("claim must not be blank")
        return v.strip()


# ---------------------------------------------------------------------------
# TruthObject response schemas
# ---------------------------------------------------------------------------


class TruthObjectResponse(BaseModel):
    """
    Full TruthObject response including related sources and audit trail.
    """

    id: UUID
    tenant_id: UUID
    claim: str
    claim_type: str
    value: TruthValue | None = None
    confidence: float = Field(..., ge=0.0, le=1.0)
    status: str
    maturity_level: int
    approved_by: str | None = None
    approved_at: datetime | None = None
    approval_notes: str | None = None
    freshness: datetime
    expires_at: datetime | None = None
    is_stale: bool
    applies_to: TruthAppliesTo | None = None
    dispute_reason: str | None = None
    dispute_notes: str | None = None
    disputed_by: str | None = None
    disputed_at: datetime | None = None
    kg_node_id: str | None = None
    kg_synced_at: datetime | None = None
    extraction_job_id: str | None = None
    extraction_model: str | None = None
    created_at: datetime
    updated_at: datetime

    # Related records
    sources: list[TruthSourceResponse] = Field(default_factory=list)
    validation_events: list[ValidationEventResponse] = Field(default_factory=list)
    maturity_history: list[MaturityHistoryResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class TruthObjectSummary(BaseModel):
    """Lightweight summary for list responses."""

    id: UUID
    claim: str
    claim_type: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    status: str
    maturity_level: int
    is_stale: bool
    source_count: int = 0
    approved_by: str | None = None
    freshness: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class TruthObjectListResponse(BaseModel):
    """Paginated list of TruthObjects."""

    items: list[TruthObjectSummary]
    total: int
    limit: int
    offset: int
    has_more: bool


class StaleTruthsResponse(TruthObjectListResponse):
    """Paginated list of stale TruthObjects."""


# ---------------------------------------------------------------------------
# Validate request/response
# ---------------------------------------------------------------------------


class ValidateRequest(BaseModel):
    """
    Schema for POST /truths/{id}/validate — trigger a state transition.

    action values:
      advance_supported     — EXTRACTED → SUPPORTED
      advance_corroborated  — SUPPORTED → CORROBORATED
      approve               — CORROBORATED → APPROVED (requires actor)
      dispute               — ANY → DISPUTED (requires dispute_reason)
      resolve_dispute       — DISPUTED → CORROBORATED
      operationalize        — APPROVED → maturity 5 (status stays APPROVED)
    """

    action: str = Field(
        ...,
        description=(
            "Transition to apply: advance_supported | advance_corroborated | "
            "approve | dispute | resolve_dispute | operationalize"
        ),
        examples=["approve"],
    )
    actor: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="User ID or service name triggering the transition",
        examples=["john.doe@company.com"],
    )
    actor_type: str = Field(
        default="human",
        description="'human' | 'system' | 'agent'",
    )
    notes: str | None = Field(
        default=None,
        max_length=2000,
        description="Optional notes for the audit trail",
    )
    dispute_reason: DisputeReason | None = Field(
        default=None,
        description="Required when action == 'dispute'",
    )

    @model_validator(mode="after")
    def validate_dispute_fields(self) -> "ValidateRequest":
        if self.action == "dispute" and not self.dispute_reason:
            raise ValueError("dispute_reason is required when action is 'dispute'")
        return self


class ValidateResponse(BaseModel):
    """Response after a validation action."""

    truth_object_id: UUID
    previous_status: str
    new_status: str
    previous_maturity: int
    new_maturity: int
    actor: str
    transition_allowed: bool = True
    message: str


# ---------------------------------------------------------------------------
# Add source request
# ---------------------------------------------------------------------------


class AddSourceRequest(TruthSourceCreate):
    """Schema for POST /truths/{id}/sources."""

    pass


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


class HealthResponse(BaseModel):
    """Health check response - public endpoint returns only safe fields."""

    status: str
    version: str
    timestamp: datetime
    # Optional internal fields - NOT returned by public health endpoint
    # Use internal readiness endpoint for dependency details
    database: str | None = None
    layer3_connected: bool | None = None
    layer3_url: str | None = None


# ---------------------------------------------------------------------------
# Maturity ladder reference
# ---------------------------------------------------------------------------


class MaturityLevelDetail(BaseModel):
    level: int
    name: str
    description: str
    required_status: str
    advancement_trigger: str


class MaturityLadderResponse(BaseModel):
    """Reference endpoint — returns the full maturity ladder definition."""

    levels: list[MaturityLevelDetail]


# ---------------------------------------------------------------------------
# Model Registry schemas
# ---------------------------------------------------------------------------

# Re-export enums
from ..models.model_registry import (
    DeploymentEnvironment,
    DeploymentStatus,
    ModelCapability,
    ModelProvider,
)


class TruthSourceResponse_extract_metadataResult(TypedDictModel):
    pass


class ModelVersionCreate(BaseModel):
    """Schema for registering a new ModelVersion."""

    name: str = Field(
        ...,
        max_length=128,
        description="Model name, e.g., 'gpt-4-turbo'",
    )
    provider: ModelProvider = Field(
        ...,
        description="LLM provider",
    )
    version: str = Field(
        ...,
        max_length=64,
        description="Semver or provider version string",
    )
    model_identifier: str = Field(
        ...,
        max_length=128,
        description="Provider's API identifier",
    )
    capabilities: list[ModelCapability] = Field(
        default_factory=list,
        description="List of supported capabilities",
    )
    context_window: int = Field(
        default=4096,
        ge=1,
        description="Maximum context window in tokens",
    )
    max_output_tokens: int | None = Field(
        default=None,
        ge=1,
        description="Maximum output tokens",
    )
    cost_per_1k_input: float = Field(
        default=0.0,
        ge=0,
        description="Cost per 1,000 input tokens in USD",
    )
    cost_per_1k_output: float = Field(
        default=0.0,
        ge=0,
        description="Cost per 1,000 output tokens in USD",
    )
    cost_per_1k_cached: float | None = Field(
        default=None,
        ge=0,
        description="Cost per 1,000 cached tokens",
    )
    description: str | None = Field(
        default=None,
        description="Human-readable description",
    )
    extra_metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional provider-specific metadata",
    )
    is_default: bool = Field(
        default=False,
        description="Whether this is the default model for the provider",
    )


class ModelVersionResponse(BaseModel):
    """Schema for a ModelVersion in API responses."""

    id: UUID
    tenant_id: UUID
    name: str
    provider: str
    version: str
    model_identifier: str
    capabilities: list[str]
    context_window: int
    max_output_tokens: int | None
    cost_per_1k_input: float
    cost_per_1k_output: float
    cost_per_1k_cached: float | None
    is_active: bool
    is_default: bool
    description: str | None
    extra_metadata: dict[str, Any] | None = None
    created_by: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ModelVersionSummary(BaseModel):
    """Summary view of a ModelVersion for list responses."""

    id: UUID
    name: str
    provider: str
    version: str
    is_active: bool
    is_default: bool
    cost_per_1k_input: float
    cost_per_1k_output: float
    created_at: datetime

    model_config = {"from_attributes": True}


class ModelVersionListResponse(BaseModel):
    """Paginated list of ModelVersions."""

    items: list[ModelVersionSummary]
    total: int
    limit: int
    offset: int
    has_more: bool


class ModelDeploymentCreate(BaseModel):
    """Schema for creating a new ModelDeployment."""

    model_version_id: UUID = Field(
        ...,
        description="ID of the model version to deploy",
    )
    environment: DeploymentEnvironment = Field(
        ...,
        description="Target environment",
    )
    traffic_percentage: int = Field(
        default=0,
        ge=0,
        le=100,
        description="Traffic percentage for canary (0-100)",
    )
    is_default_for_env: bool = Field(
        default=False,
        description="Whether this is the default model for this environment",
    )
    deployment_notes: str | None = Field(
        default=None,
        description="Notes about this deployment",
    )


class ModelDeploymentResponse(BaseModel):
    """Schema for a ModelDeployment in API responses."""

    id: UUID
    tenant_id: UUID
    model_version_id: UUID
    environment: str
    status: str
    traffic_percentage: int
    is_default_for_env: bool
    deployed_at: datetime | None
    deployed_by: str | None
    deployment_notes: str | None
    error_rate_5m: float | None
    latency_p50_ms: int | None
    latency_p99_ms: int | None
    last_health_check: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ModelDeploymentListResponse(BaseModel):
    """List of ModelDeployments."""

    items: list[ModelDeploymentResponse]
    total: int


class PromoteModelRequest(BaseModel):
    """Schema for promoting a model to an environment."""

    environment: DeploymentEnvironment = Field(
        ...,
        description="Target environment",
    )
    traffic_percentage: int = Field(
        default=100,
        ge=0,
        le=100,
        description="Traffic percentage (0-100)",
    )
    make_default: bool = Field(
        default=False,
        description="Whether to make this the default model for the environment",
    )


class PromoteModelResponse(BaseModel):
    """Response after promoting a model."""

    deployment_id: UUID
    model_version_id: UUID
    environment: str
    status: str
    traffic_percentage: int
    is_default_for_env: bool
    deployed_at: datetime
    message: str


class RollbackModelRequest(BaseModel):
    """Schema for rolling back a deployment."""

    reason: str = Field(
        ...,
        min_length=1,
        description="Reason for rollback",
    )


class RollbackModelResponse(BaseModel):
    """Response after rolling back a deployment."""

    deployment_id: UUID
    previous_status: str
    new_status: str
    rolled_back_at: datetime
    message: str


class ModelEvaluationCreate(BaseModel):
    """Schema for recording a model evaluation."""

    model_version_id: UUID = Field(
        ...,
        description="ID of the evaluated model version",
    )
    benchmark_name: str = Field(
        ...,
        max_length=128,
        description="Name of the benchmark",
    )
    benchmark_version: str | None = Field(
        default=None,
        max_length=64,
        description="Version of the benchmark dataset",
    )
    score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Primary score (0.0-1.0)",
    )
    score_details: dict[str, Any] = Field(
        default_factory=dict,
        description="Detailed scores by category",
    )
    sample_size: int | None = Field(
        default=None,
        ge=1,
        description="Number of samples evaluated",
    )
    cost_usd: float | None = Field(
        default=None,
        ge=0,
        description="Total cost of evaluation in USD",
    )
    duration_seconds: int | None = Field(
        default=None,
        ge=0,
        description="Duration of evaluation in seconds",
    )
    evaluation_config: dict[str, Any] = Field(
        default_factory=dict,
        description="Configuration used for evaluation",
    )
    notes: str | None = Field(
        default=None,
        description="Human notes about the evaluation",
    )
    artifact_urls: list[str] = Field(
        default_factory=list,
        description="Links to evaluation artifacts",
    )


class ModelEvaluationResponse(BaseModel):
    """Schema for a ModelEvaluation in API responses."""

    id: UUID
    tenant_id: UUID
    model_version_id: UUID
    benchmark_name: str
    benchmark_version: str | None
    score: float
    score_details: dict[str, Any]
    sample_size: int | None
    cost_usd: float | None
    duration_seconds: int | None
    evaluated_at: datetime
    evaluated_by: str | None
    notes: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ModelEvaluationListResponse(BaseModel):
    """List of ModelEvaluations."""

    items: list[ModelEvaluationResponse]
    total: int
