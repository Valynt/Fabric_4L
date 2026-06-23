"""Canonical ValueSignal domain model for the L2.5 Signal Refinery.

This module is the single source of truth for the ValueSignal object model.
All layers (L2.5, L3, L4) and the frontend contract derive from this definition.

Contract: contracts/value-signal.json
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class ValueSignalType(str, Enum):
    PAIN = "pain"
    OPPORTUNITY = "opportunity"
    RISK = "risk"
    EXPANSION = "expansion"
    RENEWAL = "renewal"
    COST_SAVING = "cost_saving"
    REVENUE_UPLIFT = "revenue_uplift"
    EFFICIENCY = "efficiency"
    COMPLIANCE = "compliance"
    STRATEGIC_PRIORITY = "strategic_priority"


class ValueSignalLifecycleState(str, Enum):
    DRAFT = "draft"
    EXTRACTED = "extracted"
    VALIDATED = "validated"
    REJECTED = "rejected"
    PROMOTED = "promoted"
    EXPIRED = "expired"
    SUPERSEDED = "superseded"


class SignalImpactArea(str, Enum):
    REVENUE = "revenue"
    COST = "cost"
    RISK = "risk"
    STRATEGIC = "strategic"


class ProvenanceExtractor(str, Enum):
    HUMAN = "human"
    AI = "ai"
    SYSTEM = "system"


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------


class ValueSignalEvidence(BaseModel):
    """A single piece of evidence supporting a ValueSignal."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_ref: str = Field(..., description="Reference to source document or ingestion record")
    excerpt: Optional[str] = Field(None, max_length=2000)
    url: Optional[str] = None
    document_id: Optional[str] = None
    confidence: float = Field(..., ge=0.0, le=1.0)
    relevance_score: Optional[float] = Field(None, ge=0.0, le=1.0)


class ValueSignalProvenance(BaseModel):
    """Provenance metadata describing how a signal was extracted."""

    model_config = ConfigDict(from_attributes=True)

    extractor: ProvenanceExtractor
    method: str = Field(..., description="Extraction method (e.g. llm_extraction, rule_based, manual)")
    model: Optional[str] = Field(None, description="LLM model identifier if AI-extracted")
    run_id: Optional[str] = Field(None, description="Extraction run or workflow ID")
    source_system: Optional[str] = Field(None, description="Originating system")
    extracted_at: datetime
    # v3.0: required provenance lineage
    normalizer_version: Optional[str] = None
    extractor_version: Optional[str] = None
    provenance_class: Optional[str] = Field(None, description="Provenance class: primary, secondary, derived, synthetic")


# ---------------------------------------------------------------------------
# Core ValueSignal model
# ---------------------------------------------------------------------------


class ValueSignal(BaseModel):
    """Canonical ValueSignal domain object.

    Represents a trusted, evidence-backed commercial intelligence signal
    produced by the L2.5 Signal Refinery. This is the authoritative model
    for all layers and the frontend.

    Required fields are the MVP-required set. Optional fields are enrichments
    added during refinement, validation, or downstream processing.
    """

    model_config = ConfigDict(from_attributes=True)

    # Identity
    id: UUID
    tenant_id: UUID = Field(..., description="Owning tenant — always from authenticated context")
    account_id: UUID

    # Classification
    type: ValueSignalType
    content: str = Field(..., min_length=1, max_length=4000)

    # Scoring
    confidence: float = Field(..., ge=0.0, le=1.0, description="Extraction confidence score")
    trust_score: float = Field(..., ge=0.0, le=1.0, description="Composite trust score")

    # Lifecycle
    lifecycle_state: ValueSignalLifecycleState = ValueSignalLifecycleState.DRAFT

    # Evidence and provenance
    evidence: list[ValueSignalEvidence] = Field(default_factory=list)
    evidence_chunk_ids: list[UUID] = Field(default_factory=list)
    provenance: ValueSignalProvenance
    source_refs: list[str] = Field(default_factory=list)

    # Timestamps
    created_at: datetime
    updated_at: datetime

    @field_validator("evidence_chunk_ids")
    @classmethod
    def _evidence_chunk_ids_non_empty(cls, value: list[UUID]) -> list[UUID]:
        """v3.0 invariant: a signal must link to at least one evidence chunk."""
        if not value:
            raise ValueError("evidence_chunk_ids must contain at least one evidence chunk")
        return value

    # Optional enrichments
    opportunity_id: Optional[UUID] = None
    value_driver_id: Optional[UUID] = None
    stakeholder_id: Optional[UUID] = None
    persona: Optional[str] = None
    industry: Optional[str] = None
    impact_area: Optional[SignalImpactArea] = None
    estimated_value: Optional[float] = Field(None, ge=0)
    currency: Optional[str] = Field(None, pattern=r"^[A-Z]{3}$")
    time_horizon: Optional[str] = None
    validation_notes: Optional[str] = None
    reviewer_id: Optional[UUID] = None
    expires_at: Optional[datetime] = None
    supersedes_signal_id: Optional[UUID] = None
    related_signal_ids: Optional[list[UUID]] = None


# ---------------------------------------------------------------------------
# API request/response models
# ---------------------------------------------------------------------------


class ValueSignalCreate(BaseModel):
    """Request body for creating a new ValueSignal.

    tenant_id is NOT accepted here — it is always set from authenticated context.
    """

    model_config = ConfigDict(from_attributes=True)

    account_id: UUID
    type: ValueSignalType
    content: str = Field(..., min_length=1, max_length=4000)
    confidence: float = Field(..., ge=0.0, le=1.0)
    trust_score: float = Field(0.0, ge=0.0, le=1.0)
    lifecycle_state: ValueSignalLifecycleState = ValueSignalLifecycleState.DRAFT
    evidence: list[ValueSignalEvidence] = Field(default_factory=list)
    evidence_chunk_ids: list[UUID] = Field(default_factory=list)
    provenance: ValueSignalProvenance
    source_refs: list[str] = Field(default_factory=list)

    @field_validator("evidence_chunk_ids")
    @classmethod
    def _evidence_chunk_ids_non_empty(cls, value: list[UUID]) -> list[UUID]:
        """v3.0 invariant: a signal must link to at least one evidence chunk."""
        if not value:
            raise ValueError("evidence_chunk_ids must contain at least one evidence chunk")
        return value

    # Optional enrichments
    opportunity_id: Optional[UUID] = None
    value_driver_id: Optional[UUID] = None
    stakeholder_id: Optional[UUID] = None
    persona: Optional[str] = None
    industry: Optional[str] = None
    impact_area: Optional[SignalImpactArea] = None
    estimated_value: Optional[float] = Field(None, ge=0)
    currency: Optional[str] = Field(None, pattern=r"^[A-Z]{3}$")
    time_horizon: Optional[str] = None


class ValueSignalUpdate(BaseModel):
    """Partial update for a ValueSignal (PATCH semantics)."""

    model_config = ConfigDict(from_attributes=True)

    lifecycle_state: Optional[ValueSignalLifecycleState] = None
    validation_notes: Optional[str] = None
    reviewer_id: Optional[UUID] = None
    impact_area: Optional[SignalImpactArea] = None
    estimated_value: Optional[float] = Field(None, ge=0)
    currency: Optional[str] = Field(None, pattern=r"^[A-Z]{3}$")
    time_horizon: Optional[str] = None
    value_driver_id: Optional[UUID] = None
    expires_at: Optional[datetime] = None
    supersedes_signal_id: Optional[UUID] = None
    related_signal_ids: Optional[list[UUID]] = None


class SignalReviewRequest(BaseModel):
    """Request body for human review of a signal."""

    status: ValueSignalLifecycleState = Field(
        ...,
        description="Must be 'validated' or 'rejected'",
    )
    notes: Optional[str] = None


class SignalPromoteRequest(BaseModel):
    """Request body for promoting a signal to a hypothesis."""

    value_path_category: str = Field(
        ...,
        description="Value path: revenue_uplift, cost_savings, risk_reduction, blended",
    )
    value_driver_id: Optional[UUID] = None


class RawSignalInput(BaseModel):
    """A single raw signal payload from L2 extraction, passed to the /refine endpoint.

    Callers should supply the actual extracted content and provenance rather than
    letting the refinery synthesise placeholder values.
    """

    account_id: UUID
    type: str = Field(default="pain", description="Raw signal type from L2 (mapped to ValueSignalType by refinery)")
    content: str = Field(..., min_length=1, max_length=4000)
    confidence: float = Field(..., ge=0.0, le=1.0)
    evidence: list[dict] = Field(default_factory=list)
    provenance: dict = Field(default_factory=dict)
    source_refs: list[str] = Field(default_factory=list)


class SignalRefineRequest(BaseModel):
    """Request body for triggering L2.5 refinement on L2 extraction output.

    Prefer ``raw_signals`` to pass actual L2 extraction payloads.
    ``source_refs`` alone is accepted for backward compatibility but produces
    signals with synthetic content and should not be used in production.
    """

    account_id: UUID
    raw_signals: Optional[list[RawSignalInput]] = Field(
        default=None,
        description="Actual L2 extraction payloads to refine. Preferred over source_refs.",
    )
    source_refs: list[str] = Field(default_factory=list)
    extraction_run_id: Optional[str] = None


class ValueSignalListResponse(BaseModel):
    """Paginated list response for ValueSignals."""

    model_config = ConfigDict(from_attributes=True)

    items: list[ValueSignal]
    total: int
    limit: int
    offset: int
