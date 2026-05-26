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

from ..models.assumption_registry import (
    Assumption,
    AssumptionImpact,
    AssumptionStatus,
)
from ..models.approval_workflow import (
    ApprovalRequest,
    ApprovalStatus,
    EntityType,
)
from ..services.approval_state_machine import ApprovalStateMachine

logger = logging.getLogger(__name__)

# Impact levels that require approval
REQUIRES_APPROVAL = {AssumptionImpact.HIGH.value, AssumptionImpact.CRITICAL.value}


class AssumptionApprovalService:
    """
    Service for managing assumption approval gating.

    Enforces approval requirements for high-impact assumptions and
    integrates with the generic approval workflow framework.
    """

    def __init__(self) -> None:
        self._approval_state_machine = ApprovalStateMachine()

    async def requires_approval(self, assumption: Assumption) -> bool:
        """Check if an assumption requires approval based on impact level."""
        return assumption.impact_level in REQUIRES_APPROVAL

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

        # Check if there's already a pending approval request
        existing = await db.execute(
            select(ApprovalRequest).where(
                and_(
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
            tenant_id=assumption.tenant_id,
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

        # Get the approval request
        result = await db.execute(
            select(ApprovalRequest).where(ApprovalRequest.id == assumption.approval_request_id)
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

        # Get the approval request
        result = await db.execute(
            select(ApprovalRequest).where(ApprovalRequest.id == assumption.approval_request_id)
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

        # Get the approval request
        result = await db.execute(
            select(ApprovalRequest).where(ApprovalRequest.id == assumption.approval_request_id)
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
