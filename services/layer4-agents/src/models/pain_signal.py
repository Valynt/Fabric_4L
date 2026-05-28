from __future__ import annotations

"""PainSignal domain models for Layer 4.

These models define the canonical signal representation used across
Layer 2 extraction, Layer 3 knowledge graph, and Layer 4 orchestration.
"""


from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum as PyEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SignalCategory(str, PyEnum):
    """Signal categories aligned with business value domains."""

    OPERATIONAL = "Operational"
    WORKFORCE = "Workforce"
    QUALITY = "Quality"
    COST = "Cost"
    SUPPLY_CHAIN = "Supply Chain"
    RISK = "Risk"


class TrendDirection(str, PyEnum):
    """Trend direction for signal evolution."""

    INCREASING = "increasing"
    DECREASING = "decreasing"
    STABLE = "stable"
    NEW = "new"


class ErrorCategory(str, PyEnum):
    """Categories of errors for pain signal processing."""

    VALIDATION = "validation"
    EXTRACTION = "extraction"
    ENRICHMENT = "enrichment"
    SYSTEM = "system"


class EvidenceType(str, PyEnum):
    """Types of evidence that can support a signal."""

    CASE_STUDY = "case_study"
    BENCHMARK = "benchmark"
    ROI_CALCULATOR = "roi_calculator"
    INDUSTRY_REPORT = "industry_report"


class ImpactUnit(str, PyEnum):
    """Valid units for impact quantification."""

    USD_YEAR = "USD/year"
    USD_MONTH = "USD/month"
    PERCENT_CAPACITY = "% capacity"
    PERCENT_EFFICIENCY = "% efficiency"
    HOURS_WEEK = "hours/week"
    FTE = "FTE"
    AUDIT_RISK = "Audit risk"


class EvidenceMatch(BaseModel):
    """Evidence supporting a pain signal.

    Links a signal to relevant case studies, benchmarks, or calculators
    with relevance scoring and reasoning.
    """

    model_config = ConfigDict(extra="forbid")

    evidence_id: str = Field(
        ..., description="Unique identifier for the evidence"
    )
    evidence_type: EvidenceType = Field(
        ..., description="Category of evidence"
    )
    title: str = Field(
        ..., min_length=1, max_length=300, description="Human-readable title"
    )
    match_score: int = Field(
        ..., ge=0, le=100, description="Relevance score from 0 to 100"
    )
    match_reasoning: str = Field(
        ..., min_length=10, description="Why this evidence supports the signal"
    )
    relevance_quote: str | None = Field(
        default=None, description="Direct quote from evidence source"
    )

    @field_validator("match_score")
    @classmethod
    def validate_match_score(cls, v: int) -> int:
        """Ensure match score is within valid range."""
        if not 0 <= v <= 100:
            raise ValueError("Match score must be between 0 and 100")
        return v


class PainSignal(BaseModel):
    """Canonical pain signal model.

    Represents a discovered business pain with quantified impact,
    supporting evidence, and narrative synthesis.

    This model is used for:
    - Layer 2 extraction output
    - Layer 3 knowledge graph persistence
    - Layer 4 orchestration and streaming
    - Frontend signal display
    """

    model_config = ConfigDict(extra="forbid")

    # Identity
    id: str = Field(
        ..., description="Unique identifier (UUID v4)"
    )
    account_id: str = Field(
        ..., description="Foreign key to parent account"
    )
    tenant_id: str = Field(
        ..., description="Tenant identifier for multi-tenant scoping"
    )

    # Core content
    name: str = Field(
        ..., min_length=1, max_length=200, description="Signal name (e.g., 'Production Downtime')"
    )
    category: SignalCategory = Field(
        ..., description="Business domain category"
    )
    description: str = Field(
        ..., min_length=10, description="Detailed explanation of the signal"
    )

    # Confidence
    confidence_score: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence level 0.0-1.0"
    )
    confidence_explanation: str = Field(
        ..., min_length=10, description="Rationale for confidence score"
    )

    # Impact quantification
    impact_value: Decimal | None = Field(
        default=None, description="Quantified impact value"
    )
    impact_unit: ImpactUnit | None = Field(
        default=None, description="Unit of measurement"
    )
    impact_formula_id: str | None = Field(
        default=None, description="Reference to applied formula"
    )

    # Trend analysis
    trend_direction: TrendDirection = Field(
        default=TrendDirection.NEW, description="Observed trend"
    )
    trend_explanation: str | None = Field(
        default=None, description="Rationale for trend direction"
    )

    # Evidence and synthesis
    evidence_matches: list[EvidenceMatch] = Field(
        default_factory=list, description="Supporting evidence"
    )
    executive_hypothesis: str | None = Field(
        default=None, description="Narrative synthesis for executives"
    )

    # Audit and traceability
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Last update timestamp"
    )
    source_prompt_id: str | None = Field(
        default=None, description="Trace to ProspectSetup submission"
    )
    extraction_trace_id: str | None = Field(
        default=None, description="OpenTelemetry trace ID"
    )

    @field_validator("confidence_score")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        """Ensure confidence is within valid range."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("Confidence score must be between 0.0 and 1.0")
        return v

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return self.model_dump(mode="json")

    def get_impact_display(self) -> str:
        """Get formatted impact string for display.

        Returns:
            Formatted impact string (e.g., "$2.4M/yr", "12% capacity")
        """
        if self.impact_value is None or self.impact_unit is None:
            return "Unknown"

        if self.impact_unit == ImpactUnit.USD_YEAR:
            # Format large numbers (e.g., 2400000 -> $2.4M)
            value = float(self.impact_value)
            if value >= 1_000_000:
                return f"${value / 1_000_000:.1f}M/yr"
            elif value >= 1_000:
                return f"${value / 1_000:.0f}K/yr"
            else:
                return f"${value:.0f}/yr"
        elif self.impact_unit == ImpactUnit.USD_MONTH:
            value = float(self.impact_value)
            return f"${value:,.0f}/mo"
        else:
            return f"{self.impact_value} {self.impact_unit.value}"

    def get_trend_display(self) -> str:
        """Get formatted trend string for display.

        Returns:
            Formatted trend (e.g., "↑ 23% YoY", "New", "Stable")
        """
        trend_map = {
            TrendDirection.INCREASING: "↑ Increasing",
            TrendDirection.DECREASING: "↓ Decreasing",
            TrendDirection.STABLE: "Stable",
            TrendDirection.NEW: "New",
        }
        return trend_map.get(self.trend_direction, "Unknown")


class PainSignalCreate(BaseModel):
    """Input model for creating a new pain signal.

    Used during signal extraction before persistence.
    """

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=200)
    category: SignalCategory = Field(default=SignalCategory.OPERATIONAL)
    description: str = Field(..., min_length=10)
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    confidence_explanation: str = Field(..., min_length=10)
    impact_indicators: list[str] = Field(
        default_factory=list,
        description="Clues for impact quantification"
    )
    trend_direction: TrendDirection = Field(default=TrendDirection.NEW)
    trend_explanation: str | None = None
    stakeholder_quotes: list[str] = Field(
        default_factory=list,
        description="Direct evidence from input text"
    )
    source_prompt_id: str | None = None
    extraction_trace_id: str | None = None


class PainSignalUpdate(BaseModel):
    """Input model for updating an existing pain signal.

    Used when enrichment adds evidence or quantification.
    """

    model_config = ConfigDict(extra="forbid")

    impact_value: Decimal | None = None
    impact_unit: ImpactUnit | None = None
    impact_formula_id: str | None = None
    evidence_matches: list[EvidenceMatch] | None = None
    executive_hypothesis: str | None = None
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC)
    )
