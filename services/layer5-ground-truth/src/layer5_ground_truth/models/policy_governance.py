"""
SQLAlchemy models for Policy governance.

Phase 3: Create Policy governance entity with rules engine integration
Issue: Policy objects/rules engine APIs tied to formula/benchmark application decisions

Core entities:
  - Policy             : Versioned policy definitions with rules
  - PolicyRule         : Individual rules within a policy
  - PolicyApplication  : Record of policy applications to formulas/benchmarks

Design notes:
  - Version-locked governance with approval workflow integration
  - Rules engine integration for policy evaluation
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


class PolicyType(str, PyEnum):
    """Types of policies."""

    FORMULA_APPROVAL = "formula_approval"
    """Policy governing formula approval requirements"""

    BENCHMARK_APPROVAL = "benchmark_approval"
    """Policy governing benchmark approval requirements"""

    ASSUMPTION_APPROVAL = "assumption_approval"
    """Policy governing assumption approval requirements"""

    VALUE_THRESHOLD = "value_threshold"
    """Policy for value calculation thresholds"""

    RISK_ASSESSMENT = "risk_assessment"
    """Policy for risk assessment requirements"""

    COMPLIANCE = "compliance"
    """Compliance-related policies"""

    CUSTOM = "custom"
    """Custom policy type"""


class RuleOperator(str, PyEnum):
    """Operators for policy rules."""

    EQUALS = "equals"
    """Value must equal"""

    NOT_EQUALS = "not_equals"
    """Value must not equal"""

    GREATER_THAN = "greater_than"
    """Value must be greater than"""

    LESS_THAN = "less_than"
    """Value must be less than"""

    GREATER_THAN_OR_EQUAL = "greater_than_or_equal"
    """Value must be greater than or equal"""

    LESS_THAN_OR_EQUAL = "less_than_or_equal"
    """Value must be less than or equal"""

    CONTAINS = "contains"
    """Value must contain"""

    NOT_CONTAINS = "not_contains"
    """Value must not contain"""

    IN = "in"
    """Value must be in list"""

    NOT_IN = "not_in"
    """Value must not be in list"""

    REGEX = "regex"
    """Value must match regex pattern"""


class PolicyStatus(str, PyEnum):
    """Status of a policy version."""

    DRAFT = "draft"
    """Draft version, not yet submitted"""

    PENDING_APPROVAL = "pending_approval"
    """Awaiting approval"""

    APPROVED = "approved"
    """Approved and active"""

    DEPRECATED = "deprecated"
    """Deprecated but kept for reference"""

    ARCHIVED = "archived"
    """Archived and no longer available"""


# ---------------------------------------------------------------------------
# Policy — versioned policy definition
# ---------------------------------------------------------------------------


class Policy(Base):
    """
    A versioned policy definition with rules.

    Policies define business rules that govern formula approval, benchmark usage,
    assumption validation, and other governance decisions. Each policy has
    multiple versions with approval workflow integration.
    """

    __tablename__ = "policies"

    # -------------------------------------------------------------------------
    # Primary identifiers
    # -------------------------------------------------------------------------
    id = Column(
        UUID,
        primary_key=True,
        default=lambda: uuid.uuid4(),
        comment="Globally unique policy identifier",
    )
    tenant_id = Column(
        UUID,
        nullable=False,
        index=True,
        comment="Tenant isolation",
    )

    # -------------------------------------------------------------------------
    # Policy identification
    # -------------------------------------------------------------------------
    name = Column(
        String(128),
        nullable=False,
        comment="Human-readable policy name",
    )
    slug = Column(
        String(128),
        nullable=False,
        unique=True,
        index=True,
        comment="URL-safe slug for API references",
    )
    policy_type = Column(
        String(32),
        nullable=False,
        index=True,
        comment="Type of policy — see PolicyType enum",
    )
    description = Column(
        Text,
        nullable=True,
        comment="Human-readable description of the policy",
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
    # Policy configuration
    # -------------------------------------------------------------------------
    is_mandatory = Column(
        Boolean,
        nullable=False,
        default=True,
        comment="Whether this policy is mandatory (cannot be bypassed)",
    )
    severity = Column(
        String(32),
        nullable=False,
        default="medium",
        comment="Severity level (low, medium, high, critical)",
    )
    applies_to_entity_types = Column(
        JSON,
        nullable=False,
        default=list,
        comment="List of entity types this policy applies to",
    )

    # -------------------------------------------------------------------------
    # Lifecycle
    # -------------------------------------------------------------------------
    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        comment="Whether this policy is active",
    )
    deprecated_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the policy was deprecated",
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
        comment="User who created the policy",
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
    versions: Mapped[list["PolicyVersion"]] = relationship(
        "PolicyVersion",
        back_populates="policy",
        cascade="all, delete-orphan",
        order_by="PolicyVersion.version",
    )
    rules: Mapped[list["PolicyRule"]] = relationship(
        "PolicyRule",
        back_populates="policy",
        cascade="all, delete-orphan",
    )
    applications: Mapped[list["PolicyApplication"]] = relationship(
        "PolicyApplication",
        back_populates="policy",
        cascade="all, delete-orphan",
    )

    # -------------------------------------------------------------------------
    # Indexes
    # -------------------------------------------------------------------------
    __table_args__ = (
        Index(
            "ix_policies_tenant_type",
            "tenant_id",
            "policy_type",
        ),
        Index(
            "ix_policies_tenant_slug",
            "tenant_id",
            "slug",
        ),
    )


# ---------------------------------------------------------------------------
# PolicyVersion — individual policy version
# ---------------------------------------------------------------------------


class PolicyVersion(Base):
    """
    An individual version of a policy.

    Each version has its own rules, effective dates, and approval status.
    Only approved versions can be used for policy evaluation.
    """

    __tablename__ = "policy_versions"

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
    policy_id = Column(
        UUID,
        ForeignKey("policies.id", ondelete="CASCADE"),
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
    rules_engine_config = Column(
        JSON,
        nullable=False,
        comment="Rules engine configuration for this version",
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
        default=PolicyStatus.DRAFT.value,
        index=True,
        comment="Approval status — see PolicyStatus enum",
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
    policy: Mapped["Policy"] = relationship(
        "Policy",
        back_populates="versions",
    )

    # -------------------------------------------------------------------------
    # Indexes
    # -------------------------------------------------------------------------
    __table_args__ = (
        Index(
            "ix_policy_versions_tenant_policy",
            "tenant_id",
            "policy_id",
        ),
        Index(
            "ix_policy_versions_tenant_status",
            "tenant_id",
            "status",
        ),
        Index(
            "ix_policy_versions_policy_version",
            "policy_id",
            "version",
            unique=True,
        ),
        Index(
            "ix_policy_versions_effective",
            "effective_from",
            "effective_until",
        ),
    )


# ---------------------------------------------------------------------------
# PolicyRule — individual rule within a policy
# ---------------------------------------------------------------------------


class PolicyRule(Base):
    """
    An individual rule within a policy.

    Rules define the specific conditions and actions for policy evaluation.
    Each rule has an operator, target field, and expected value.
    """

    __tablename__ = "policy_rules"

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
    policy_id = Column(
        UUID,
        ForeignKey("policies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # -------------------------------------------------------------------------
    # Rule details
    # -------------------------------------------------------------------------
    rule_name = Column(
        String(128),
        nullable=False,
        comment="Human-readable rule name",
    )
    rule_order = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Order of rule evaluation (lower = earlier)",
    )
    target_field = Column(
        String(128),
        nullable=False,
        comment="Field to evaluate (e.g., 'confidence', 'sample_size')",
    )
    operator = Column(
        String(32),
        nullable=False,
        comment="Comparison operator — see RuleOperator enum",
    )
    expected_value = Column(
        JSON,
        nullable=False,
        comment="Expected value for comparison",
    )
    error_message = Column(
        Text,
        nullable=True,
        comment="Error message when rule fails",
    )

    # -------------------------------------------------------------------------
    # Rule configuration
    # -------------------------------------------------------------------------
    is_blocking = Column(
        Boolean,
        nullable=False,
        default=True,
        comment="Whether this rule blocks the operation when it fails",
    )
    severity = Column(
        String(32),
        nullable=False,
        default="medium",
        comment="Severity level for this rule",
    )

    # -------------------------------------------------------------------------
    # Metadata
    # -------------------------------------------------------------------------
    description = Column(
        Text,
        nullable=True,
        comment="Description of the rule",
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

    # -------------------------------------------------------------------------
    # Relationships
    # -------------------------------------------------------------------------
    policy: Mapped["Policy"] = relationship(
        "Policy",
        back_populates="rules",
    )

    # -------------------------------------------------------------------------
    # Indexes
    # -------------------------------------------------------------------------
    __table_args__ = (
        Index(
            "ix_policy_rules_tenant_policy",
            "tenant_id",
            "policy_id",
        ),
        Index(
            "ix_policy_rules_policy_order",
            "policy_id",
            "rule_order",
        ),
    )


# ---------------------------------------------------------------------------
# PolicyApplication — record of policy applications
# ---------------------------------------------------------------------------


class PolicyApplication(Base):
    """
    Record of a policy application to an entity.

    Tracks when a policy was evaluated against a formula, benchmark, or assumption,
    and the result of that evaluation.
    """

    __tablename__ = "policy_applications"

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
    policy_id = Column(
        UUID,
        ForeignKey("policies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # -------------------------------------------------------------------------
    # Entity reference
    # -------------------------------------------------------------------------
    entity_type = Column(
        String(32),
        nullable=False,
        index=True,
        comment="Type of entity the policy was applied to",
    )
    entity_id = Column(
        UUID,
        nullable=False,
        index=True,
        comment="ID of the entity the policy was applied to",
    )
    entity_version = Column(
        String(64),
        nullable=True,
        comment="Version of the entity (if versioned)",
    )

    # -------------------------------------------------------------------------
    # Application details
    # -------------------------------------------------------------------------
    applied_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        index=True,
        comment="When the policy was applied",
    )
    applied_by = Column(
        String(255),
        nullable=True,
        comment="User or system that applied the policy",
    )
    result = Column(
        String(32),
        nullable=False,
        comment="Result of policy evaluation (passed, failed, warning)",
    )
    rule_results = Column(
        JSON,
        nullable=True,
        comment="Detailed results for each rule in the policy",
    )
    context = Column(
        JSON,
        nullable=True,
        comment="Context data used for evaluation",
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
    policy: Mapped["Policy"] = relationship(
        "Policy",
        back_populates="applications",
    )

    # -------------------------------------------------------------------------
    # Indexes
    # -------------------------------------------------------------------------
    __table_args__ = (
        Index(
            "ix_policy_applications_tenant_policy",
            "tenant_id",
            "policy_id",
        ),
        Index(
            "ix_policy_applications_entity",
            "entity_type",
            "entity_id",
        ),
        Index(
            "ix_policy_applications_applied_at",
            "applied_at",
        ),
    )
