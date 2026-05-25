"""
SQLAlchemy models for Assumption registry.

Phase 4: Create Assumption registry with evidence linkage
Issue: Explicit assumption governance + evidence linkage + reviewability

Core entities:
  - Assumption         : High-impact assumptions with evidence linkage
  - AssumptionEvidence : Evidence supporting an assumption
  - AssumptionReview   : Review records for assumptions

Design notes:
  - Assumptions linked to TruthObjects for evidence
  - High-impact assumptions require approval
  - Tenant-scoped with audit trail
"""

import uuid
from datetime import UTC, datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, relationship
from sqlalchemy.types import JSON

# Import from truth_object to share the same Base and UUID type
from .truth_object import UUID, Base


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class AssumptionType(str, PyEnum):
    """Types of assumptions."""

    MARKET_GROWTH = "market_growth"
    """Market growth rate assumptions"""

    PRICING = "pricing"
    """Pricing assumptions"""

    COST_STRUCTURE = "cost_structure"
    """Cost structure assumptions"""

    TIMELINE = "timeline"
    """Timeline assumptions"""

    RESOURCE_AVAILABILITY = "resource_availability"
    """Resource availability assumptions"""

    COMPETITIVE_RESPONSE = "competitive_response"
    """Competitive response assumptions"""

    CUSTOMER_BEHAVIOR = "customer_behavior"
    """Customer behavior assumptions"""

    TECHNICAL_FEASIBILITY = "technical_feasibility"
    """Technical feasibility assumptions"""

    REGULATORY = "regulatory"
    """Regulatory assumptions"""

    CUSTOM = "custom"
    """Custom assumption type"""


class AssumptionImpact(str, PyEnum):
    """Impact level of an assumption."""

    LOW = "low"
    """Low impact on overall value"""

    MEDIUM = "medium"
    """Medium impact on overall value"""

    HIGH = "high"
    """High impact on overall value"""

    CRITICAL = "critical"
    """Critical assumption - failure significantly impacts value"""


class AssumptionStatus(str, PyEnum):
    """Status of an assumption."""

    DRAFT = "draft"
    """Draft assumption, not yet submitted"""

    PENDING_APPROVAL = "pending_approval"
    """Awaiting approval (for high-impact assumptions)"""

    APPROVED = "approved"
    """Approved and available for use"""

    REJECTED = "rejected"
    """Rejected and not available for use"""

    DEPRECATED = "deprecated"
    """Deprecated but kept for reference"""

    ARCHIVED = "archived"
    """Archived and no longer available"""


# ---------------------------------------------------------------------------
# Assumption — high-impact assumption
# ---------------------------------------------------------------------------


class Assumption(Base):
    """
    A high-impact assumption with evidence linkage.

    Assumptions are key inputs to ROI calculations and business cases.
    High-impact assumptions require approval and must be backed by evidence.
    """

    __tablename__ = "assumptions"

    # -------------------------------------------------------------------------
    # Primary identifiers
    # -------------------------------------------------------------------------
    id = Column(
        UUID,
        primary_key=True,
        default=lambda: uuid.uuid4(),
        comment="Globally unique assumption identifier",
    )
    tenant_id = Column(
        UUID,
        nullable=False,
        index=True,
        comment="Tenant isolation",
    )

    # -------------------------------------------------------------------------
    # Assumption identification
    # -------------------------------------------------------------------------
    name = Column(
        String(128),
        nullable=False,
        comment="Human-readable assumption name",
    )
    slug = Column(
        String(128),
        nullable=False,
        unique=True,
        index=True,
        comment="URL-safe slug for API references",
    )
    assumption_type = Column(
        String(32),
        nullable=False,
        index=True,
        comment="Type of assumption — see AssumptionType enum",
    )
    description = Column(
        Text,
        nullable=False,
        comment="Detailed description of the assumption",
    )

    # -------------------------------------------------------------------------
    # Assumption value
    # -------------------------------------------------------------------------
    value = Column(
        JSON,
        nullable=False,
        comment="Assumption value (structure varies by type)",
    )
    value_type = Column(
        String(32),
        nullable=False,
        comment="Data type of the value (number, percentage, string, etc.)",
    )

    # -------------------------------------------------------------------------
    # Impact assessment
    # -------------------------------------------------------------------------
    impact_level = Column(
        String(32),
        nullable=False,
        index=True,
        comment="Impact level — see AssumptionImpact enum",
    )
    sensitivity_analysis = Column(
        JSON,
        nullable=True,
        comment="Sensitivity analysis results",
    )

    # -------------------------------------------------------------------------
    # Evidence linkage
    # -------------------------------------------------------------------------
    truth_object_id = Column(
        UUID,
        nullable=True,
        index=True,
        comment="Link to supporting TruthObject (if applicable)",
    )
    evidence_count = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of evidence records supporting this assumption",
    )

    # -------------------------------------------------------------------------
    # Lifecycle
    # -------------------------------------------------------------------------
    status = Column(
        String(32),
        nullable=False,
        default=AssumptionStatus.DRAFT.value,
        index=True,
        comment="Approval status — see AssumptionStatus enum",
    )
    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        comment="Whether this assumption is active",
    )
    deprecated_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the assumption was deprecated",
    )
    deprecation_reason = Column(
        Text,
        nullable=True,
        comment="Reason for deprecation",
    )

    # -------------------------------------------------------------------------
    # Approval workflow integration
    # -------------------------------------------------------------------------
    approval_request_id = Column(
        UUID,
        nullable=True,
        index=True,
        comment="Reference to approval request (for high-impact assumptions)",
    )
    approved_by = Column(
        String(255),
        nullable=True,
        comment="User who approved this assumption",
    )
    approved_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="When this assumption was approved",
    )

    # -------------------------------------------------------------------------
    # Context
    # -------------------------------------------------------------------------
    applies_to_opportunity_id = Column(
        UUID,
        nullable=True,
        index=True,
        comment="Opportunity ID this assumption applies to (if applicable)",
    )
    applies_to_formula_id = Column(
        UUID,
        nullable=True,
        index=True,
        comment="Formula ID this assumption is used in (if applicable)",
    )

    # -------------------------------------------------------------------------
    # Metadata
    # -------------------------------------------------------------------------
    created_by = Column(
        String(255),
        nullable=True,
        comment="User who created the assumption",
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # -------------------------------------------------------------------------
    # Relationships
    # -------------------------------------------------------------------------
    evidence: Mapped[list["AssumptionEvidence"]] = relationship(
        "AssumptionEvidence",
        back_populates="assumption",
        cascade="all, delete-orphan",
    )
    reviews: Mapped[list["AssumptionReview"]] = relationship(
        "AssumptionReview",
        back_populates="assumption",
        cascade="all, delete-orphan",
        order_by="AssumptionReview.reviewed_at",
    )

    # -------------------------------------------------------------------------
    # Indexes
    # -------------------------------------------------------------------------
    __table_args__ = (
        Index(
            "ix_assumptions_tenant_type",
            "tenant_id",
            "assumption_type",
        ),
        Index(
            "ix_assumptions_tenant_slug",
            "tenant_id",
            "slug",
        ),
        Index(
            "ix_assumptions_tenant_impact",
            "tenant_id",
            "impact_level",
        ),
        Index(
            "ix_assumptions_tenant_status",
            "tenant_id",
            "status",
        ),
    )


# ---------------------------------------------------------------------------
# AssumptionEvidence — evidence supporting an assumption
# ---------------------------------------------------------------------------


class AssumptionEvidence(Base):
    """
    Evidence supporting an assumption.

    Links assumptions to TruthObjects or external sources for evidence.
    """

    __tablename__ = "assumption_evidence"

    # -------------------------------------------------------------------------
    # Primary identifiers
    # -------------------------------------------------------------------------
    id = Column(
        UUID,
        primary_key=True,
        default=lambda: uuid.uuid4(),
    )
    tenant_id = Column(
        UUID,
        nullable=False,
        index=True,
    )
    assumption_id = Column(
        UUID,
        ForeignKey("assumptions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # -------------------------------------------------------------------------
    # Evidence details
    # -------------------------------------------------------------------------
    evidence_type = Column(
        String(32),
        nullable=False,
        comment="Type of evidence (truth_object, external_source, etc.)",
    )
    truth_object_id = Column(
        UUID,
        nullable=True,
        index=True,
        comment="Link to TruthObject if evidence is from Layer 5",
    )
    source_url = Column(
        Text,
        nullable=True,
        comment="URL of external source (if applicable)",
    )
    source_title = Column(
        String(512),
        nullable=True,
        comment="Title of the evidence source",
    )
    excerpt = Column(
        Text,
        nullable=True,
        comment="Excerpt from the source supporting the assumption",
    )

    # -------------------------------------------------------------------------
    # Evidence quality
    # -------------------------------------------------------------------------
    confidence = Column(
        String(32),
        nullable=False,
        default="medium",
        comment="Confidence in this evidence (high, medium, low)",
    )
    relevance = Column(
        String(32),
        nullable=False,
        default="medium",
        comment="Relevance to the assumption (high, medium, low)",
    )

    # -------------------------------------------------------------------------
    # Metadata
    # -------------------------------------------------------------------------
    added_by = Column(
        String(255),
        nullable=True,
        comment="User who added this evidence",
    )
    added_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    notes = Column(
        Text,
        nullable=True,
        comment="Notes about this evidence",
    )

    # -------------------------------------------------------------------------
    # Relationships
    # -------------------------------------------------------------------------
    assumption: Mapped["Assumption"] = relationship(
        "Assumption",
        back_populates="evidence",
    )

    # -------------------------------------------------------------------------
    # Indexes
    # -------------------------------------------------------------------------
    __table_args__ = (
        Index(
            "ix_assumption_evidence_tenant_assumption",
            "tenant_id",
            "assumption_id",
        ),
        Index(
            "ix_assumption_evidence_truth_object",
            "truth_object_id",
        ),
    )


# ---------------------------------------------------------------------------
# AssumptionReview — review records
# ---------------------------------------------------------------------------


class AssumptionReview(Base):
    """
    Review record for an assumption.

    Tracks reviews and approvals for assumptions, especially high-impact ones.
    """

    __tablename__ = "assumption_reviews"

    # -------------------------------------------------------------------------
    # Primary identifiers
    # -------------------------------------------------------------------------
    id = Column(
        UUID,
        primary_key=True,
        default=lambda: uuid.uuid4(),
    )
    tenant_id = Column(
        UUID,
        nullable=False,
        index=True,
    )
    assumption_id = Column(
        UUID,
        ForeignKey("assumptions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # -------------------------------------------------------------------------
    # Review details
    # -------------------------------------------------------------------------
    review_type = Column(
        String(32),
        nullable=False,
        comment="Type of review (approval, rejection, feedback)",
    )
    reviewed_by = Column(
        String(255),
        nullable=False,
        comment="User who performed the review",
    )
    reviewed_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        index=True,
    )
    decision = Column(
        String(32),
        nullable=True,
        comment="Review decision (approve, reject, request_changes)",
    )
    review_notes = Column(
        Text,
        nullable=True,
        comment="Reviewer notes and feedback",
    )

    # -------------------------------------------------------------------------
    # Review context
    # -------------------------------------------------------------------------
    previous_status = Column(
        String(32),
        nullable=True,
        comment="Status before this review",
    )
    new_status = Column(
        String(32),
        nullable=True,
        comment="Status after this review",
    )
    review_metadata = Column(
        JSON,
        nullable=True,
        comment="Additional review context",
    )

    # -------------------------------------------------------------------------
    # Metadata
    # -------------------------------------------------------------------------
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

    # -------------------------------------------------------------------------
    # Relationships
    # -------------------------------------------------------------------------
    assumption: Mapped["Assumption"] = relationship(
        "Assumption",
        back_populates="reviews",
    )

    # -------------------------------------------------------------------------
    # Indexes
    # -------------------------------------------------------------------------
    __table_args__ = (
        Index(
            "ix_assumption_reviews_tenant_assumption",
            "tenant_id",
            "assumption_id",
        ),
        Index(
            "ix_assumption_reviews_reviewed_by",
            "reviewed_by",
        ),
    )
