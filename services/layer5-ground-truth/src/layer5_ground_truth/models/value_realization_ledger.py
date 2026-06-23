"""
SQLAlchemy models for Value Realization Ledger.

Phase 5: Create ValueRealizationLedger for auditable ROI updates
Issue: Value realization updates auditable

Core entities:
  - ValueRealizationEntry : Individual value realization records with audit trail
  - ValueRealizationUpdate : Update records tracking changes over time

Design notes:
  - Auditable update trail for ROI calculations and value claims
  - Tracks previous and new values with change reasons
  - Links to formulas, benchmarks, and assumptions used
  - Tenant-scoped with immutable audit trail
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
    Numeric,
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


class ValueType(str, PyEnum):
    """Types of value being tracked."""

    ROI = "roi"
    """Return on Investment"""

    COST_SAVINGS = "cost_savings"
    """Cost savings value"""

    REVENUE_IMPACT = "revenue_impact"
    """Revenue impact value"""

    EFFICIENCY_GAIN = "efficiency_gain"
    """Efficiency gain value"""

    TIME_SAVINGS = "time_savings"
    """Time savings value"""

    RISK_REDUCTION = "risk_reduction"
    """Risk reduction value"""

    CUSTOM = "custom"
    """Custom value type"""


class UpdateReason(str, PyEnum):
    """Reasons for value updates."""

    NEW_CALCULATION = "new_calculation"
    """New calculation performed"""

    DATA_REFRESH = "data_refresh"
    """Underlying data refreshed"""

    FORMULA_CHANGE = "formula_change"
    """Formula used changed"""

    BENCHMARK_UPDATE = "benchmark_update"
    """Benchmark data updated"""

    ASSUMPTION_CHANGE = "assumption_change"
    """Assumption changed"""

    CORRECTION = "correction"
    """Error correction"""

    REVALIDATION = "revalidation"
    """Periodic revalidation"""

    MANUAL_OVERRIDE = "manual_override"
    """Manual override by user"""

    OTHER = "other"
    """Other reason"""


# ---------------------------------------------------------------------------
# ValueRealizationEntry — value realization record
# ---------------------------------------------------------------------------


class ValueRealizationEntry(Base):
    """
    A value realization record with auditable update trail.

    Tracks ROI calculations, cost savings, revenue impact, and other value
    metrics over time. Each entry has a complete history of updates with
    reasons and provenance.
    """

    __tablename__ = "value_realization_entries"

    # -------------------------------------------------------------------------
    # Primary identifiers
    # -------------------------------------------------------------------------
    id = Column(
        UUID,
        primary_key=True,
        default=lambda: uuid.uuid4(),
        comment="Globally unique value realization identifier",
    )
    tenant_id = Column(
        UUID,
        nullable=False,
        index=True,
        comment="Tenant isolation",
    )

    # -------------------------------------------------------------------------
    # Entry identification
    # -------------------------------------------------------------------------
    entry_type = Column(
        String(32),
        nullable=False,
        index=True,
        comment="Type of value — see ValueType enum",
    )
    entry_name = Column(
        String(128),
        nullable=False,
        comment="Human-readable name of this value entry",
    )
    description = Column(
        Text,
        nullable=True,
        comment="Description of what this value represents",
    )

    # -------------------------------------------------------------------------
    # Current value
    # -------------------------------------------------------------------------
    current_value = Column(
        Numeric(20, 6),
        nullable=False,
        comment="Current value of this metric",
    )
    value_unit = Column(
        String(32),
        nullable=True,
        comment="Unit of value (USD, hours, percentage, etc.)",
    )
    value_currency = Column(
        String(3),
        nullable=True,
        comment="Currency code (if monetary)",
    )

    # -------------------------------------------------------------------------
    # Calculation provenance
    # -------------------------------------------------------------------------
    formula_id = Column(
        UUID,
        nullable=True,
        index=True,
        comment="Formula used for calculation (if applicable)",
    )
    formula_version = Column(
        String(64),
        nullable=True,
        comment="Version of formula used",
    )
    benchmark_id = Column(
        UUID,
        nullable=True,
        index=True,
        comment="Benchmark used for comparison (if applicable)",
    )
    benchmark_version = Column(
        String(64),
        nullable=True,
        comment="Version of benchmark used",
    )
    assumption_ids = Column(
        JSON,
        nullable=True,
        comment="List of assumption IDs used in calculation",
    )

    # -------------------------------------------------------------------------
    # Context
    # -------------------------------------------------------------------------
    opportunity_id = Column(
        UUID,
        nullable=True,
        index=True,
        comment="Opportunity ID this value relates to",
    )
    account_id = Column(
        UUID,
        nullable=True,
        index=True,
        comment="Account ID this value relates to",
    )
    business_case_id = Column(
        UUID,
        nullable=True,
        index=True,
        comment="Business case ID this value is part of",
    )

    # -------------------------------------------------------------------------
    # Lifecycle
    # -------------------------------------------------------------------------
    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        comment="Whether this entry is active",
    )
    archived_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="When this entry was archived",
    )

    # -------------------------------------------------------------------------
    # Metadata
    # -------------------------------------------------------------------------
    created_by = Column(
        String(255),
        nullable=True,
        comment="User who created this entry",
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
    updates: Mapped[list["ValueRealizationUpdate"]] = relationship(
        "ValueRealizationUpdate",
        back_populates="entry",
        cascade="all, delete-orphan",
        order_by="ValueRealizationUpdate.updated_at.desc()",
    )

    # -------------------------------------------------------------------------
    # Indexes
    # -------------------------------------------------------------------------
    __table_args__ = (
        Index(
            "ix_value_realization_entries_tenant_type",
            "tenant_id",
            "entry_type",
        ),
        Index(
            "ix_value_realization_entries_tenant_opportunity",
            "tenant_id",
            "opportunity_id",
        ),
        Index(
            "ix_value_realization_entries_tenant_account",
            "tenant_id",
            "account_id",
        ),
    )


# ---------------------------------------------------------------------------
# ValueRealizationUpdate — update record
# ---------------------------------------------------------------------------


class ValueRealizationUpdate(Base):
    """
    An update record for a value realization entry.

    Tracks every change to a value with previous value, new value,
    change reason, and provenance information. Provides a complete
    auditable trail of value changes.
    """

    __tablename__ = "value_realization_updates"

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
    entry_id = Column(
        UUID,
        ForeignKey("value_realization_entries.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # -------------------------------------------------------------------------
    # Value change
    # -------------------------------------------------------------------------
    previous_value = Column(
        Numeric(20, 6),
        nullable=True,
        comment="Previous value before this update",
    )
    new_value = Column(
        Numeric(20, 6),
        nullable=False,
        comment="New value after this update",
    )
    value_change = Column(
        Numeric(20, 6),
        nullable=True,
        comment="Absolute change (new - previous)",
    )
    value_change_percent = Column(
        Numeric(10, 4),
        nullable=True,
        comment="Percentage change",
    )

    # -------------------------------------------------------------------------
    # Update reason
    # -------------------------------------------------------------------------
    update_reason = Column(
        String(32),
        nullable=False,
        index=True,
        comment="Reason for update — see UpdateReason enum",
    )
    update_notes = Column(
        Text,
        nullable=True,
        comment="Detailed notes about the update",
    )

    # -------------------------------------------------------------------------
    # Provenance
    # -------------------------------------------------------------------------
    updated_by = Column(
        String(255),
        nullable=False,
        comment="User or system that performed the update",
    )
    updated_by_type = Column(
        String(32),
        nullable=False,
        default="human",
        comment="Type of updater (human, system, agent)",
    )

    # -------------------------------------------------------------------------
    # Calculation context at time of update
    # -------------------------------------------------------------------------
    formula_id_at_update = Column(
        UUID,
        nullable=True,
        comment="Formula used at time of update",
    )
    formula_version_at_update = Column(
        String(64),
        nullable=True,
        comment="Formula version at time of update",
    )
    benchmark_id_at_update = Column(
        UUID,
        nullable=True,
        comment="Benchmark used at time of update",
    )
    benchmark_version_at_update = Column(
        String(64),
        nullable=True,
        comment="Benchmark version at time of update",
    )
    assumption_ids_at_update = Column(
        JSON,
        nullable=True,
        comment="Assumption IDs used at time of update",
    )
    calculation_metadata = Column(
        JSON,
        nullable=True,
        comment="Additional calculation context",
    )

    # -------------------------------------------------------------------------
    # Metadata
    # -------------------------------------------------------------------------
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

    # -------------------------------------------------------------------------
    # Relationships
    # -------------------------------------------------------------------------
    entry: Mapped["ValueRealizationEntry"] = relationship(
        "ValueRealizationEntry",
        back_populates="updates",
    )

    # -------------------------------------------------------------------------
    # Indexes
    # -------------------------------------------------------------------------
    __table_args__ = (
        Index(
            "ix_value_realization_updates_tenant_entry",
            "tenant_id",
            "entry_id",
        ),
        Index(
            "ix_value_realization_updates_updated_by",
            "updated_by",
        ),
        Index(
            "ix_value_realization_updates_updated_at",
            "updated_at",
        ),
        Index(
            "ix_value_realization_updates_reason",
            "update_reason",
        ),
    )
