"""
Assumption approval gating service.

Phase 4: Add high-impact assumption approval gating
Issue: High-impact assumption approval gating

Integrates Assumption entities with the generic approval workflow framework.
High-impact assumptions (CRITICAL, HIGH) require approval before use.
"""

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.approval_workflow import (
    ApprovalRequest,
    ApprovalStatus,
    EntityType,
)
from ..models.assumption_registry import (
    Assumption,
    AssumptionEvidence,
    AssumptionImpact,
    AssumptionStatus,
)
from ..services.approval_state_machine import ApprovalStateMachine

logger = logging.getLogger(__name__)

# Impact levels that require approval
REQUIRES_APPROVAL = {AssumptionImpact.HIGH.value, AssumptionImpact.CRITICAL.value}


class AssumptionNotFoundError(Exception):
    """Raised when an assumption cannot be found for the tenant."""

    pass


class AssumptionApprovalService:
    """
    Service for managing assumption approval gating.

    Enforces approval requirements for high-impact assumptions and
    integrates with the generic approval workflow framework.
    """

    def __init__(self) -> None:
        self._approval_state_machine = ApprovalStateMachine()

    @staticmethod
    def _require_assumption_tenant(assumption: Assumption) -> UUID:
        """Fail closed when an assumption is missing tenant ownership metadata."""
        if assumption.tenant_id is None:
            raise ValueError(
                f"Assumption {assumption.id} is missing tenant_id; refusing to process approval workflow."
            )
        return assumption.tenant_id

    async def requires_approval(self, assumption: Assumption) -> bool:
        """Check if an assumption requires approval based on impact level."""
        return assumption.impact_level in REQUIRES_APPROVAL

    async def create_assumption(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        name: str,
        slug: str,
        assumption_type: str,
        description: str,
        value: dict,
        value_type: str,
        impact_level: str,
        truth_object_id: UUID | None = None,
        applies_to_opportunity_id: UUID | None = None,
        applies_to_formula_id: UUID | None = None,
        created_by: str | None = "system",
    ) -> Assumption:
        """Create a tenant-scoped assumption and apply approval gating."""
        assumption = Assumption(
            tenant_id=tenant_id,
            name=name,
            slug=slug,
            assumption_type=assumption_type,
            description=description,
            value=value,
            value_type=value_type,
            impact_level=impact_level,
            truth_object_id=truth_object_id,
            applies_to_opportunity_id=applies_to_opportunity_id,
            applies_to_formula_id=applies_to_formula_id,
            status=AssumptionStatus.DRAFT.value,
            is_active=True,
            evidence_count=0,
            created_by=created_by,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        db.add(assumption)
        await db.flush()

        if await self.requires_approval(assumption):
            await self.create_approval_request(db, assumption, requested_by=created_by or "system")
        else:
            assumption.status = AssumptionStatus.APPROVED.value
            assumption.approved_by = created_by
            assumption.approved_at = datetime.now(UTC)
            assumption.updated_at = datetime.now(UTC)

        await db.flush()
        return assumption

    async def list_assumptions(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        assumption_type: str | None = None,
        impact_level: str | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[Assumption], int]:
        """List tenant-scoped assumptions with optional filters."""
        query = select(Assumption).where(Assumption.tenant_id == tenant_id)
        if assumption_type:
            query = query.where(Assumption.assumption_type == assumption_type)
        if impact_level:
            query = query.where(Assumption.impact_level == impact_level)
        if status:
            query = query.where(Assumption.status == status)

        from sqlalchemy import func

        total_result = await db.execute(select(func.count()).select_from(query.subquery()))
        total = int(total_result.scalar() or 0)
        result = await db.execute(
            query.order_by(Assumption.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        )
        return list(result.scalars().all()), total

    async def add_evidence(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        assumption_id: UUID,
        evidence_type: str,
        truth_object_id: UUID | None = None,
        source_url: str | None = None,
        source_title: str | None = None,
        excerpt: str | None = None,
        confidence: str = "medium",
        relevance: str = "medium",
        notes: str | None = None,
        added_by: str | None = "system",
    ) -> Assumption:
        """Add tenant-scoped evidence to an assumption."""
        result = await db.execute(
            select(Assumption).where(
                and_(Assumption.id == assumption_id, Assumption.tenant_id == tenant_id)
            )
        )
        assumption = result.scalar_one_or_none()
        if assumption is None:
            raise AssumptionNotFoundError(f"Assumption {assumption_id} not found")

        evidence = AssumptionEvidence(
            tenant_id=tenant_id,
            assumption_id=assumption_id,
            evidence_type=evidence_type,
            truth_object_id=truth_object_id,
            source_url=source_url,
            source_title=source_title,
            excerpt=excerpt,
            confidence=confidence,
            relevance=relevance,
            notes=notes,
            added_by=added_by,
            added_at=datetime.now(UTC),
        )
        db.add(evidence)
        assumption.evidence_count = (assumption.evidence_count or 0) + 1
        assumption.updated_at = datetime.now(UTC)
        await db.flush()
        return assumption

    async def create_approval_request(
        self,
        db: AsyncSession,
        assumption: Assumption,
        requested_by: str,
        reason: str | None = None,
    ) -> ApprovalRequest:
        """
        Create an approval request for a high-impact assumption.

        Args:
            db: Database session
            assumption: The assumption requiring approval
            requested_by: User requesting approval
            reason: Reason for the approval request

        Returns:
            The created ApprovalRequest

        Raises:
            ValueError: If assumption does not require approval
        """
        if not await self.requires_approval(assumption):
            raise ValueError(
                f"Assumption with impact level '{assumption.impact_level}' does not require approval. "
                f"Only {REQUIRES_APPROVAL} impact levels require approval."
            )

        tenant_id = self._require_assumption_tenant(assumption)

        # Check if there's already a pending approval request (tenant-scoped)
        existing = await db.execute(
            select(ApprovalRequest).where(
                and_(
                    ApprovalRequest.tenant_id == tenant_id,
                    ApprovalRequest.entity_type == EntityType.ASSUMPTION.value,
                    ApprovalRequest.entity_id == assumption.id,
                    ApprovalRequest.status == ApprovalStatus.PENDING.value,
                )
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError(
                f"Assumption {assumption.id} already has a pending approval request."
            )

        # Create approval request
        request = ApprovalRequest(
            tenant_id=tenant_id,
            entity_type=EntityType.ASSUMPTION.value,
            entity_id=assumption.id,
            entity_version=None,  # Assumptions are not versioned in the same way
            status=ApprovalStatus.DRAFT.value,
            requested_by=requested_by,
            request_reason=reason or f"Approval for {assumption.impact_level} impact assumption",
            request_metadata={
                "assumption_name": assumption.name,
                "assumption_type": assumption.assumption_type,
                "impact_level": assumption.impact_level,
            },
        )
        db.add(request)
        await db.flush()

        # Link to assumption
        assumption.approval_request_id = request.id
        assumption.status = AssumptionStatus.PENDING_APPROVAL.value

        logger.info(
            "Created approval request for assumption %s (impact: %s)",
            assumption.id,
            assumption.impact_level,
        )

        return request

    async def submit_for_approval(
        self,
        db: AsyncSession,
        assumption: Assumption,
        submitter: str,
        notes: str | None = None,
    ) -> Assumption:
        """
        Submit a high-impact assumption for approval.

        Args:
            db: Database session
            assumption: The assumption to submit
            submitter: User submitting for approval
            notes: Optional notes

        Returns:
            The updated assumption

        Raises:
            ValueError: If assumption does not require approval or has no approval request
        """
        if not await self.requires_approval(assumption):
            raise ValueError(
                f"Assumption with impact level '{assumption.impact_level}' does not require approval."
            )

        if assumption.approval_request_id is None:
            raise ValueError(
                f"Assumption {assumption.id} has no approval request. "
                "Call create_approval_request first."
            )

        tenant_id = self._require_assumption_tenant(assumption)

        # Get the approval request (tenant-scoped; fail closed on mismatch)
        result = await db.execute(
            select(ApprovalRequest).where(
                and_(
                    ApprovalRequest.id == assumption.approval_request_id,
                    ApprovalRequest.tenant_id == tenant_id,
                )
            )
        )
        request = result.scalar_one_or_none()
        if request is None:
            raise ValueError(f"Approval request {assumption.approval_request_id} not found.")

        # Submit through approval state machine
        request = await self._approval_state_machine.submit_for_approval(
            db=db,
            request=request,
            submitter=submitter,
            notes=notes,
        )

        assumption.status = AssumptionStatus.PENDING_APPROVAL.value
        assumption.updated_at = datetime.now(UTC)

        logger.info(
            "Submitted assumption %s for approval",
            assumption.id,
        )

        return assumption

    async def approve_assumption(
        self,
        db: AsyncSession,
        assumption: Assumption,
        approver: str,
        notes: str | None = None,
    ) -> Assumption:
        """
        Approve a high-impact assumption.

        Args:
            db: Database session
            assumption: The assumption to approve
            approver: User approving the assumption
            notes: Optional notes

        Returns:
            The updated assumption

        Raises:
            ValueError: If assumption does not require approval or has no approval request
        """
        if not await self.requires_approval(assumption):
            raise ValueError(
                f"Assumption with impact level '{assumption.impact_level}' does not require approval."
            )

        if assumption.approval_request_id is None:
            raise ValueError(
                f"Assumption {assumption.id} has no approval request."
            )

        tenant_id = self._require_assumption_tenant(assumption)

        # Get the approval request (tenant-scoped; fail closed on mismatch)
        result = await db.execute(
            select(ApprovalRequest).where(
                and_(
                    ApprovalRequest.id == assumption.approval_request_id,
                    ApprovalRequest.tenant_id == tenant_id,
                )
            )
        )
        request = result.scalar_one_or_none()
        if request is None:
            raise ValueError(f"Approval request {assumption.approval_request_id} not found.")

        # Approve through approval state machine
        request = await self._approval_state_machine.approve(
            db=db,
            request=request,
            approver=approver,
            notes=notes,
        )

        # Update assumption
        assumption.status = AssumptionStatus.APPROVED.value
        assumption.approved_by = approver
        assumption.approved_at = datetime.now(UTC)
        assumption.updated_at = datetime.now(UTC)

        logger.info(
            "Approved assumption %s by %s",
            assumption.id,
            approver,
        )

        return assumption

    async def reject_assumption(
        self,
        db: AsyncSession,
        assumption: Assumption,
        reviewer: str,
        notes: str | None = None,
    ) -> Assumption:
        """
        Reject a high-impact assumption.

        Args:
            db: Database session
            assumption: The assumption to reject
            reviewer: User rejecting the assumption
            notes: Optional notes

        Returns:
            The updated assumption

        Raises:
            ValueError: If assumption does not require approval or has no approval request
        """
        if not await self.requires_approval(assumption):
            raise ValueError(
                f"Assumption with impact level '{assumption.impact_level}' does not require approval."
            )

        if assumption.approval_request_id is None:
            raise ValueError(
                f"Assumption {assumption.id} has no approval request."
            )

        tenant_id = self._require_assumption_tenant(assumption)

        # Get the approval request (tenant-scoped; fail closed on mismatch)
        result = await db.execute(
            select(ApprovalRequest).where(
                and_(
                    ApprovalRequest.id == assumption.approval_request_id,
                    ApprovalRequest.tenant_id == tenant_id,
                )
            )
        )
        request = result.scalar_one_or_none()
        if request is None:
            raise ValueError(f"Approval request {assumption.approval_request_id} not found.")

        # Reject through approval state machine
        request = await self._approval_state_machine.reject(
            db=db,
            request=request,
            reviewer=reviewer,
            notes=notes,
        )

        # Update assumption
        assumption.status = AssumptionStatus.REJECTED.value
        assumption.updated_at = datetime.now(UTC)

        logger.info(
            "Rejected assumption %s by %s",
            assumption.id,
            reviewer,
        )

        return assumption

    async def check_approval_status(
        self,
        db: AsyncSession,
        assumption: Assumption,
    ) -> tuple[bool, str]:
        """
        Check if an assumption is approved for use.

        Args:
            db: Database session
            assumption: The assumption to check

        Returns:
            Tuple of (is_approved, status_message)
        """
        # Low/medium impact assumptions are auto-approved
        if not await self.requires_approval(assumption):
            return True, f"Auto-approved (impact level: {assumption.impact_level})"

        # High/critical impact assumptions require explicit approval
        if assumption.status == AssumptionStatus.APPROVED.value:
            return True, f"Approved by {assumption.approved_by}"

        if assumption.status == AssumptionStatus.PENDING_APPROVAL.value:
            return False, "Pending approval"

        if assumption.status == AssumptionStatus.REJECTED.value:
            return False, "Rejected"

        if assumption.status == AssumptionStatus.DRAFT.value:
            return False, "Draft - not submitted for approval"

        return False, f"Unknown status: {assumption.status}"
