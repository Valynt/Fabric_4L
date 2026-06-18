"""Canonical claim models for Fabric_4L v3.0.

These models represent evidence-backed value claims that are extracted from
sources, validated against signals, and projected into FabricFoundSummary views.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .value_signal import ProvenanceExtractor, ValueSignalEvidence


class ClaimStatus(str, Enum):
    """Lifecycle status of a value claim."""

    EXTRACTED = "extracted"
    SUPPORTED = "supported"
    VALIDATED = "validated"
    NEEDS_REVIEW = "needs_review"
    NEEDS_OVERRIDE = "needs_override"
    CONTESTED = "contested"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class EvidenceStrength(str, Enum):
    """Qualitative evidence-strength band."""

    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"
    CONCLUSIVE = "conclusive"


class ClaimProvenance(BaseModel):
    """Provenance of how a claim was derived."""

    model_config = ConfigDict(from_attributes=True)

    extractor: ProvenanceExtractor
    method: str = Field(..., description="Extraction method (e.g. llm_extraction, rule_based, manual)")
    model: Optional[str] = Field(None, description="LLM model identifier if AI-extracted")
    run_id: Optional[str] = Field(None, description="Ingestion run or workflow ID")
    source_refs: list[str] = Field(default_factory=list)
    extracted_at: datetime
    normalizer_version: Optional[str] = None
    extractor_version: Optional[str] = None


class Claim(BaseModel):
    """Canonical evidence-backed value claim.

    A claim is a differentiated, uncertain statement about business value that
    must be traceable to one or more evidence chunks and supporting signals.
    """

    model_config = ConfigDict(from_attributes=True)

    # Identity
    id: UUID
    tenant_id: UUID = Field(..., description="Owning tenant — always from authenticated context")
    account_id: UUID
    opportunity_id: Optional[UUID] = None
    value_driver_id: Optional[UUID] = None

    # Claim content
    claim_text: str = Field(..., min_length=1, max_length=4000)
    category: Optional[str] = Field(None, description="Value category, e.g. revenue_uplift, cost_savings, risk_reduction")

    # Evidence and provenance
    evidence_chunk_ids: list[UUID] = Field(default_factory=list)
    evidence: list[ValueSignalEvidence] = Field(default_factory=list)
    provenance: ClaimProvenance
    source_refs: list[str] = Field(default_factory=list)

    # Scoring
    confidence: float = Field(..., ge=0.0, le=1.0)
    trust_score: float = Field(..., ge=0.0, le=1.0)
    evidence_strength: Optional[EvidenceStrength] = None
    evidence_strength_score: Optional[float] = Field(None, ge=0.0, le=1.0)

    # Lifecycle
    status: ClaimStatus = ClaimStatus.EXTRACTED
    validation_notes: Optional[str] = None
    reviewer_id: Optional[UUID] = None
    reviewed_at: Optional[datetime] = None

    # Parameter bindings
    parameter_ids: Optional[list[UUID]] = Field(default_factory=list)
    override_ids: Optional[list[UUID]] = Field(default_factory=list)

    # Lineage
    superseded_by_claim_id: Optional[UUID] = None
    supersedes_claim_id: Optional[UUID] = None
    related_claim_ids: Optional[list[UUID]] = Field(default_factory=list)

    # Timestamps
    created_at: datetime
    updated_at: datetime
    expires_at: Optional[datetime] = None

    @field_validator("evidence_chunk_ids")
    @classmethod
    def _evidence_chunk_ids_non_empty(cls, value: list[UUID]) -> list[UUID]:
        """v3.0 invariant: a claim must link to at least one evidence chunk."""
        if not value:
            raise ValueError("evidence_chunk_ids must contain at least one evidence chunk")
        return value


class ClaimOverride(BaseModel):
    """User override applied to a claim or its parameter inputs.

    Overrides are immutable audit records. Applying an override creates a new
    claim revision rather than mutating the original claim.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    account_id: UUID
    claim_id: Optional[UUID] = None
    parameter_id: Optional[UUID] = None
    overridden_by: UUID
    overridden_at: datetime
    reason: Optional[str] = None
    previous_value: Optional[dict] = None
    new_value: Optional[dict] = None
    source_refs: list[str] = Field(default_factory=list)


class ClaimCreate(BaseModel):
    """Request body for creating a claim.

    tenant_id is NOT accepted here — it is always set from authenticated context.
    """

    model_config = ConfigDict(from_attributes=True)

    account_id: UUID
    opportunity_id: Optional[UUID] = None
    value_driver_id: Optional[UUID] = None
    claim_text: str = Field(..., min_length=1, max_length=4000)
    category: Optional[str] = None
    evidence_chunk_ids: list[UUID] = Field(default_factory=list)
    evidence: list[ValueSignalEvidence] = Field(default_factory=list)
    provenance: ClaimProvenance
    source_refs: list[str] = Field(default_factory=list)
    confidence: float = Field(..., ge=0.0, le=1.0)
    trust_score: float = Field(0.0, ge=0.0, le=1.0)
    parameter_ids: Optional[list[UUID]] = Field(default_factory=list)

    @field_validator("evidence_chunk_ids")
    @classmethod
    def _evidence_chunk_ids_non_empty(cls, value: list[UUID]) -> list[UUID]:
        if not value:
            raise ValueError("evidence_chunk_ids must contain at least one evidence chunk")
        return value


class ClaimUpdate(BaseModel):
    """Partial update for a claim (PATCH semantics)."""

    model_config = ConfigDict(from_attributes=True)

    status: Optional[ClaimStatus] = None
    validation_notes: Optional[str] = None
    reviewer_id: Optional[UUID] = None
    reviewed_at: Optional[datetime] = None
    evidence_strength: Optional[EvidenceStrength] = None
    evidence_strength_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    expires_at: Optional[datetime] = None
    related_claim_ids: Optional[list[UUID]] = None
