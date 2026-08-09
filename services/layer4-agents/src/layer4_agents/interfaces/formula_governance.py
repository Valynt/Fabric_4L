from __future__ import annotations

"""Formula Governance interface for Layer 4 Agents.

Provides versioned, governed financial logic with activation lifecycle.
Internal interfaces for core operations, API contracts for management.
"""


from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class FormulaStatus(str, Enum):
    """Formula lifecycle status."""

    DRAFT = "draft"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    RETIRED = "retired"


@dataclass
class FormulaVersion:
    """Formula version metadata."""

    version: str  # semver
    formula_id: str
    status: FormulaStatus
    created_at: datetime
    created_by: str
    change_summary: str
    previous_version: str | None = None


@dataclass
class FormulaGovernance:
    """Governance metadata for a formula."""

    formula_id: str
    current_version: str
    status: FormulaStatus

    # Version history
    versions: list[FormulaVersion] = field(default_factory=list)

    # Approval workflow
    approvers: list[str] = field(default_factory=list)
    approved_at: datetime | None = None
    approved_by: str | None = None

    # Metadata
    owner: str | None = None
    department: str | None = None
    review_cycle_days: int = 90
    last_reviewed_at: datetime | None = None
    next_review_at: datetime | None = None


@dataclass
class FormulaDependency:
    """Dependency relationship between formulas."""

    source_formula_id: str
    target_formula_id: str
    dependency_type: str  # "uses", "extends", "validates"
    created_at: datetime = field(default_factory=datetime.now(UTC))


@dataclass
class ActivationRequest:
    """Request to activate a formula version."""

    formula_id: str
    version: str
    requested_by: str
    justification: str
    effective_date: datetime | None = None


@dataclass
class DeprecationRequest:
    """Request to deprecate a formula."""

    formula_id: str
    replacement_formula_id: str | None
    deprecation_date: datetime
    reason: str
    requested_by: str


@dataclass
class GovernanceTransitionResult:
    """Result of governance state transition."""

    success: bool
    formula_id: str
    old_status: FormulaStatus
    new_status: FormulaStatus
    error_message: str | None = None
    requires_approval: bool = False


class IFormulaGovernanceService(ABC):
    """Abstract interface for Formula Governance.

    Internal service interface for core governance operations.
    HTTP API exposed for administrative management.
    """

    @abstractmethod
    async def get_governance(self, formula_id: str, tenant_id: str) -> FormulaGovernance | None:
        """Retrieve governance metadata for formula."""
        pass

    @abstractmethod
    async def create_version(
        self,
        formula_id: str,
        tenant_id: str,
        new_version: str,
        change_summary: str,
        created_by: str,
    ) -> FormulaVersion:
        """Create new formula version."""
        pass

    @abstractmethod
    async def list_versions(
        self,
        formula_id: str,
        tenant_id: str,
        include_retired: bool = False,
    ) -> list[FormulaVersion]:
        """List all versions of a formula."""
        pass

    @abstractmethod
    async def activate(
        self,
        request: ActivationRequest,
        tenant_id: str,
    ) -> GovernanceTransitionResult:
        """Activate a formula version."""
        pass

    @abstractmethod
    async def deprecate(
        self,
        request: DeprecationRequest,
        tenant_id: str,
    ) -> GovernanceTransitionResult:
        """Deprecate a formula."""
        pass

    @abstractmethod
    async def get_dependencies(
        self,
        formula_id: str,
        tenant_id: str,
        direction: str = "outgoing",  # outgoing, incoming, both
    ) -> list[FormulaDependency]:
        """Get formula dependencies."""
        pass

    @abstractmethod
    async def validate_activation(
        self,
        formula_id: str,
        tenant_id: str,
        version: str,
    ) -> dict[str, Any]:
        """Validate if formula can be activated."""
        pass


class IFormulaApprovalWorkflow(ABC):
    """Interface for formula approval workflow.

    Admin-only transitions with audit trail.
    """

    @abstractmethod
    async def submit_for_review(
        self,
        formula_id: str,
        tenant_id: str,
        version: str,
        submitted_by: str,
    ) -> GovernanceTransitionResult:
        """Submit formula for review."""
        pass

    @abstractmethod
    async def approve(
        self,
        formula_id: str,
        tenant_id: str,
        version: str,
        approved_by: str,
        comments: str | None = None,
    ) -> GovernanceTransitionResult:
        """Approve formula (admin only)."""
        pass

    @abstractmethod
    async def reject(
        self,
        formula_id: str,
        tenant_id: str,
        version: str,
        rejected_by: str,
        reason: str,
    ) -> GovernanceTransitionResult:
        """Reject formula (admin only)."""
        pass
