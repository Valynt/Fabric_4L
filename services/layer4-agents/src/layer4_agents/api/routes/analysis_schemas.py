from __future__ import annotations

import os
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from value_fabric.shared.models.typed_dict import TypedDictModel

from ...test_support.seed_runtime_config import (
    SEED_APPROVED_CASE_ALIASES,
    SEED_APPROVED_CASE_ID,
    SEED_DRAFT_CASE_ID,
    SEED_SERVICE_ACCOUNT_ID,
    SEED_TENANT_NAME,
    SEED_TENANT_SLUG,
)

VALIDATION_ACCOUNT_MAPPINGS = [
    {
        "provider_record_id": "acct-meridian-001",
        "backend_uuid": os.environ.get("E2E_MERIDIAN_ACCOUNT_UUID", "00000000-0000-4000-e2e0-000000000101"),
        "label": "Meridian Automotive",
    }
]


class export_business_caseResult(TypedDictModel):
    blocked: bool
    case_id: Any
    document_url: Any
    download_ready: bool
    export_id: Any
    format: Any
    manifest: dict[str, Any]
    manifest_url: Any | None = None
    remediation_items: Any
    truth_references: Any
    url_expires_at: Any | None = None


class generate_workspace_intelligenceResult(TypedDictModel):
    account_id: Any
    case_id: Any
    generated: bool
    stats: dict[str, Any]


class ROIAnalysisRequest(BaseModel):
    """Quick ROI analysis request."""

    prospect_id: str | None = Field(None, description="Prospect identifier")
    value_driver_ids: list[str] = Field(default_factory=list, description="Value drivers to calculate")
    prospect_data: dict[str, float] = Field(
        default_factory=dict, description="Prospect-specific variables"
    )
    industry_vertical: str | None = None
    company_size: str | None = None

    # Legacy/release-smoke compatibility fields. Canonical clients should continue
    # to send prospect_id, value_driver_ids, and prospect_data.
    account_id: str | None = None
    variables: dict[str, float] = Field(default_factory=dict)
    formula_id: str | None = None


class ROIAnalysisResponse(BaseModel):
    """ROI analysis response."""

    prospect_id: str
    aggregated_roi: dict[str, Any]
    detailed_results: list[dict[str, Any]]
    benchmark_comparison: dict[str, Any] | None = None


class WhitespaceAnalysisRequest(BaseModel):
    """Whitespace analysis request."""

    prospect_id: str = Field(..., description="Prospect identifier")
    prospect_needs: str = Field(..., min_length=10, description="Description of prospect needs")
    analysis_depth: str = Field(
        default="standard", description="Analysis depth (quick, standard, deep)"
    )


class WhitespaceAnalysisResponse(BaseModel):
    """Whitespace analysis response."""

    prospect_id: str
    extracted_needs: list[str]
    gap_analysis: list[dict[str, Any]]
    opportunity_score: float
    recommendations: list[str]


class BusinessCaseRequest(BaseModel):
    """Business case generation request."""

    account_id: UUID = Field(..., description="Account UUID identifier")
    opportunity_id: str | None = None
    sections: list[str] = Field(
        default_factory=lambda: [
            "executive_summary",
            "roi_analysis",
            "implementation",
            "next_steps",
        ]
    )
    output_format: str = Field(default="pdf", description="Output format (pdf, docx, html)")
    custom_inputs: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional custom inputs, including truth_requirements and organization_id",
    )


class RegenerateBusinessCaseRequest(BusinessCaseRequest):
    """Regenerate request with lineage to an existing case."""

    previous_case_id: str = Field(..., description="Existing case id being regenerated")


class BusinessCaseResponse(BaseModel):
    """Business case generation response."""

    case_id: str
    title: str = "Business Case"
    summary: str = ""
    total_value: float = 0.0
    implementation_cost: float = 0.0
    roi_ratio: float = 0.0
    payback_months: int = 0
    confidence_score: float = 0.0
    recommendations: list[str] = Field(default_factory=list)
    status: str = "unknown"
    created_at: str | None = None
    document_url: str | None = None
    page_count: int = 0
    file_size_bytes: int = 0
    truth_references: list[dict[str, Any]] = Field(default_factory=list)
    remediation_items: list[dict[str, Any]] = Field(default_factory=list)
    sdes: dict[str, Any] = Field(default_factory=dict)
    case_metadata: dict[str, Any] = Field(default_factory=dict)
    revision_history: list[dict[str, Any]] = Field(default_factory=list)
    diff_summary: dict[str, Any] = Field(default_factory=dict)


class BusinessCaseLifecycleSeedRequest(BaseModel):
    """Non-production deterministic lifecycle seed payload for backend E2E validation."""

    account_id: UUID
    draft_case_id: str = SEED_DRAFT_CASE_ID
    approved_case_id: str = SEED_APPROVED_CASE_ID
    approved_case_aliases: list[str] = Field(default_factory=lambda: SEED_APPROVED_CASE_ALIASES.copy())


class ValidationSeededApiKey(BaseModel):
    """Pre-hashed API key metadata for deterministic non-production validation."""

    model_config = ConfigDict(extra="forbid")

    key_id: str = Field(..., min_length=3, max_length=64)
    name: str = Field(default="E2E backend-integrated validation service key", min_length=1, max_length=100)
    key_hash: str = Field(..., pattern=r"^[a-f0-9]{64}$")
    prefix: str = Field(..., min_length=4, max_length=16)
    role: str = Field(default="system", min_length=1, max_length=30)
    permissions: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ValidationAuthContextSeedRequest(BaseModel):
    """Non-production deterministic auth-context seed payload.

    The payload intentionally accepts only non-secret metadata and optional
    pre-hashed API key material. Raw secrets are rejected by ``extra=forbid``.
    """

    model_config = ConfigDict(extra="forbid")

    tenant_id: UUID | None = None
    tenant_slug: str = Field(default=SEED_TENANT_SLUG, min_length=1, max_length=63)
    tenant_name: str = Field(default=SEED_TENANT_NAME, min_length=1, max_length=200)
    service_account_id: str = Field(default=SEED_SERVICE_ACCOUNT_ID, min_length=1, max_length=128)
    api_key: ValidationSeededApiKey | None = None
    account_mappings: list[dict[str, str]] = Field(default_factory=lambda: VALIDATION_ACCOUNT_MAPPINGS.copy())


class ValidationSessionRequest(BaseModel):
    """Non-production browser session payload for backend-integrated Playwright validation."""

    user_id: str = Field(default="e2e-admin-user", min_length=1)
    email: str = Field(default="e2e@valuefabric.test", min_length=3)
    role: str = Field(default="admin", min_length=1)
    tenant_slug: str = Field(default="e2e-test", min_length=1)
    expires_in_seconds: int = Field(default=3600, ge=60, le=86400)


class CaseListItem(BaseModel):
    """Case list response item."""
    case_id: str
    account_id: str | None = None
    title: str | None = None
    status: str = "unknown"
    created_at: str | None = None
    updated_at: str | None = None


class CaseListResponse(BaseModel):
    """List of cases for an account."""
    items: list[CaseListItem]
    total: int


class CreateCaseRequest(BaseModel):
    """Create a new case for an account."""
    account_id: str = Field(..., description="Account identifier")
    title: str | None = Field(None, description="Case title")
    case_id: str | None = Field(
        None,
        description="Optional deterministic case id. Generated if omitted.",
    )


class CreateCaseResponse(BaseModel):
    """Created case response."""
    case_id: str
    account_id: str
    title: str | None = None
    status: str = "created"
    created_at: str


class SaveScenarioRequest(BaseModel):
    """Persist a business-case what-if scenario."""

    name: str = Field(..., min_length=1, max_length=120)
    adjustments: list[dict[str, Any]] = Field(default_factory=list, max_length=100)


class SavedScenarioSummary(BaseModel):
    """Safe scenario metadata returned to the frontend."""

    id: str
    name: str
    created_at: str


class SavedScenarioDetail(SavedScenarioSummary):
    """Full server-side scenario payload."""

    adjustments: list[dict[str, Any]]


class WorkspaceEvidenceItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    title: str
    type: str = "evidence"
    source: str = "Unknown"
    match_score: int = Field(default=0, alias="matchScore")
    verification: str = "unverified"
    linked_signals: list[str] = Field(default_factory=list, alias="linkedSignals")
    excerpt: str = ""
    decision_status: str | None = None
    attached_driver_id: str | None = None
    provenance_id: str | None = None
    confidence: float | None = None
    decision_note: str | None = None


class WorkspaceEvidenceResponse(BaseModel):
    evidence: list[WorkspaceEvidenceItem] = Field(default_factory=list)


