"""
SQLAlchemy models for the Ground Truth Layer.

Core entities:
  - TruthObject      : The central evidence-backed fact record
  - TruthSource      : Individual evidence sources linked to a TruthObject
  - ValidationEvent  : Immutable audit log of every state transition
  - MaturityHistory  : Tracks maturity ladder progression (0-5)

Design notes:
  - Uses PostgreSQL JSONB for flexible metadata storage (mirrors Layer 1 pattern)
  - UUID primary keys throughout for distributed-safe IDs
  - Soft-delete via `deleted_at` — records are never hard-deleted
  - `tenant_id` on every table for multi-tenancy isolation
"""

import uuid
from datetime import UTC, datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON, TypeDecorator

# ---------------------------------------------------------------------------
# Declarative Base
# ---------------------------------------------------------------------------


class Base(DeclarativeBase):
    """Shared declarative base for all Layer 5 models."""

    pass


# ---------------------------------------------------------------------------
# Cross-platform UUID Type
# ---------------------------------------------------------------------------


class UUID(TypeDecorator):
    """
    Cross-platform UUID type that works with PostgreSQL and SQLite.

    Uses PostgreSQL's native UUID type when available, falls back to
    String(36) for SQLite (used in testing).
    """

    impl = String(36)
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        return dialect.type_descriptor(String(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            return str(value)
        return str(uuid.UUID(value))

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(str(value))


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class ClaimType(str, PyEnum):
    """Semantic category of the claim being recorded."""

    COST_SAVINGS_BASELINE = "cost_savings_baseline"
    REVENUE_IMPACT = "revenue_impact"
    EFFICIENCY_GAIN = "efficiency_gain"
    RISK_REDUCTION = "risk_reduction"
    COMPLIANCE_REQUIREMENT = "compliance_requirement"
    CUSTOMER_OUTCOME = "customer_outcome"
    TECHNICAL_CAPABILITY = "technical_capability"
    MARKET_BENCHMARK = "market_benchmark"
    PERSONA_PAIN_POINT = "persona_pain_point"
    VALUE_DRIVER_METRIC = "value_driver_metric"
    OTHER = "other"


class TruthStatus(str, PyEnum):
    """
    Truth lifecycle state machine — aligned with target trust-governance taxonomy.

    Transitions:
      proposed → validated | disputed | rejected
      validated → disputed | superseded | expired
      disputed → validated | rejected
      rejected → (terminal)
      superseded → (terminal)
      expired → (terminal)
    """

    PROPOSED = "proposed"  # AI-identified or ingested claim, not yet validated
    VALIDATED = "validated"  # Evidence-backed and accepted (human or gated auto)
    DISPUTED = "disputed"  # Flagged as conflicting or unreliable
    REJECTED = "rejected"  # Human-reviewed and explicitly discarded
    SUPERSEDED = "superseded"  # Replaced by a newer TruthObject
    EXPIRED = "expired"  # Past freshness TTL; re-validation required


class MaturityLevel(int, PyEnum):
    """
    Truth Maturity Ladder — mirrors the Kimi architecture doc.

    0 = Raw        : Just captured, no processing
    1 = Extracted  : AI identified the claim
    2 = Supported  : Has linked sources
    3 = Corroborated: Multiple sources align
    4 = Approved   : Human validated
    5 = Operationalized: Used in ROI / board-level decisions
    """

    RAW = 0
    EXTRACTED = 1
    SUPPORTED = 2
    CORROBORATED = 3
    APPROVED = 4
    OPERATIONALIZED = 5


class DisputeReason(str, PyEnum):
    """Reason a truth object was marked as disputed."""

    CONFLICTING_SOURCES = "conflicting_sources"
    STALE_DATA = "stale_data"
    METHODOLOGY_FLAW = "methodology_flaw"
    OUT_OF_SCOPE = "out_of_scope"
    OTHER = "other"


class RejectionReason(str, PyEnum):
    """Reason a truth object was rejected."""

    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    OUT_OF_SCOPE = "out_of_scope"
    FACTUALLY_INCORRECT = "factually_incorrect"
    SUPERSEDED = "superseded"
    OTHER = "other"


# ---------------------------------------------------------------------------
# TruthObject — the central model
# ---------------------------------------------------------------------------


class TruthObject(Base):
    """
    A single evidence-backed factual claim in the Ground Truth Layer.

    This is the atomic unit of verified knowledge. Every ROI model, value
    tree node, and executive narrative must trace back to one or more
    TruthObjects with status ≥ SUPPORTED.

    Columns mirror the Truth Object Schema from the Value Fabric architecture:
      claim, claim_type, value, sources[], confidence, status,
      approved_by, freshness, applies_to
    """

    __tablename__ = "truth_objects"

    # -------------------------------------------------------------------------
    # Primary identifiers
    # -------------------------------------------------------------------------
    id = Column(
        UUID,
        primary_key=True,
        default=lambda: uuid.uuid4(),
        comment="Globally unique truth object identifier",
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        nullable=False,
        index=True,
        comment="Tenant isolation — all queries must filter by this",
    )

    # -------------------------------------------------------------------------
    # Core claim fields (from spec)
    # -------------------------------------------------------------------------
    claim = Column(
        Text,
        nullable=False,
        comment='Natural-language statement of the fact, e.g. "20 hrs/month reconciling"',
    )
    claim_type = Column(
        String(64),
        nullable=False,
        default=ClaimType.OTHER.value,
        comment="Semantic category — see ClaimType enum",
    )
    value = Column(
        JSONB,
        nullable=True,
        comment=(
            "Structured value: {amount, unit, currency, period} "
            "e.g. {amount: 20, unit: 'hours', period: 'month'}"
        ),
    )

    # -------------------------------------------------------------------------
    # Confidence & validation state
    # -------------------------------------------------------------------------
    confidence = Column(
        Float,
        nullable=False,
        default=0.0,
        comment="Model confidence score 0.0–1.0 at time of extraction",
    )
    status = Column(
        String(32),
        nullable=False,
        default=TruthStatus.PROPOSED.value,
        index=True,
        comment="Current validation state — see TruthStatus enum",
    )
    maturity_level = Column(
        Integer,
        nullable=False,
        default=MaturityLevel.RAW.value,
        comment="Maturity ladder 0 (Raw) → 5 (Operationalized)",
    )

    # -------------------------------------------------------------------------
    # Human validation
    # -------------------------------------------------------------------------
    validated_by = Column(
        String(255),
        nullable=True,
        comment="User ID or email of the human reviewer who validated this fact",
    )
    validated_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp of human validation",
    )
    validation_notes = Column(
        Text,
        nullable=True,
        comment="Optional reviewer notes at time of validation",
    )

    # -------------------------------------------------------------------------
    # Rejection tracking
    # -------------------------------------------------------------------------
    rejected_by = Column(
        String(255),
        nullable=True,
        comment="User ID or email who rejected this fact",
    )
    rejected_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp of rejection",
    )
    rejection_reason = Column(
        String(64),
        nullable=True,
        comment="Reason for REJECTED status — see RejectionReason enum",
    )

    # -------------------------------------------------------------------------
    # Supersession tracking
    # -------------------------------------------------------------------------
    superseded_by_id = Column(
        UUID,
        ForeignKey("truth_objects.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Reference to the newer TruthObject that supersedes this one",
    )
    superseded_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when this truth was marked superseded",
    )

    # -------------------------------------------------------------------------
    # Freshness tracking
    # -------------------------------------------------------------------------
    freshness = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        comment="Date the claim was last validated or refreshed",
    )
    expires_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Date after which this fact should be re-validated",
    )
    is_stale = Column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
        comment="Set to True by the freshness monitor when expires_at is exceeded",
    )

    # -------------------------------------------------------------------------
    # Scope / applicability
    # -------------------------------------------------------------------------
    applies_to = Column(
        JSONB,
        nullable=True,
        comment=(
            "Scope of applicability: {opportunity_id, account_id, industry, "
            "product_line, geography} — any subset"
        ),
    )

    # -------------------------------------------------------------------------
    # Dispute tracking
    # -------------------------------------------------------------------------
    dispute_reason = Column(
        String(64),
        nullable=True,
        comment="Reason for DISPUTED status — see DisputeReason enum",
    )
    dispute_notes = Column(
        Text,
        nullable=True,
        comment="Free-text explanation of the dispute",
    )
    disputed_by = Column(
        String(255),
        nullable=True,
        comment="User ID or email who raised the dispute",
    )
    disputed_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    # -------------------------------------------------------------------------
    # Layer 3 Knowledge Graph linkage
    # -------------------------------------------------------------------------
    kg_node_id = Column(
        String(255),
        nullable=True,
        index=True,
        comment="Neo4j node ID in Layer 3 Knowledge Graph (set after sync)",
    )
    kg_synced_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last time this record was synced to the Knowledge Graph",
    )

    # -------------------------------------------------------------------------
    # Extraction provenance
    # -------------------------------------------------------------------------
    extraction_job_id = Column(
        String(255),
        nullable=True,
        index=True,
        comment="Layer 2 extraction job that produced this claim",
    )
    extraction_model = Column(
        String(128),
        nullable=True,
        comment="LLM / model version used for extraction",
    )
    raw_extraction_data = Column(
        JSON,
        nullable=True,
        comment="Original extraction payload for full reproducibility",
    )

    # -------------------------------------------------------------------------
    # Soft delete & audit timestamps
    # -------------------------------------------------------------------------
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
    deleted_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Soft delete timestamp — NULL means active",
    )

    # -------------------------------------------------------------------------
    # Relationships
    # -------------------------------------------------------------------------
    sources: Mapped[list["TruthSource"]] = relationship(
        "TruthSource",
        back_populates="truth_object",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    validation_events: Mapped[list["ValidationEvent"]] = relationship(
        "ValidationEvent",
        back_populates="truth_object",
        cascade="all, delete-orphan",
        order_by="ValidationEvent.created_at",
        lazy="selectin",
    )
    maturity_history: Mapped[list["MaturityHistory"]] = relationship(
        "MaturityHistory",
        back_populates="truth_object",
        cascade="all, delete-orphan",
        order_by="MaturityHistory.recorded_at",
        lazy="selectin",
    )

    # -------------------------------------------------------------------------
    # Indexes
    # -------------------------------------------------------------------------
    __table_args__ = (
        Index("ix_truth_objects_tenant_status", "tenant_id", "status"),
        Index("ix_truth_objects_tenant_claim_type", "tenant_id", "claim_type"),
        Index("ix_truth_objects_tenant_maturity", "tenant_id", "maturity_level"),
        # GIN indexes only work with PostgreSQL; they are skipped for other dialects
        Index("ix_truth_objects_applies_to", "applies_to", postgresql_using="gin"),
        Index("ix_truth_objects_value", "value", postgresql_using="gin"),
        Index("ix_truth_objects_active", "tenant_id", "deleted_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<TruthObject id={self.id} status={self.status} "
            f"maturity={self.maturity_level} claim={self.claim[:40]!r}>"
        )


# ---------------------------------------------------------------------------
# TruthSource — individual evidence records
# ---------------------------------------------------------------------------


class SourceType(str, PyEnum):
    """Type of evidence source."""

    CALL_TRANSCRIPT = "call_transcript"
    CRM_FIELD = "crm_field"
    EMAIL = "email"
    WEBSITE_CONTENT = "website_content"
    PRODUCT_DOCS = "product_docs"
    USAGE_DATA = "usage_data"
    SEC_FILING = "sec_filing"
    ANALYST_REPORT = "analyst_report"
    CUSTOMER_SURVEY = "customer_survey"
    INTERNAL_DOCUMENT = "internal_document"
    BENCHMARK_STUDY = "benchmark_study"
    OTHER = "other"


class TruthSource(Base):
    """
    An individual piece of evidence supporting a TruthObject.

    A TruthObject advances from SUPPORTED → CORROBORATED when it has
    ≥ 2 distinct TruthSource records with different source_types or
    source_urls, confirming the claim from independent angles.
    """

    __tablename__ = "truth_sources"

    id = Column(UUID, primary_key=True, default=lambda: uuid.uuid4())
    truth_object_id = Column(
        UUID,
        ForeignKey("truth_objects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID, nullable=False, index=True)

    # Source identification
    source_type = Column(
        String(64),
        nullable=False,
        default=SourceType.OTHER.value,
        comment="Category of evidence — see SourceType enum",
    )
    source_url = Column(
        Text,
        nullable=True,
        comment="URL or URI of the source document",
    )
    source_id = Column(
        String(255),
        nullable=True,
        comment="Internal document / asset ID (e.g. Layer 1 raw content ID)",
    )
    source_title = Column(
        String(512),
        nullable=True,
        comment="Human-readable title of the source",
    )

    # Evidence detail
    excerpt = Column(
        Text,
        nullable=True,
        comment="Verbatim excerpt from the source that supports the claim",
    )
    excerpt_location = Column(
        String(255),
        nullable=True,
        comment='Location within source, e.g. "page 3, paragraph 2" or "timestamp 04:32"',
    )
    confidence_contribution = Column(
        Float,
        nullable=False,
        default=0.0,
        comment="How much this source contributes to overall confidence (0.0–1.0)",
    )

    # Freshness
    source_date = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Date the source was published or captured",
    )

    # Extra metadata (renamed from 'metadata' to avoid SQLAlchemy reserved name)
    extra_metadata = Column("metadata", JSON, nullable=True, default=dict)

    created_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    created_by = Column(String(255), nullable=True)

    # Relationships
    truth_object: Mapped["TruthObject"] = relationship(
        "TruthObject",
        back_populates="sources",
    )

    __table_args__ = (
        Index("ix_truth_sources_tenant_type", "tenant_id", "source_type"),
        Index("ix_truth_sources_source_id", "source_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<TruthSource id={self.id} type={self.source_type} "
            f"truth_object_id={self.truth_object_id}>"
        )


# ---------------------------------------------------------------------------
# ValidationEvent — immutable state transition audit log
# ---------------------------------------------------------------------------


class ValidationEvent(Base):
    """
    Immutable record of every validation state transition.

    Never updated or deleted — provides a complete audit trail of how
    a TruthObject moved through the validation state machine.
    """

    __tablename__ = "validation_events"

    id = Column(UUID, primary_key=True, default=lambda: uuid.uuid4())
    truth_object_id = Column(
        UUID,
        ForeignKey("truth_objects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID, nullable=False, index=True)

    # Transition details
    from_status = Column(
        String(32),
        nullable=True,
        comment="Previous status (NULL for initial EXTRACTED state)",
    )
    to_status = Column(
        String(32),
        nullable=False,
        comment="New status after this transition",
    )
    from_maturity = Column(Integer, nullable=True)
    to_maturity = Column(Integer, nullable=False)

    # Actor
    actor = Column(
        String(255),
        nullable=True,
        comment="User ID / service name that triggered this transition",
    )
    actor_type = Column(
        String(32),
        nullable=False,
        default="system",
        comment="'human' | 'system' | 'agent'",
    )

    # Evidence snapshot
    confidence_at_transition = Column(Float, nullable=True)
    source_count_at_transition = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
    extra_metadata = Column("metadata", JSON, nullable=True, default=dict)

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        index=True,
    )

    # Relationships
    truth_object: Mapped["TruthObject"] = relationship(
        "TruthObject",
        back_populates="validation_events",
    )

    __table_args__ = (
        Index("ix_validation_events_tenant_status", "tenant_id", "to_status"),
        Index("ix_validation_events_actor", "actor"),
    )

    def __repr__(self) -> str:
        return (
            f"<ValidationEvent id={self.id} "
            f"{self.from_status} → {self.to_status} by {self.actor}>"
        )


# ---------------------------------------------------------------------------
# MaturityHistory — maturity ladder progression log
# ---------------------------------------------------------------------------


class MaturityHistory(Base):
    """
    Tracks progression through the 0–5 maturity ladder.

    Separate from ValidationEvent to allow independent maturity
    advancement (e.g. a fact can be APPROVED at maturity=4 and later
    advance to OPERATIONALIZED=5 when it is used in a board deck).
    """

    __tablename__ = "maturity_history"

    id = Column(UUID, primary_key=True, default=lambda: uuid.uuid4())
    truth_object_id = Column(
        UUID,
        ForeignKey("truth_objects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID, nullable=False, index=True)

    from_level = Column(Integer, nullable=True)
    to_level = Column(Integer, nullable=False)
    trigger = Column(
        String(128),
        nullable=True,
        comment="What triggered this advancement, e.g. 'used_in_roi_model', 'human_approval'",
    )
    triggered_by = Column(String(255), nullable=True)
    context = Column(
        JSON,
        nullable=True,
        comment="Additional context, e.g. {roi_model_id: '...', deck_id: '...'}",
    )

    recorded_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        index=True,
    )

    # Relationships
    truth_object: Mapped["TruthObject"] = relationship(
        "TruthObject",
        back_populates="maturity_history",
    )

    __table_args__ = (
        Index("ix_maturity_history_tenant_recorded", "tenant_id", "recorded_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<MaturityHistory id={self.id} level {self.from_level} → {self.to_level}>"
        )
