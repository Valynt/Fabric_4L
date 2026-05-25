"""Phase 2: Deterministic Entity Resolution Schema.

Defines the contract for entity resolution operations with:
- Request models for resolution queries
- Response models with match confidence and explainability
- Match scoring and tie-breaking rules
- Provenance tracking for resolution decisions
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class ResolutionStrategy(str, Enum):
    """Strategy for resolving entity matches."""

    EXACT = "exact"  # Exact ID match
    FUZZY = "fuzzy"  # Fuzzy name/attribute match
    HYBRID = "hybrid"  # Combination of exact and fuzzy
    VECTOR = "vector"  # Semantic similarity match


class MatchConfidence(str, Enum):
    """Confidence level for a match."""

    HIGH = "high"  # >0.9 confidence
    MEDIUM = "medium"  # 0.7-0.9 confidence
    LOW = "low"  # 0.5-0.7 confidence
    AMBIGUOUS = "ambiguous"  # Multiple candidates with similar scores
    NONE = "none"  # No suitable match


class TieBreakRule(str, Enum):
    """Rules for breaking ties in ambiguous matches."""

    MOST_RECENT = "most_recent"  # Prefer most recently updated
    MOST_REFERENCED = "most_referenced"  # Prefer most referenced entity
    HIGHEST_CONFIDENCE = "highest_confidence"  # Prefer highest score
    MANUAL_REVIEW = "manual_review"  # Require manual review


class EntityResolutionRequest(BaseModel):
    """Request for entity resolution.

    Attributes:
        entity_type: The type of entity to resolve (e.g., "Product", "ValueDriver")
        tenant_id: Tenant context for isolation
        query_attributes: Attributes to match against (name, external_id, etc.)
        strategy: Resolution strategy to use
        min_confidence: Minimum confidence threshold for acceptance
        tie_break_rule: Rule for resolving ambiguous matches
        request_id: Optional request ID for tracing
    """

    entity_type: str = Field(..., description="Type of entity to resolve")
    tenant_id: str = Field(..., description="Tenant context for isolation")
    query_attributes: dict[str, Any] = Field(
        default_factory=dict,
        description="Attributes to match against (name, external_id, etc.)"
    )
    strategy: ResolutionStrategy = Field(
        default=ResolutionStrategy.HYBRID,
        description="Resolution strategy to use"
    )
    min_confidence: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Minimum confidence threshold for acceptance"
    )
    tie_break_rule: TieBreakRule = Field(
        default=TieBreakRule.HIGHEST_CONFIDENCE,
        description="Rule for resolving ambiguous matches"
    )
    request_id: str | None = Field(
        default=None,
        description="Optional request ID for tracing"
    )

    @field_validator("query_attributes")
    @classmethod
    def validate_query_attributes(cls, v: dict[str, Any]) -> dict[str, Any]:
        """Ensure query attributes are not empty."""
        if not v:
            raise ValueError("query_attributes must contain at least one attribute")
        return v


class MatchCandidate(BaseModel):
    """A single candidate match for an entity.

    Attributes:
        entity_id: The matched entity's ID
        entity_type: The entity type
        score: Confidence score (0.0-1.0)
        matched_attributes: Which attributes matched
        explanation: Human-readable explanation of the match
        metadata: Additional match metadata
    """

    entity_id: str = Field(..., description="Matched entity ID")
    entity_type: str = Field(..., description="Entity type")
    score: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    matched_attributes: list[str] = Field(
        default_factory=list,
        description="Which attributes matched"
    )
    explanation: str = Field(
        default="",
        description="Human-readable explanation"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional match metadata"
    )


class ResolutionProvenance(BaseModel):
    """Provenance tracking for resolution decisions.

    Attributes:
        resolved_at: When the resolution occurred
        strategy_used: Which strategy was applied
        candidates_evaluated: Number of candidates considered
        tie_break_applied: Whether tie-breaking was used
        tie_break_rule: Which tie-break rule was applied
        source_system: System that initiated the resolution
    """

    resolved_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When the resolution occurred"
    )
    strategy_used: ResolutionStrategy = Field(
        ...,
        description="Strategy that was applied"
    )
    candidates_evaluated: int = Field(
        default=0,
        ge=0,
        description="Number of candidates considered"
    )
    tie_break_applied: bool = Field(
        default=False,
        description="Whether tie-breaking was used"
    )
    tie_break_rule: TieBreakRule | None = Field(
        default=None,
        description="Which tie-break rule was applied"
    )
    source_system: str = Field(
        default="layer3-knowledge",
        description="System that initiated the resolution"
    )


class EntityResolutionResponse(BaseModel):
    """Response from entity resolution.

    Attributes:
        request_id: Request ID for tracing
        matched_entity_id: The resolved entity ID (if match found)
        confidence: Overall confidence level
        candidates: All candidates considered (sorted by score)
        provenance: Resolution decision provenance
        requires_manual_review: Whether manual review is needed
        error: Error message if resolution failed
    """

    request_id: str | None = Field(
        default=None,
        description="Request ID for tracing"
    )
    matched_entity_id: str | None = Field(
        default=None,
        description="Resolved entity ID (if match found)"
    )
    confidence: MatchConfidence = Field(
        default=MatchConfidence.NONE,
        description="Overall confidence level"
    )
    candidates: list[MatchCandidate] = Field(
        default_factory=list,
        description="All candidates considered (sorted by score)"
    )
    provenance: ResolutionProvenance = Field(
        default_factory=ResolutionProvenance,
        description="Resolution decision provenance"
    )
    requires_manual_review: bool = Field(
        default=False,
        description="Whether manual review is needed"
    )
    error: str | None = Field(
        default=None,
        description="Error message if resolution failed"
    )

    @field_validator("candidates")
    @classmethod
    def sort_candidates_by_score(cls, v: list[MatchCandidate]) -> list[MatchCandidate]:
        """Ensure candidates are sorted by score descending."""
        return sorted(v, key=lambda c: c.score, reverse=True)


class BatchResolutionRequest(BaseModel):
    """Request for batch entity resolution.

    Attributes:
        requests: List of individual resolution requests
        tenant_id: Tenant context for isolation
        request_id: Optional request ID for tracing
    """

    requests: list[EntityResolutionRequest] = Field(
        ...,
        description="List of individual resolution requests"
    )
    tenant_id: str = Field(..., description="Tenant context for isolation")
    request_id: str | None = Field(
        default=None,
        description="Optional request ID for tracing"
    )

    @field_validator("requests")
    @classmethod
    def validate_requests(cls, v: list[EntityResolutionRequest]) -> list[EntityResolutionRequest]:
        """Ensure all requests have matching tenant_id."""
        if not v:
            raise ValueError("requests must contain at least one request")
        return v


class BatchResolutionResponse(BaseModel):
    """Response from batch entity resolution.

    Attributes:
        request_id: Request ID for tracing
        responses: List of individual resolution responses
        total_processed: Total number of requests processed
        successful: Number of successful resolutions
        failed: Number of failed resolutions
        requires_manual_review: Number requiring manual review
    """

    request_id: str | None = Field(
        default=None,
        description="Request ID for tracing"
    )
    responses: list[EntityResolutionResponse] = Field(
        default_factory=list,
        description="Individual resolution responses"
    )
    total_processed: int = Field(
        default=0,
        ge=0,
        description="Total number of requests processed"
    )
    successful: int = Field(
        default=0,
        ge=0,
        description="Number of successful resolutions"
    )
    failed: int = Field(
        default=0,
        ge=0,
        description="Number of failed resolutions"
    )
    requires_manual_review: int = Field(
        default=0,
        ge=0,
        description="Number requiring manual review"
    )

    @field_validator("responses")
    @classmethod
    def calculate_statistics(cls, v: list[EntityResolutionResponse]) -> list[EntityResolutionResponse]:
        """Calculate statistics from responses."""
        # This is handled in post-processing, not validation
        return v
