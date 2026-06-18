"""Canonical FabricFoundSummary model for Fabric_4L v3.0.

A FabricFoundSummary is a read-only, deterministic projection of validated and
supported claims. It is versioned and never mutates historical revisions.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SummarySection(str, Enum):
    """Standard sections in a FabricFoundSummary."""

    EXECUTIVE_SUMMARY = "executive_summary"
    FACTS = "facts"
    RECOMMENDATIONS = "recommendations"
    STAKEHOLDERS = "stakeholders"
    VALUE_DRIVERS = "value_drivers"
    METRICS = "metrics"
    BENCHMARKS = "benchmarks"
    RISKS = "risks"
    BUSINESS_CASE = "business_case"


class SummaryItemStatus(str, Enum):
    """Status band applied to a summary item during projection."""

    FACT = "fact"
    SUPPORTED_FACT = "supported_fact"
    WARNING = "warning"
    MISSING_INPUT = "missing_input"
    REVIEW_ONLY = "review_only"
    HIDDEN = "hidden"


class SummaryItem(BaseModel):
    """A single item within a FabricFoundSummary section."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    section: SummarySection
    title: str = Field(..., min_length=1, max_length=500)
    body: str = Field(..., min_length=1)
    status: SummaryItemStatus
    claim_ids: list[UUID] = Field(default_factory=list)
    evidence_chunk_ids: list[UUID] = Field(default_factory=list)
    source_refs: list[str] = Field(default_factory=list)
    confidence: float = Field(..., ge=0.0, le=1.0)
    trust_score: float = Field(..., ge=0.0, le=1.0)
    parameter_ids: Optional[list[UUID]] = Field(default_factory=list)


class FabricFoundSummary(BaseModel):
    """Deterministic, read-only projection of claims for an account/opportunity.

    Every field in a summary must be traceable to a claim and its evidence.
    Revisions are immutable; applying an override or receiving new evidence
    produces a new revision rather than editing the current one.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID = Field(..., description="Owning tenant — always from authenticated context")
    account_id: UUID
    opportunity_id: Optional[UUID] = None
    revision: int = Field(..., ge=1)
    title: str = Field(..., min_length=1, max_length=500)
    items: list[SummaryItem] = Field(default_factory=list)
    claim_ids: list[UUID] = Field(default_factory=list)
    overridden_parameter_ids: Optional[list[UUID]] = Field(default_factory=list)
    created_at: datetime
    superseded_by_summary_id: Optional[UUID] = None


class FabricFoundSummaryProjectionRequest(BaseModel):
    """Request body for projecting a summary from claims."""

    model_config = ConfigDict(from_attributes=True)

    account_id: UUID
    opportunity_id: Optional[UUID] = None
    title: Optional[str] = None
    claim_ids: Optional[list[UUID]] = Field(default_factory=list)
    overridden_parameter_ids: Optional[list[UUID]] = Field(default_factory=list)
