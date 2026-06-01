"""
SQLAlchemy models for Formula governance.

Phase 3: Create Formula governance entity with versioning and schema validation
Issue: Formulas versioned/typed/schema-validated (Layer 5 governance)

Core entities:
  - Formula           : Versioned value calculation formulas with schema contracts
  - FormulaVersion    : Individual formula versions with validation status
  - FormulaParameter  : Parameter definitions for formulas

Design notes:
  - Version-locked governance with approval workflow integration
  - Schema validation for formula expressions
  - Type-safe parameter definitions
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


class FormulaType(str, PyEnum):
    """Types of value calculation formulas."""

    ROI_CALCULATION = "roi_calculation"
    """Return on Investment calculation"""

    COST_SAVINGS = "cost_savings"
    """Cost savings calculation"""

    REVENUE_IMPACT = "revenue_impact"
    """Revenue impact calculation"""

    EFFICIENCY_GAIN = "efficiency_gain"
    """Efficiency gain calculation"""

    RISK_REDUCTION = "risk_reduction"
    """Risk reduction calculation"""

    CUSTOM = "custom"
    """Custom formula type"""


class ParameterType(str, PyEnum):
    """Data types for formula parameters."""

    NUMBER = "number"
    """Numeric value (int or float)"""

    STRING = "string"
    """Text value"""

    BOOLEAN = "boolean"
    """True/false value"""

    CURRENCY = "currency"
    """Monetary value with currency code"""

    PERCENTAGE = "percentage"
    """Percentage value (0-100)"""

    DATE = "date"
    """Date value"""

    DURATION = "duration"
    """Time duration value"""


class FormulaStatus(str, PyEnum):
    """Status of a formula version."""

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
# Formula — versioned formula definition
# ---------------------------------------------------------------------------


class Formula(Base):
    """
    A versioned value calculation formula with schema validation.

    Formulas are used for ROI calculations, cost savings, revenue impact, etc.
    Each formula has multiple versions, with only approved versions available for use.
    """

    __tablename__ = "formulas"

    # -------------------------------------------------------------------------
    # Primary identifiers
    # -------------------------------------------------------------------------
    id = Column(
        UUID,
        primary_key=True,
        default=lambda: uuid.uuid4(),
        comment="Globally unique formula identifier",
    )
    tenant_id = Column(
        UUID,
        nullable=False,
        index=True,
        comment="Tenant isolation",
    )

    # -------------------------------------------------------------------------
    # Formula identification
    # -------------------------------------------------------------------------
    name = Column(
        String(128),
        nullable=False,
        comment="Human-readable formula name",
    )
    slug = Column(
        String(128),
        nullable=False,
        unique=True,
        index=True,
        comment="URL-safe slug for API references",
    )
    formula_type = Column(
        String(32),
        nullable=False,
        index=True,
        comment="Type of formula — see FormulaType enum",
    )
    description = Column(
        Text,
        nullable=True,
        comment="Human-readable description of what the formula calculates",
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
    # Schema contract
    # -------------------------------------------------------------------------
    input_schema = Column(
        JSON,
        nullable=False,
        comment="JSON Schema for input validation",
    )
    output_schema = Column(
        JSON,
        nullable=False,
        comment="JSON Schema for output validation",
    )

    # -------------------------------------------------------------------------
    # Lifecycle
    # -------------------------------------------------------------------------
    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        comment="Whether this formula is active",
    )
    deprecated_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the formula was deprecated",
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
        comment="User who created the formula",
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
    versions: Mapped[list["FormulaVersion"]] = relationship(
        "FormulaVersion",
        back_populates="formula",
        cascade="all, delete-orphan",
        order_by="FormulaVersion.version",
    )
    parameters: Mapped[list["FormulaParameter"]] = relationship(
        "FormulaParameter",
        back_populates="formula",
        cascade="all, delete-orphan",
    )

    # -------------------------------------------------------------------------
    # Indexes
    # -------------------------------------------------------------------------
    __table_args__ = (
        Index(
            "ix_formulas_tenant_type",
            "tenant_id",
            "formula_type",
        ),
        Index(
            "ix_formulas_tenant_slug",
            "tenant_id",
            "slug",
        ),
    )


# ---------------------------------------------------------------------------
# FormulaVersion — individual formula version
# ---------------------------------------------------------------------------


class FormulaVersion(Base):
    """
    An individual version of a formula.

    Each version has its own expression, parameters, and approval status.
    Only approved versions can be used in calculations.
    """

    __tablename__ = "formula_versions"

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
    formula_id = Column(
        UUID,
        ForeignKey("formulas.id", ondelete="CASCADE"),
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
    expression = Column(
        Text,
        nullable=False,
        comment="Formula expression (language-specific)",
    )
    expression_language = Column(
        String(32),
        nullable=False,
        default="python",
        comment="Expression language (python, javascript, etc.)",
    )

    # -------------------------------------------------------------------------
    # Validation
    # -------------------------------------------------------------------------
    status = Column(
        String(32),
        nullable=False,
        default=FormulaStatus.DRAFT.value,
        index=True,
        comment="Approval status — see FormulaStatus enum",
    )
    validation_errors = Column(
        JSON,
        nullable=True,
        comment="Schema validation errors (if any)",
    )
    test_results = Column(
        JSON,
        nullable=True,
        comment="Test case results for this version",
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
    formula: Mapped["Formula"] = relationship(
        "Formula",
        back_populates="versions",
    )

    # -------------------------------------------------------------------------
    # Indexes
    # -------------------------------------------------------------------------
    __table_args__ = (
        Index(
            "ix_formula_versions_tenant_formula",
            "tenant_id",
            "formula_id",
        ),
        Index(
            "ix_formula_versions_tenant_status",
            "tenant_id",
            "status",
        ),
        Index(
            "ix_formula_versions_formula_version",
            "formula_id",
            "version",
            unique=True,
        ),
    )


# ---------------------------------------------------------------------------
# FormulaParameter — parameter definition
# ---------------------------------------------------------------------------


class FormulaParameter(Base):
    """
    A parameter definition for a formula.

    Defines the expected input parameters for a formula, including
    type, constraints, and default values.
    """

    __tablename__ = "formula_parameters"

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
    formula_id = Column(
        UUID,
        ForeignKey("formulas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # -------------------------------------------------------------------------
    # Parameter details
    # -------------------------------------------------------------------------
    name = Column(
        String(128),
        nullable=False,
        comment="Parameter name (identifier)",
    )
    display_name = Column(
        String(128),
        nullable=True,
        comment="Human-readable parameter name",
    )
    parameter_type = Column(
        String(32),
        nullable=False,
        comment="Data type — see ParameterType enum",
    )
    description = Column(
        Text,
        nullable=True,
        comment="Parameter description",
    )

    # -------------------------------------------------------------------------
    # Constraints
    # -------------------------------------------------------------------------
    required = Column(
        Boolean,
        nullable=False,
        default=True,
        comment="Whether this parameter is required",
    )
    default_value = Column(
        JSON,
        nullable=True,
        comment="Default value for optional parameters",
    )
    min_value = Column(
        JSON,
        nullable=True,
        comment="Minimum value (for numeric types)",
    )
    max_value = Column(
        JSON,
        nullable=True,
        comment="Maximum value (for numeric types)",
    )
    allowed_values = Column(
        JSON,
        nullable=True,
        comment="List of allowed values (for enums)",
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
    formula: Mapped["Formula"] = relationship(
        "Formula",
        back_populates="parameters",
    )

    # -------------------------------------------------------------------------
    # Indexes
    # -------------------------------------------------------------------------
    __table_args__ = (
        Index(
            "ix_formula_parameters_tenant_formula",
            "tenant_id",
            "formula_id",
        ),
        Index(
            "ix_formula_parameters_formula_name",
            "formula_id",
            "name",
            unique=True,
        ),
    )
