from __future__ import annotations

"""SQLAlchemy models for Company Knowledge Onboarding.

Stores the tenant's approved company knowledge profile, knowledge sources,
extraction records with confidence scores, and ICP profiles.

Architecture:
- Layer 4 Postgres = system of record for company knowledge and onboarding state
- Layer 3 Neo4j = downstream graph projection of approved knowledge
- Layer 1/2 = upstream ingestion and extraction pipelines
"""


import uuid
from datetime import UTC, datetime
from enum import Enum as PyEnum
from typing import Any

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base

# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class ProfileStatus(str, PyEnum):
    """Lifecycle status of a company knowledge profile."""

    DRAFT = "draft"
    NEEDS_REVIEW = "needs_review"
    APPROVED = "approved"
    ARCHIVED = "archived"


class SourceType(str, PyEnum):
    """Origin of a knowledge source."""

    WEBSITE = "website"
    ICP = "icp"
    UPLOAD = "upload"
    MANUAL = "manual"


class CrawlStatus(str, PyEnum):
    """Progress of a website crawl job."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"
    FAILED = "failed"


class AuthorityWeight(str, PyEnum):
    """How authoritative this source is considered."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class PageType(str, PyEnum):
    """Classification of a crawled / extracted page."""

    PRODUCT = "product"
    USE_CASE = "use_case"
    CASE_STUDY = "case_study"
    PRICING = "pricing"
    TRUST = "trust"
    BLOG = "blog"
    HOMEPAGE = "homepage"
    OTHER = "other"


class ReviewStatus(str, PyEnum):
    """Human review state of an extraction record."""

    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    MODIFIED = "modified"


class ICPSourceType(str, PyEnum):
    """How the ICP was provided."""

    UPLOAD = "upload"
    PASTE = "paste"
    GENERATED_FROM_WEBSITE = "generated_from_website"
    MANUAL = "manual"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now() -> datetime:
    return datetime.now(UTC)


# ---------------------------------------------------------------------------
# CompanyKnowledgeProfile
# ---------------------------------------------------------------------------


class CompanyKnowledgeProfile(Base):
    """The tenant's structured, reviewable company knowledge profile.

    Acts as the central document that aggregates extracted knowledge from
    all sources.  JSONB columns store typed sub-documents so the schema
    can evolve without migrations.
    """

    __tablename__ = "company_knowledge_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    tenant_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="default",
        comment="Tenant identifier for RLS isolation",
    )

    company_name: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="Company name as extracted or provided"
    )

    website: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="Primary company website URL"
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=ProfileStatus.DRAFT.value,
        comment="draft | needs_review | approved | archived",
    )

    version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, comment="Monotonic version number"
    )

    confidence_score: Mapped[float | None] = mapped_column(
        Numeric(3, 2),
        nullable=True,
        comment="Overall profile confidence 0.00-1.00",
    )

    # -----------------------------------------------------------------------
    # Typed JSONB sections (see feature brief §7)
    # -----------------------------------------------------------------------

    identity: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Company name, description, category, positioning, business model",
    )

    product_catalog: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Products, platform structure, capabilities, feature groups",
    )

    target_customer: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Target industries, company size, geography, buying triggers",
    )

    personas: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Economic buyer, technical buyer, champion, end user, etc.",
    )

    use_cases: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Primary, secondary, industry-specific, persona-specific use cases",
    )

    value_drivers: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Revenue uplift, cost savings, risk reduction claims with evidence",
    )

    proof_points: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Case studies, customer quotes, quantified outcomes, logos",
    )

    trust_commercial: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Security certs, compliance, pricing, packaging, integrations",
    )

    # -----------------------------------------------------------------------
    # Book-keeping
    # -----------------------------------------------------------------------

    active_source_ids: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        comment="IDs of KnowledgeSource records that contributed to this profile",
    )

    review_status: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Per-section review state: {section: status}",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_now,
        onupdate=_now,
    )

    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )

    # -----------------------------------------------------------------------
    # Relationships
    # -----------------------------------------------------------------------

    sources: Mapped[list[KnowledgeSource]] = relationship(
        "KnowledgeSource",
        back_populates="profile",
        cascade="all, delete-orphan",
    )

    extraction_records: Mapped[list[ValueExtractionRecord]] = relationship(
        "ValueExtractionRecord",
        back_populates="profile",
        cascade="all, delete-orphan",
    )

    icp_profiles: Mapped[list[ICPProfile]] = relationship(
        "ICPProfile",
        back_populates="profile",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "company_name", "version",
            name="uix_ckp_tenant_name_version",
        ),
        Index("ix_ckp_tenant_status", "tenant_id", "status"),
        Index("ix_ckp_tenant_updated", "tenant_id", "updated_at"),
        Index("ix_ckp_website", "website"),
    )

    def __repr__(self) -> str:
        return (
            f"<CompanyKnowledgeProfile("
            f"id={self.id}, company_name='{self.company_name}', "
            f"status={self.status}, version={self.version})>"
        )


# ---------------------------------------------------------------------------
# KnowledgeSource
# ---------------------------------------------------------------------------


class KnowledgeSource(Base):
    """A raw source of company knowledge: website, uploaded doc, ICP, etc.

    Tracks provenance, crawl state, and authority so downstream extraction
    can be weighted and re-processed.
    """

    __tablename__ = "knowledge_sources"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    tenant_id: Mapped[str] = mapped_column(
        String(100), nullable=False, default="default"
    )

    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("company_knowledge_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )

    source_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=SourceType.WEBSITE.value,
        comment="website | icp | upload | manual",
    )

    source_url: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="URL if source is a website page"
    )

    document_name: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="Filename if source is an upload"
    )

    content_hash: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="SHA-256 of raw content for dedup"
    )

    raw_storage_path: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="MinIO/S3 path to raw snapshot"
    )

    crawl_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=CrawlStatus.PENDING.value,
        comment="pending | in_progress | complete | failed",
    )

    authority_weight: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=AuthorityWeight.MEDIUM.value,
        comment="high | medium | low",
    )

    page_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="product | use_case | case_study | pricing | trust | blog | homepage | other",
    )

    extra_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        comment="Crawl timestamps, headers, page count, extraction job refs",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_now,
        onupdate=_now,
    )

    # -----------------------------------------------------------------------
    # Relationships
    # -----------------------------------------------------------------------

    profile: Mapped[CompanyKnowledgeProfile] = relationship(
        "CompanyKnowledgeProfile", back_populates="sources"
    )

    extraction_records: Mapped[list[ValueExtractionRecord]] = relationship(
        "ValueExtractionRecord",
        back_populates="source",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_ks_tenant_profile", "tenant_id", "profile_id"),
        Index("ix_ks_tenant_type", "tenant_id", "source_type"),
        Index("ix_ks_crawl_status", "crawl_status"),
        Index("ix_ks_content_hash", "content_hash"),
    )

    def __repr__(self) -> str:
        return (
            f"<KnowledgeSource("
            f"id={self.id}, type={self.source_type}, "
            f"crawl_status={self.crawl_status})>"
        )


# ---------------------------------------------------------------------------
# ValueExtractionRecord
# ---------------------------------------------------------------------------


class ValueExtractionRecord(Base):
    """Structured output from an extraction pass before promotion to profile.

    Holds draft entities with confidence scores, source references, and
    human review state.  This is the review-queue layer.
    """

    __tablename__ = "value_extraction_records"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_sources.id", ondelete="CASCADE"),
        nullable=False,
    )

    tenant_id: Mapped[str] = mapped_column(
        String(100), nullable=False, default="default"
    )

    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("company_knowledge_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )

    page_type: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="Classification of the extracted page"
    )

    extracted: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        comment="Typed payload: products, capabilities, personas, industries, use_cases, value_drivers, metrics, proof_points",
    )

    confidence: Mapped[float | None] = mapped_column(
        Numeric(3, 2), nullable=True, comment="Extraction confidence 0.00-1.00"
    )

    requires_review: Mapped[bool] = mapped_column(
        default=False, comment="True if confidence is low or contradictions found"
    )

    review_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=ReviewStatus.PENDING.value,
        comment="pending | accepted | rejected | modified",
    )

    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )

    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    extraction_version: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="Schema/prompt version used"
    )

    llm_model: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="Model that performed extraction"
    )

    trace_span_id: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="OpenTelemetry trace span for provenance"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_now,
        onupdate=_now,
    )

    # -----------------------------------------------------------------------
    # Relationships
    # -----------------------------------------------------------------------

    source: Mapped[KnowledgeSource] = relationship(
        "KnowledgeSource", back_populates="extraction_records"
    )

    profile: Mapped[CompanyKnowledgeProfile] = relationship(
        "CompanyKnowledgeProfile", back_populates="extraction_records"
    )

    __table_args__ = (
        Index("ix_ver_tenant_profile", "tenant_id", "profile_id"),
        Index("ix_ver_tenant_review", "tenant_id", "review_status"),
        Index("ix_ver_confidence", "confidence"),
        Index("ix_ver_requires_review", "requires_review"),
        Index("ix_ver_source_id", "source_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<ValueExtractionRecord("
            f"id={self.id}, confidence={self.confidence}, "
            f"requires_review={self.requires_review})>"
        )


# ---------------------------------------------------------------------------
# ICPProfile
# ---------------------------------------------------------------------------


class ICPProfile(Base):
    """Ideal Customer Profile linked to a CompanyKnowledgeProfile.

    A tenant may have one active ICP per knowledge profile.  Stored as
    mostly JSONB to allow flexible criteria without schema churn.
    """

    __tablename__ = "icp_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    tenant_id: Mapped[str] = mapped_column(
        String(100), nullable=False, default="default"
    )

    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("company_knowledge_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )

    industries: Mapped[list[str]] = mapped_column(
        JSON, nullable=False, default=list
    )

    company_size: Mapped[list[str]] = mapped_column(
        JSON, nullable=False, default=list, comment="Ranges or labels"
    )

    buyer_personas: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, nullable=False, default=list
    )

    user_personas: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, nullable=False, default=list
    )

    pain_points: Mapped[list[str]] = mapped_column(
        JSON, nullable=False, default=list
    )

    trigger_events: Mapped[list[str]] = mapped_column(
        JSON, nullable=False, default=list
    )

    qualification_criteria: Mapped[list[str]] = mapped_column(
        JSON, nullable=False, default=list
    )

    disqualification_criteria: Mapped[list[str]] = mapped_column(
        JSON, nullable=False, default=list
    )

    competitive_context: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True
    )

    buying_committee_structure: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True
    )

    typical_sales_motion: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )

    confidence: Mapped[float | None] = mapped_column(
        Numeric(3, 2), nullable=True, comment="ICP confidence 0.00-1.00"
    )

    source_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=ICPSourceType.MANUAL.value,
        comment="upload | paste | generated_from_website | manual",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_now,
        onupdate=_now,
    )

    # -----------------------------------------------------------------------
    # Relationships
    # -----------------------------------------------------------------------

    profile: Mapped[CompanyKnowledgeProfile] = relationship(
        "CompanyKnowledgeProfile", back_populates="icp_profiles"
    )

    __table_args__ = (
        Index("ix_icp_tenant_profile", "tenant_id", "profile_id"),
        Index("ix_icp_tenant_source", "tenant_id", "source_type"),
    )

    def __repr__(self) -> str:
        return (
            f"<ICPProfile("
            f"id={self.id}, confidence={self.confidence}, "
            f"source_type={self.source_type})>"
        )
