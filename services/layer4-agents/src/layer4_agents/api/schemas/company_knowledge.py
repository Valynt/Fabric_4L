from __future__ import annotations

"""Pydantic schemas for Company Knowledge Onboarding API.

Request/response models for profiles, sources, extraction records, and ICP.
"""


from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ...models.company_knowledge import (
    AuthorityWeight,
    CrawlStatus,
    ICPSourceType,
    PageType,
    ProfileStatus,
    ReviewStatus,
    SourceType,
)

# ============================================================================
# Typed JSONB Sub-Schemas
# ============================================================================


class CompanyIdentitySchema(BaseModel):
    """Company identity section."""

    short_description: str | None = None
    long_description: str | None = None
    category: str | None = None
    market_positioning: str | None = None
    primary_business_model: str | None = None


class ProductItemSchema(BaseModel):
    """Single product in the catalog."""

    name: str
    description: str | None = None
    capabilities: list[str] = Field(default_factory=list)
    feature_groups: list[str] = Field(default_factory=list)


class ProductCatalogSchema(BaseModel):
    """Product catalog section."""

    products: list[ProductItemSchema] = Field(default_factory=list)
    platform_structure: str | None = None


class TargetCustomerSchema(BaseModel):
    """Target customer / ICP-aligned section."""

    industries: list[str] = Field(default_factory=list)
    company_size: list[str] = Field(default_factory=list)
    geography: list[str] = Field(default_factory=list)
    buying_triggers: list[str] = Field(default_factory=list)


class PersonaSchema(BaseModel):
    """Single persona definition."""

    role: str
    goals: list[str] = Field(default_factory=list)
    pain_points: list[str] = Field(default_factory=list)
    objections: list[str] = Field(default_factory=list)
    success_metrics: list[str] = Field(default_factory=list)
    relevant_value_drivers: list[str] = Field(default_factory=list)


class UseCaseSchema(BaseModel):
    """Single use case definition."""

    name: str
    description: str | None = None
    primary: bool = False
    industry_specific: bool = False
    persona_specific: bool = False
    required_capabilities: list[str] = Field(default_factory=list)


class ValueDriverSchema(BaseModel):
    """Single value driver with evidence."""

    name: str
    category: str | None = Field(None, description="Revenue Uplift | Cost Savings | Risk Reduction")
    description: str | None = None
    metric_candidates: list[str] = Field(default_factory=list)
    relevant_personas: list[str] = Field(default_factory=list)
    supporting_proof: list[str] = Field(default_factory=list)
    confidence: float | None = Field(None, ge=0.0, le=1.0)


class ProofPointSchema(BaseModel):
    """Single proof point / evidence item."""

    type: str | None = Field(None, description="case_study | quote | quantified_outcome | logo | analyst | compliance | integration")
    description: str | None = None
    source_url: str | None = None
    linked_products: list[str] = Field(default_factory=list)
    linked_use_cases: list[str] = Field(default_factory=list)
    linked_value_drivers: list[str] = Field(default_factory=list)


class TrustCommercialSchema(BaseModel):
    """Trust and commercial context section."""

    security_certifications: list[str] = Field(default_factory=list)
    compliance_claims: list[str] = Field(default_factory=list)
    pricing_model: str | None = None
    packaging: str | None = None
    integrations: list[str] = Field(default_factory=list)
    deployment_model: str | None = None
    implementation_requirements: str | None = None


class SectionReviewStateSchema(BaseModel):
    """Per-section review state."""

    section: str
    status: ReviewStatus
    reviewed_by: UUID | None = None
    reviewed_at: datetime | None = None
    notes: str | None = None


# ============================================================================
# Knowledge Source Schemas
# ============================================================================


class KnowledgeSourceCreateRequest(BaseModel):
    """Request to add a new knowledge source."""

    profile_id: UUID
    source_type: SourceType
    source_url: str | None = None
    document_name: str | None = None
    content_hash: str | None = None
    raw_storage_path: str | None = None
    authority_weight: AuthorityWeight = AuthorityWeight.MEDIUM
    page_type: PageType | None = None
    extra_metadata: dict[str, Any] = Field(default_factory=dict)


class KnowledgeSourceResponse(BaseModel):
    """Knowledge source item in API responses."""

    id: UUID
    tenant_id: str
    profile_id: UUID
    source_type: SourceType
    source_url: str | None = None
    document_name: str | None = None
    content_hash: str | None = None
    raw_storage_path: str | None = None
    crawl_status: CrawlStatus
    authority_weight: AuthorityWeight
    page_type: PageType | None = None
    extra_metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Value Extraction Record Schemas
# ============================================================================


class ExtractedPayloadSchema(BaseModel):
    """Typed extraction payload."""

    products: list[dict[str, Any]] = Field(default_factory=list)
    capabilities: list[dict[str, Any]] = Field(default_factory=list)
    personas: list[dict[str, Any]] = Field(default_factory=list)
    industries: list[str] = Field(default_factory=list)
    use_cases: list[dict[str, Any]] = Field(default_factory=list)
    value_drivers: list[dict[str, Any]] = Field(default_factory=list)
    metrics: list[dict[str, Any]] = Field(default_factory=list)
    proof_points: list[dict[str, Any]] = Field(default_factory=list)


class ValueExtractionRecordResponse(BaseModel):
    """Extraction record in API responses."""

    id: UUID
    source_id: UUID
    tenant_id: str
    profile_id: UUID
    page_type: PageType | None = None
    extracted: dict[str, Any]
    confidence: float | None = Field(None, ge=0.0, le=1.0)
    requires_review: bool
    review_status: ReviewStatus
    reviewed_by: UUID | None = None
    reviewed_at: datetime | None = None
    extraction_version: str | None = None
    llm_model: str | None = None
    trace_span_id: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ValueExtractionReviewRequest(BaseModel):
    """Request to review an extraction record."""

    action: ReviewStatus = Field(..., description="accepted | rejected | modified")
    user_edits: dict[str, Any] | None = Field(
        None, description="Modified extracted fields when action=modified"
    )
    notes: str | None = None


# ============================================================================
# ICP Profile Schemas
# ============================================================================


class ICPBuyerPersonaSchema(BaseModel):
    """Buyer persona in ICP."""

    title: str
    department: str | None = None
    goals: list[str] = Field(default_factory=list)
    pain_points: list[str] = Field(default_factory=list)


class ICPProfileCreateRequest(BaseModel):
    """Request to create an ICP profile."""

    profile_id: UUID
    industries: list[str] = Field(default_factory=list)
    company_size: list[str] = Field(default_factory=list)
    buyer_personas: list[dict[str, Any]] = Field(default_factory=list)
    user_personas: list[dict[str, Any]] = Field(default_factory=list)
    pain_points: list[str] = Field(default_factory=list)
    trigger_events: list[str] = Field(default_factory=list)
    qualification_criteria: list[str] = Field(default_factory=list)
    disqualification_criteria: list[str] = Field(default_factory=list)
    competitive_context: dict[str, Any] | None = None
    buying_committee_structure: dict[str, Any] | None = None
    typical_sales_motion: str | None = None
    confidence: float | None = Field(None, ge=0.0, le=1.0)
    source_type: ICPSourceType = ICPSourceType.MANUAL


class ICPProfileUpdateRequest(BaseModel):
    """Request to update an ICP profile."""

    industries: list[str] | None = None
    company_size: list[str] | None = None
    buyer_personas: list[dict[str, Any]] | None = None
    user_personas: list[dict[str, Any]] | None = None
    pain_points: list[str] | None = None
    trigger_events: list[str] | None = None
    qualification_criteria: list[str] | None = None
    disqualification_criteria: list[str] | None = None
    competitive_context: dict[str, Any] | None = None
    buying_committee_structure: dict[str, Any] | None = None
    typical_sales_motion: str | None = None
    confidence: float | None = Field(None, ge=0.0, le=1.0)
    source_type: ICPSourceType | None = None


class ICPProfileResponse(BaseModel):
    """ICP profile in API responses."""

    id: UUID
    tenant_id: str
    profile_id: UUID
    industries: list[str]
    company_size: list[str]
    buyer_personas: list[dict[str, Any]]
    user_personas: list[dict[str, Any]]
    pain_points: list[str]
    trigger_events: list[str]
    qualification_criteria: list[str]
    disqualification_criteria: list[str]
    competitive_context: dict[str, Any] | None = None
    buying_committee_structure: dict[str, Any] | None = None
    typical_sales_motion: str | None = None
    confidence: float | None = Field(None, ge=0.0, le=1.0)
    source_type: ICPSourceType
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Company Knowledge Profile Schemas
# ============================================================================


class CompanyKnowledgeProfileCreateRequest(BaseModel):
    """Request to create a draft company knowledge profile."""

    model_config = ConfigDict(extra="forbid")

    company_name: str = Field(..., min_length=1, max_length=255)
    website: str | None = Field(None, max_length=255)

    @field_validator("website")
    @classmethod
    def _website_must_be_http_url(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip().lower()
        if not (normalized.startswith("http://") or normalized.startswith("https://")):
            raise ValueError("website must use http or https")
        return value


class CompanyKnowledgeProfileUpdateRequest(BaseModel):
    """Request to update profile sections."""

    company_name: str | None = Field(None, min_length=1, max_length=255)
    website: str | None = Field(None, max_length=255)
    identity: dict[str, Any] | None = None
    product_catalog: dict[str, Any] | None = None
    target_customer: dict[str, Any] | None = None
    personas: dict[str, Any] | None = None
    use_cases: dict[str, Any] | None = None
    value_drivers: dict[str, Any] | None = None
    proof_points: dict[str, Any] | None = None
    trust_commercial: dict[str, Any] | None = None
    review_status: dict[str, Any] | None = None


class CompanyKnowledgeProfileResponse(BaseModel):
    """Full company knowledge profile response."""

    id: UUID
    tenant_id: str
    company_name: str
    website: str | None = None
    status: ProfileStatus
    version: int
    confidence_score: float | None = Field(None, ge=0.0, le=1.0)
    identity: dict[str, Any] | None = None
    product_catalog: dict[str, Any] | None = None
    target_customer: dict[str, Any] | None = None
    personas: dict[str, Any] | None = None
    use_cases: dict[str, Any] | None = None
    value_drivers: dict[str, Any] | None = None
    proof_points: dict[str, Any] | None = None
    trust_commercial: dict[str, Any] | None = None
    active_source_ids: list[str]
    review_status: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime
    approved_at: datetime | None = None
    approved_by: UUID | None = None

    model_config = ConfigDict(from_attributes=True)


class CompanyKnowledgeProfileListItemResponse(BaseModel):
    """Lightweight profile item for list responses."""

    id: UUID
    tenant_id: str
    company_name: str
    website: str | None = None
    status: ProfileStatus
    version: int
    confidence_score: float | None = Field(None, ge=0.0, le=1.0)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProfileApproveRequest(BaseModel):
    """Request to approve a draft profile."""

    approved_by: UUID


# ============================================================================
# Onboarding Status Schema
# ============================================================================


class OnboardingStatusResponse(BaseModel):
    """Aggregated onboarding progress for a tenant."""

    tenant_id: str
    profile_id: UUID | None = None
    profile_status: ProfileStatus | None = None
    company_name: str | None = None
    website: str | None = None
    sources_count: int
    extractions_count: int
    extractions_pending_review: int
    extractions_accepted: int
    extractions_rejected: int
    average_confidence: float | None = Field(None, ge=0.0, le=1.0)
    icp_present: bool
    has_approved_profile: bool
    next_step: str = Field(
        ..., description="Human-readable next action for the onboarding flow"
    )

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# List / Paginated Responses
# ============================================================================


class PaginatedResponse(BaseModel):
    """Base paginated response."""

    total: int
    page: int
    page_size: int
    has_more: bool


class ValueExtractionRecordListResponse(PaginatedResponse):
    """Paginated extraction records."""

    items: list[ValueExtractionRecordResponse]


class KnowledgeSourceListResponse(PaginatedResponse):
    """Paginated knowledge sources."""

    items: list[KnowledgeSourceResponse]
