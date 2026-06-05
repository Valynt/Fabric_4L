"""
SQLAlchemy models for the Approval Workflow framework.

Phase 2: Generic approval workflow for governance artifacts
Issue A: Missing generalized approval workflow for high-impact assumptions/formulas/benchmarks

Core entities:
  - ApprovalRequest      : Individual approval request for a governance artifact
  - ApprovalWorkflow     : Workflow definition for an entity type
  - ApprovalDecision     : Decision record for an approval request

Design notes:
  - Generic framework applicable to Formula, Benchmark, Policy, Assumption entities
  - Draft → Pending Approval → Approved → Deprecated → Archived lifecycle
  - Supports version-locked governance objects
  - Tenant-scoped with role-based approval gates
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


class ApprovalStatus(str, PyEnum):
    """Approval lifecycle states."""

    DRAFT = "draft"
    """Initial state, not yet submitted for approval"""

    PENDING = "pending"
    """Submitted and awaiting review"""

    APPROVED = "approved"
    """Approved and ready for use"""

    REJECTED = "rejected"
    """Rejected by reviewer"""

    DEPRECATED = "deprecated"
    """Previously approved but now deprecated"""

    ARCHIVED = "archived"
    """No longer in use, kept for historical reference"""


class EntityType(str, PyEnum):
    """Entity types that require approval governance."""

    FORMULA = "formula"
    """Value calculation formulas"""

    BENCHMARK = "benchmark"
    """Benchmark datasets and comparisons"""

    POLICY = "policy"
    """Business rules and policies"""

    ASSUMPTION = "assumption"
    """High-impact assumptions in models"""


class ApprovalDecisionType(str, PyEnum):
    """Types of approval decisions."""

    APPROVE = "approve"
    """Grant approval"""

    REJECT = "reject"
    """Deny approval"""

    REQUEST_CHANGES = "request_changes"
    """Request modifications before approval"""

    ESCALATE = "escalate"
    """Escalate to higher authority"""


# ---------------------------------------------------------------------------
# ApprovalRequest — individual approval request
# ---------------------------------------------------------------------------


class ApprovalRequest(Base):
    """
    An individual approval request for a governance artifact.

    Tracks the approval lifecycle for Formula, Benchmark, Policy, or Assumption entities.
    Each request is version-locked to the specific entity version being approved.
    """

    __tablename__ = "approval_requests"

    # -------------------------------------------------------------------------
    # Primary identifiers
    # -------------------------------------------------------------------------
    id = Column(
        UUID,
        primary_key=True,
        default=lambda: uuid.uuid4(),
        comment="Globally unique approval request identifier",
    )
    tenant_id = Column(
        UUID,
        nullable=False,
        index=True,
        comment="Tenant isolation",
    )

    # -------------------------------------------------------------------------
    # Entity reference
    # -------------------------------------------------------------------------
    entity_type = Column(
        String(32),
        nullable=False,
        index=True,
        comment="Type of entity requiring approval — see EntityType enum",
    )
    entity_id = Column(
        UUID,
        nullable=False,
        index=True,
        comment="ID of the entity being approved",
    )
    entity_version = Column(
        String(64),
        nullable=True,
        comment="Version of the entity being approved (if versioned)",
    )

    # -------------------------------------------------------------------------
    # Request details
    # -------------------------------------------------------------------------
    status = Column(
        String(32),
        nullable=False,
        default=ApprovalStatus.DRAFT.value,
        index=True,
        comment="Current approval status — see ApprovalStatus enum",
    )
    requested_by = Column(
        String(255),
        nullable=False,
        comment="User ID who requested approval",
    )
    requested_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        comment="When the request was created",
    )
    request_reason = Column(
        Text,
        nullable=True,
        comment="Reason for the approval request",
    )
    request_metadata = Column(
        JSON,
        nullable=True,
        comment="Additional context for the request",
    )

    # -------------------------------------------------------------------------
    # Review details
    # -------------------------------------------------------------------------
    reviewed_by = Column(
        String(255),
        nullable=True,
        comment="User ID who reviewed the request",
    )
    reviewed_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the review was completed",
    )
    review_notes = Column(
        Text,
        nullable=True,
        comment="Reviewer notes and feedback",
    )

    # -------------------------------------------------------------------------
    # Effective dates
    # -------------------------------------------------------------------------
    effective_from = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the approval becomes effective (if approved)",
    )
    effective_until = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the approval expires (if applicable)",
    )

    # -------------------------------------------------------------------------
    # Audit timestamps
    # -------------------------------------------------------------------------
    approved_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the request was approved",
    )
    rejected_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the request was rejected",
    )
    deprecated_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the approved entity was deprecated",
    )
    archived_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the request was archived",
    )

    # -------------------------------------------------------------------------
    # Metadata
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

    # -------------------------------------------------------------------------
    # Relationships
    # -------------------------------------------------------------------------
    decisions: Mapped[list["ApprovalDecision"]] = relationship(
        "ApprovalDecision",
        back_populates="approval_request",
        cascade="all, delete-orphan",
        order_by="ApprovalDecision.decided_at",
    )

    # -------------------------------------------------------------------------
    # Indexes
    # -------------------------------------------------------------------------
    __table_args__ = (
        Index(
            "ix_approval_requests_tenant_entity",
            "tenant_id",
            "entity_type",
            "entity_id",
        ),
        Index(
            "ix_approval_requests_tenant_status",
            "tenant_id",
            "status",
        ),
        Index(
            "ix_approval_requests_requested_by",
            "requested_by",
        ),
        {"extend_existing": True},
    )


# ---------------------------------------------------------------------------
# ApprovalDecision — decision record
# ---------------------------------------------------------------------------


class ApprovalDecision(Base):
    """
    A decision record for an approval request.

    Tracks individual decisions in the approval chain, supporting
    multi-step approval workflows with escalation.
    """

    __tablename__ = "approval_decisions"

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
    approval_request_id = Column(
        UUID,
        ForeignKey("approval_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # -------------------------------------------------------------------------
    # Decision details
    # -------------------------------------------------------------------------
    decision_type = Column(
        String(32),
        nullable=False,
        comment="Type of decision — see ApprovalDecisionType enum",
    )
    decided_by = Column(
        String(255),
        nullable=False,
        comment="User ID who made the decision",
    )
    decided_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        index=True,
    )
    decision_notes = Column(
        Text,
        nullable=True,
        comment="Notes explaining the decision",
    )
    decision_metadata = Column(
        JSON,
        nullable=True,
        comment="Additional decision context",
    )

    # -------------------------------------------------------------------------
    # Approval chain
    # -------------------------------------------------------------------------
    approval_level = Column(
        Integer,
        nullable=False,
        default=1,
        comment="Level in the approval chain (1 = first reviewer, 2 = escalator, etc.)",
    )
    escalated_from_id = Column(
        UUID,
        nullable=True,
        comment="ID of the decision this was escalated from (if applicable)",
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
    approval_request: Mapped["ApprovalRequest"] = relationship(
        "ApprovalRequest",
        back_populates="decisions",
    )

    # -------------------------------------------------------------------------
    # Indexes
    # -------------------------------------------------------------------------
    __table_args__ = (
        Index(
            "ix_approval_decisions_tenant_request",
            "tenant_id",
            "approval_request_id",
        ),
        Index(
            "ix_approval_decisions_decided_by",
            "decided_by",
        ),
        {"extend_existing": True},
    )


# ---------------------------------------------------------------------------
# ApprovalWorkflow — workflow definition
# ---------------------------------------------------------------------------


class ApprovalWorkflow(Base):
    """
    Workflow definition for an entity type.

    Defines the approval process for different entity types, including
    required approval levels, role requirements, and automated checks.
    """

    __tablename__ = "approval_workflows"

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

    # -------------------------------------------------------------------------
    # Workflow definition
    # -------------------------------------------------------------------------
    entity_type = Column(
        String(32),
        nullable=False,
        unique=True,
        comment="Entity type this workflow applies to — see EntityType enum",
    )
    workflow_name = Column(
        String(128),
        nullable=False,
        comment="Human-readable name of the workflow",
    )
    description = Column(
        Text,
        nullable=True,
        comment="Description of the workflow",
    )

    # -------------------------------------------------------------------------
    # Approval configuration
    # -------------------------------------------------------------------------
    required_approval_levels = Column(
        Integer,
        nullable=False,
        default=1,
        comment="Number of approval levels required",
    )
    auto_approve_threshold = Column(
        Integer,
        nullable=True,
        comment="Auto-approve if confidence score exceeds this threshold",
    )
    require_evidence = Column(
        Boolean,
        nullable=False,
        default=True,
        comment="Whether evidence attachment is required",
    )
    require_justification = Column(
        Boolean,
        nullable=False,
        default=True,
        comment="Whether justification is required for approval",
    )

    # -------------------------------------------------------------------------
    # Role requirements
    # -------------------------------------------------------------------------
    approver_roles = Column(
        JSON,
        nullable=False,
        default=list,
        comment="List of roles that can approve (e.g., ['admin', 'reviewer'])",
    )
    escalation_roles = Column(
        JSON,
        nullable=True,
        comment="List of roles that can escalate (e.g., ['senior_reviewer'])",
    )
    level_definitions = Column(
        JSON,
        nullable=True,
        comment="Ordered approval levels config (e.g., [{'level':1,'quorum':1},{'level':2,'quorum':2}])",
    )
    default_level_quorum = Column(
        Integer,
        nullable=False,
        default=1,
        comment="Default quorum required per approval level when level_definitions are omitted",
    )
    escalation_mode = Column(
        String(32),
        nullable=False,
        default="manual",
        comment="Escalation semantics (manual | automatic)",
    )

    # -------------------------------------------------------------------------
    # Lifecycle
    # -------------------------------------------------------------------------
    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        comment="Whether this workflow is active",
    )
    version = Column(
        String(64),
        nullable=False,
        default="1.0",
        comment="Workflow version",
    )

    # -------------------------------------------------------------------------
    # Metadata
    # -------------------------------------------------------------------------
    created_by = Column(
        String(255),
        nullable=True,
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
    # Indexes
    # -------------------------------------------------------------------------
    __table_args__ = (
        Index(
            "ix_approval_workflows_tenant_entity",
            "tenant_id",
            "entity_type",
        ),
    )
