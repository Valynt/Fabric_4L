"""
SQLAlchemy models for Benchmark governance.

Phase 3: Create Benchmark governance entity with metadata completeness
Issue: Benchmark metadata completeness (source/version/effective date/scope/confidence in Layer 5)

Core entities:
  - BenchmarkDataset    : Versioned benchmark datasets with full metadata
  - BenchmarkVersion    : Individual benchmark versions
  - BenchmarkScope      : Scope definition for benchmark applicability

Design notes:
  - Version-locked governance with approval workflow integration
  - Complete metadata: source, version, effective date, scope, confidence
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


class BenchmarkType(str, PyEnum):
    """Types of benchmark datasets."""

    INDUSTRY_STANDARD = "industry_standard"
    """Industry-wide standard benchmarks"""

    COMPETITIVE = "competitive"
    """Competitor benchmarks"""

    HISTORICAL = "historical"
    """Historical performance benchmarks"""

    CUSTOMER_REFERENCE = "customer_reference"
    """Customer reference benchmarks"""

    INTERNAL = "internal"
    """Internal organizational benchmarks"""

    THIRD_PARTY = "third_party"
    """Third-party research benchmarks"""


class BenchmarkStatus(str, PyEnum):
    """Status of a benchmark version."""

    DRAFT = "draft"
    """Draft version, not yet submitted"""

    PENDING_APPROVAL = "pending_approval"
    """Awaiting approval"""

    APPROVED = "approved"
    """Approved and available for use"""

    DEPRECATED = "deprecated"
    """Deprecated but kept for reference"""

    ARCHIVED = "archived"
    """Archived and no longer available"""


# ---------------------------------------------------------------------------
# BenchmarkDataset — versioned benchmark dataset
# ---------------------------------------------------------------------------


class BenchmarkDataset(Base):
    """
    A versioned benchmark dataset with complete metadata.

    Benchmarks provide reference data for ROI calculations, competitive analysis,
    and performance comparisons. Each dataset has multiple versions with full
    provenance tracking.
    """

    __tablename__ = "benchmark_datasets"

    # -------------------------------------------------------------------------
    # Primary identifiers
    # -------------------------------------------------------------------------
    id = Column(
        UUID,
        primary_key=True,
        default=lambda: uuid.uuid4(),
        comment="Globally unique benchmark identifier",
    )
    tenant_id = Column(
        UUID,
        nullable=False,
        index=True,
        comment="Tenant isolation",
    )

    # -------------------------------------------------------------------------
    # Benchmark identification
    # -------------------------------------------------------------------------
    name = Column(
        String(128),
        nullable=False,
        comment="Human-readable benchmark name",
    )
    slug = Column(
        String(128),
        nullable=False,
        unique=True,
        index=True,
        comment="URL-safe slug for API references",
    )
    benchmark_type = Column(
        String(32),
        nullable=False,
        index=True,
        comment="Type of benchmark — see BenchmarkType enum",
    )
    description = Column(
        Text,
        nullable=True,
        comment="Human-readable description of the benchmark",
    )

    # -------------------------------------------------------------------------
    # Version tracking
    # -------------------------------------------------------------------------
    current_version = Column(
        String(64),
        nullable=False,
        default="1.0.0",
        comment="Current approved version (semver)",
    )
    latest_version = Column(
        String(64),
        nullable=False,
        default="1.0.0",
        comment="Latest version (including pending)",
    )

    # -------------------------------------------------------------------------
    # Source metadata
    # -------------------------------------------------------------------------
    source_name = Column(
        String(128),
        nullable=False,
        comment="Name of the data source",
    )
    source_url = Column(
        Text,
        nullable=True,
        comment="URL or reference to the source",
    )
    source_type = Column(
        String(32),
        nullable=False,
        comment="Type of source (research, survey, internal, etc.)",
    )
    source_date = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Date the source data was published or collected",
    )
    collection_methodology = Column(
        Text,
        nullable=True,
        comment="Description of data collection methodology",
    )

    # -------------------------------------------------------------------------
    # Confidence and quality
    # -------------------------------------------------------------------------
    confidence_level = Column(
        String(32),
        nullable=False,
        default="medium",
        comment="Confidence level in the data (high, medium, low)",
    )
    sample_size = Column(
        Integer,
        nullable=True,
        comment="Sample size of the benchmark data",
    )
    margin_of_error = Column(
        JSON,
        nullable=True,
        comment="Margin of error information",
    )
    data_quality_notes = Column(
        Text,
        nullable=True,
        comment="Notes on data quality and limitations",
    )

    # -------------------------------------------------------------------------
    # Lifecycle
    # -------------------------------------------------------------------------
    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        comment="Whether this benchmark is active",
    )
    deprecated_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the benchmark was deprecated",
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
        comment="Reference to current approval request (if pending)",
    )

    # -------------------------------------------------------------------------
    # Metadata
    # -------------------------------------------------------------------------
    created_by = Column(
        String(255),
        nullable=True,
        comment="User who created the benchmark",
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
    versions: Mapped[list["BenchmarkVersion"]] = relationship(
        "BenchmarkVersion",
        back_populates="benchmark",
        cascade="all, delete-orphan",
        order_by="BenchmarkVersion.version",
    )
    scopes: Mapped[list["BenchmarkScope"]] = relationship(
        "BenchmarkScope",
        back_populates="benchmark",
        cascade="all, delete-orphan",
    )

    # -------------------------------------------------------------------------
    # Indexes
    # -------------------------------------------------------------------------
    __table_args__ = (
        Index(
            "ix_benchmark_datasets_tenant_type",
            "tenant_id",
            "benchmark_type",
        ),
        Index(
            "ix_benchmark_datasets_tenant_slug",
            "tenant_id",
            "slug",
        ),
        {"extend_existing": True},
    )


# ---------------------------------------------------------------------------
# BenchmarkVersion — individual benchmark version
# ---------------------------------------------------------------------------


class BenchmarkVersion(Base):
    """
    An individual version of a benchmark dataset.

    Each version has its own data, effective dates, and approval status.
    Only approved versions can be used in calculations.
    """

    __tablename__ = "benchmark_versions"

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
    benchmark_id = Column(
        UUID,
        ForeignKey("benchmark_datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # -------------------------------------------------------------------------
    # Version details
    # -------------------------------------------------------------------------
    version = Column(
        String(64),
        nullable=False,
        comment="Semver version string (e.g., '1.0.0')",
    )
    data = Column(
        JSON,
        nullable=False,
        comment="Benchmark data (structure varies by type)",
    )
    data_schema = Column(
        JSON,
        nullable=False,
        comment="JSON Schema for the data structure",
    )

    # -------------------------------------------------------------------------
    # Effective dates
    # -------------------------------------------------------------------------
    effective_from = Column(
        DateTime(timezone=True),
        nullable=False,
        comment="Date when this version becomes effective",
    )
    effective_until = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Date when this version expires (if applicable)",
    )

    # -------------------------------------------------------------------------
    # Validation
    # -------------------------------------------------------------------------
    status = Column(
        String(32),
        nullable=False,
        default=BenchmarkStatus.DRAFT.value,
        index=True,
        comment="Approval status — see BenchmarkStatus enum",
    )
    validation_errors = Column(
        JSON,
        nullable=True,
        comment="Schema validation errors (if any)",
    )

    # -------------------------------------------------------------------------
    # Change tracking
    # -------------------------------------------------------------------------
    change_description = Column(
        Text,
        nullable=True,
        comment="Description of changes in this version",
    )
    changed_by = Column(
        String(255),
        nullable=True,
        comment="User who created this version",
    )

    # -------------------------------------------------------------------------
    # Approval workflow
    # -------------------------------------------------------------------------
    approval_request_id = Column(
        UUID,
        nullable=True,
        index=True,
        comment="Reference to approval request",
    )
    approved_by = Column(
        String(255),
        nullable=True,
        comment="User who approved this version",
    )
    approved_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="When this version was approved",
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
    benchmark: Mapped["BenchmarkDataset"] = relationship(
        "layer5_ground_truth.models.benchmark_governance.BenchmarkDataset",
        back_populates="versions",
    )

    # -------------------------------------------------------------------------
    # Indexes
    # -------------------------------------------------------------------------
    __table_args__ = (
        Index(
            "ix_benchmark_versions_tenant_benchmark",
            "tenant_id",
            "benchmark_id",
        ),
        Index(
            "ix_benchmark_versions_tenant_status",
            "tenant_id",
            "status",
        ),
        Index(
            "ix_benchmark_versions_benchmark_version",
            "benchmark_id",
            "version",
            unique=True,
        ),
        Index(
            "ix_benchmark_versions_effective",
            "effective_from",
            "effective_until",
        ),
    )


# ---------------------------------------------------------------------------
# BenchmarkScope — scope definition
# ---------------------------------------------------------------------------


class BenchmarkScope(Base):
    """
    Scope definition for benchmark applicability.

    Defines where and when a benchmark applies (industry, region, segment, etc.).
    """

    __tablename__ = "benchmark_scopes"

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
    benchmark_id = Column(
        UUID,
        ForeignKey("benchmark_datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # -------------------------------------------------------------------------
    # Scope details
    # -------------------------------------------------------------------------
    scope_type = Column(
        String(32),
        nullable=False,
        comment="Type of scope — see BenchmarkScope enum",
    )
    scope_value = Column(
        String(255),
        nullable=False,
        comment="Value of the scope (e.g., 'technology', 'north_america')",
    )
    description = Column(
        Text,
        nullable=True,
        comment="Description of the scope",
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
    benchmark: Mapped["BenchmarkDataset"] = relationship(
        "layer5_ground_truth.models.benchmark_governance.BenchmarkDataset",
        back_populates="scopes",
    )

    # -------------------------------------------------------------------------
    # Indexes
    # -------------------------------------------------------------------------
    __table_args__ = (
        Index(
            "ix_benchmark_scopes_tenant_benchmark",
            "tenant_id",
            "benchmark_id",
        ),
        Index(
            "ix_benchmark_scopes_type_value",
            "benchmark_id",
            "scope_type",
            "scope_value",
        ),
    )
