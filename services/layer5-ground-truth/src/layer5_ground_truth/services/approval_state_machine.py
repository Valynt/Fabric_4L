"""
Approval State Machine for governance artifacts.

Phase 2: Implement approval state machine (draft → pending → approved → deprecated)
Issue A: Missing generalized approval workflow for high-impact assumptions/formulas/benchmarks

Implements the approval lifecycle:
  draft → pending → approved | rejected
  approved → deprecated → archived
  rejected → (terminal, can resubmit as new draft)
  deprecated → archived
"""

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.approval_workflow import (
    ApprovalDecision,
    ApprovalDecisionType,
    ApprovalRequest,
    ApprovalStatus,
    ApprovalWorkflow,
    EntityType,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------


class InvalidApprovalTransitionError(ValueError):
    """Raised when a requested approval transition is not permitted."""
    pass


class ApprovalRequirementError(ValueError):
    """Raised when approval requirements are not met."""
    pass


class ApprovalConflictError(ValueError):
    """Raised when a concurrent approval state change conflict occurs."""
    pass


# ---------------------------------------------------------------------------
# Allowed transitions map
# ---------------------------------------------------------------------------


ALLOWED_APPROVAL_TRANSITIONS: dict[ApprovalStatus, set[ApprovalStatus]] = {
    ApprovalStatus.DRAFT: {ApprovalStatus.PENDING, ApprovalStatus.ARCHIVED},
    ApprovalStatus.PENDING: {ApprovalStatus.APPROVED, ApprovalStatus.REJECTED, ApprovalStatus.DRAFT},
    ApprovalStatus.APPROVED: {ApprovalStatus.DEPRECATED, ApprovalStatus.ARCHIVED},
    ApprovalStatus.REJECTED: set(),  # Terminal - resubmit as new draft
    ApprovalStatus.DEPRECATED: {ApprovalStatus.ARCHIVED},
    ApprovalStatus.ARCHIVED: set(),  # Terminal
}


# ---------------------------------------------------------------------------
# Approval state machine service
# ---------------------------------------------------------------------------


class ApprovalStateMachine:
    """
    Encapsulates all approval state transition logic for governance artifacts.

    Generic framework applicable to Formula, Benchmark, Policy, and Assumption entities.
    """

    def __init__(self) -> None:
        pass

    # ------------------------------------------------------------------
    # Public transition methods
    # ------------------------------------------------------------------

    async def submit_for_approval(
        self,
        db: AsyncSession,
        request: ApprovalRequest,
        submitter: str,
        notes: str | None = None,
    ) -> ApprovalRequest:
        """
        Submit a draft approval request for review (DRAFT → PENDING).

        Requirements:
          - Current status must be DRAFT
          - submitter must be the original requester
        """
        self._assert_approval_transition(request, ApprovalStatus.PENDING)

        if request.requested_by != submitter:
            raise ApprovalRequirementError(
                f"Only the original requester ({request.requested_by}) can submit for approval."
            )

        return await self._apply_approval_transition(
            db=db,
            request=request,
            new_status=ApprovalStatus.PENDING,
            actor=submitter,
            actor_type="human",
            decision_type=ApprovalDecisionType.APPROVE,
            notes=notes or "Submitted for approval",
        )

    async def approve(
        self,
        db: AsyncSession,
        request: ApprovalRequest,
        approver: str,
        notes: str | None = None,
        effective_from: datetime | None = None,
        effective_until: datetime | None = None,
    ) -> ApprovalRequest:
        """
        Approve a pending request (PENDING → APPROVED).

        Requirements:
          - Current status must be PENDING
          - approver must have required role (checked at API layer)
        """
        self._assert_approval_transition(request, ApprovalStatus.APPROVED)
        workflow = await self._require_tenant_workflow(db=db, request=request)
        await self._assert_decision_tenant_consistency(db=db, request=request)
        await self._assert_approval_requirements_met(db=db, request=request, workflow=workflow)

        request.reviewed_by = approver
        request.reviewed_at = datetime.now(UTC)
        request.review_notes = notes
        request.effective_from = effective_from
        request.effective_until = effective_until

        return await self._apply_approval_transition(
            db=db,
            request=request,
            new_status=ApprovalStatus.APPROVED,
            actor=approver,
            actor_type="human",
            decision_type=ApprovalDecisionType.APPROVE,
            notes=notes or "Approved",
            workflow=workflow,
        )

    async def reject(
        self,
        db: AsyncSession,
        request: ApprovalRequest,
        reviewer: str,
        notes: str | None = None,
    ) -> ApprovalRequest:
        """
        Reject a pending request (PENDING → REJECTED).

        Requirements:
          - Current status must be PENDING
          - reviewer must have required role
        """
        self._assert_approval_transition(request, ApprovalStatus.REJECTED)

        request.reviewed_by = reviewer
        request.reviewed_at = datetime.now(UTC)
        request.review_notes = notes

        return await self._apply_approval_transition(
            db=db,
            request=request,
            new_status=ApprovalStatus.REJECTED,
            actor=reviewer,
            actor_type="human",
            decision_type=ApprovalDecisionType.REJECT,
            notes=notes or "Rejected",
        )

    async def request_changes(
        self,
        db: AsyncSession,
        request: ApprovalRequest,
        reviewer: str,
        notes: str | None = None,
    ) -> ApprovalRequest:
        """
        Request changes and return to draft (PENDING → DRAFT).

        Requirements:
          - Current status must be PENDING
        """
        self._assert_approval_transition(request, ApprovalStatus.DRAFT)

        request.reviewed_by = reviewer
        request.reviewed_at = datetime.now(UTC)
        request.review_notes = notes

        return await self._apply_approval_transition(
            db=db,
            request=request,
            new_status=ApprovalStatus.DRAFT,
            actor=reviewer,
            actor_type="human",
            decision_type=ApprovalDecisionType.REQUEST_CHANGES,
            notes=notes or "Changes requested",
        )

    async def deprecate(
        self,
        db: AsyncSession,
        request: ApprovalRequest,
        deprecator: str,
        notes: str | None = None,
    ) -> ApprovalRequest:
        """
        Deprecate an approved request (APPROVED → DEPRECATED).

        Requirements:
          - Current status must be APPROVED
        """
        self._assert_approval_transition(request, ApprovalStatus.DEPRECATED)

        request.deprecated_at = datetime.now(UTC)

        return await self._apply_approval_transition(
            db=db,
            request=request,
            new_status=ApprovalStatus.DEPRECATED,
            actor=deprecator,
            actor_type="human",
            decision_type=ApprovalDecisionType.ESCALATE,
            notes=notes or "Deprecated",
        )

    async def archive(
        self,
        db: AsyncSession,
        request: ApprovalRequest,
        archiver: str,
        notes: str | None = None,
    ) -> ApprovalRequest:
        """
        Archive a request (DEPRECATED → ARCHIVED or DRAFT → ARCHIVED).

        Requirements:
          - Current status must be DEPRECATED or DRAFT
        """
        self._assert_approval_transition(request, ApprovalStatus.ARCHIVED)

        request.archived_at = datetime.now(UTC)

        return await self._apply_approval_transition(
            db=db,
            request=request,
            new_status=ApprovalStatus.ARCHIVED,
            actor=archiver,
            actor_type="human",
            decision_type=ApprovalDecisionType.ESCALATE,
            notes=notes or "Archived",
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _assert_approval_transition(
        self,
        request: ApprovalRequest,
        target: ApprovalStatus,
    ) -> None:
        """Raise InvalidApprovalTransitionError if the transition is not permitted."""
        current = ApprovalStatus(request.status)
        allowed = ALLOWED_APPROVAL_TRANSITIONS.get(current, set())
        if target not in allowed:
            logger.warning(
                "approval_transition_rejected",
                extra={
                    "request_id": str(request.id),
                    "entity_type": request.entity_type,
                    "entity_id": str(request.entity_id),
                    "current_status": current.value,
                    "target_status": target.value,
                },
            )
            raise InvalidApprovalTransitionError(
                f"Transition {current.value} → {target.value} is not permitted. "
                f"Allowed from {current.value}: {[s.value for s in allowed] or 'none'}."
            )

    async def _apply_approval_transition(
        self,
        db: AsyncSession,
        request: ApprovalRequest,
        new_status: ApprovalStatus,
        actor: str,
        actor_type: str,
        decision_type: ApprovalDecisionType,
        notes: str | None = None,
        workflow: ApprovalWorkflow | None = None,
    ) -> ApprovalRequest:
        """Apply a validated approval transition and record decision."""
        old_status = request.status

        # Concurrency guard: only transition if the row is still in the expected state
        result = await db.execute(
            update(ApprovalRequest)
            .where(
                and_(
                    ApprovalRequest.id == request.id,
                    ApprovalRequest.tenant_id == request.tenant_id,
                    ApprovalRequest.status == old_status,
                )
            )
            .values(
                status=new_status.value,
                updated_at=datetime.now(UTC),
            )
            .execution_options(synchronize_session=False)
        )
        if (result.rowcount or 0) != 1:
            raise ApprovalConflictError(
                "Concurrent approval state change conflict: request state changed before transition could be applied."
            )

        # Keep ORM object in sync
        request.status = new_status.value
        request.updated_at = datetime.now(UTC)

        # Set timestamp based on new status
        if new_status == ApprovalStatus.APPROVED:
            request.approved_at = datetime.now(UTC)
        elif new_status == ApprovalStatus.REJECTED:
            request.rejected_at = datetime.now(UTC)

        # Record approval decision
        decision_level = await self._compute_decision_level(db=db, request=request, workflow=workflow)
        decision = ApprovalDecision(
            tenant_id=request.tenant_id,
            approval_request_id=request.id,
            decision_type=decision_type.value,
            decided_by=actor,
            decided_at=datetime.now(UTC),
            decision_notes=notes,
            approval_level=decision_level,
        )
        db.add(decision)

        logger.info(
            "ApprovalRequest %s transitioned %s → %s by %s",
            request.id,
            old_status,
            new_status.value,
            actor,
        )

        await db.flush()
        return request

    async def _compute_decision_level(
        self,
        db: AsyncSession,
        request: ApprovalRequest,
        workflow: ApprovalWorkflow | None,
    ) -> int:
        """Compute decision level from workflow and existing decision history."""
        if workflow is None:
            return 1
        level_defs = workflow.level_definitions or []
        if not level_defs:
            return 1
        level_counts: dict[int, int] = {}
        for row in (
            await db.execute(
                select(ApprovalDecision.approval_level, func.count(ApprovalDecision.id))
                .where(
                    and_(
                        ApprovalDecision.approval_request_id == request.id,
                        ApprovalDecision.tenant_id == request.tenant_id,
                        ApprovalDecision.decision_type == ApprovalDecisionType.APPROVE.value,
                    )
                )
                .group_by(ApprovalDecision.approval_level)
            )
        ).all():
            level_counts[int(row[0])] = int(row[1])
        for level_def in sorted(level_defs, key=lambda v: int(v.get("level", 1))):
            level = int(level_def.get("level", 1))
            quorum = int(level_def.get("quorum", workflow.default_level_quorum or 1))
            if level_counts.get(level, 0) < quorum:
                return level
        return int(level_defs[-1].get("level", 1))

    async def _require_tenant_workflow(self, db: AsyncSession, request: ApprovalRequest) -> ApprovalWorkflow:
        workflow = await self.get_workflow_for_entity(db, request.tenant_id, EntityType(request.entity_type))
        if workflow is None:
            raise ApprovalRequirementError("No active approval workflow found for tenant/entity.")
        if workflow.tenant_id != request.tenant_id:
            raise ApprovalRequirementError("Workflow tenant mismatch for approval request.")
        return workflow

    async def _assert_decision_tenant_consistency(self, db: AsyncSession, request: ApprovalRequest) -> None:
        mismatched = (
            await db.execute(
                select(ApprovalDecision.id).where(
                    and_(
                        ApprovalDecision.approval_request_id == request.id,
                        ApprovalDecision.tenant_id != request.tenant_id,
                    )
                )
            )
        ).scalar_one_or_none()
        if mismatched is not None:
            raise ApprovalRequirementError("Existing decisions include foreign-tenant records.")

    async def _assert_approval_requirements_met(
        self,
        db: AsyncSession,
        request: ApprovalRequest,
        workflow: ApprovalWorkflow,
    ) -> None:
        """Enforce quorum/level guard before allowing APPROVED transition."""
        level_defs = workflow.level_definitions or []
        required_levels = workflow.required_approval_levels or 1
        if not level_defs:
            level_defs = [{"level": level, "quorum": workflow.default_level_quorum or 1} for level in range(1, required_levels + 1)]
        rows = (
            await db.execute(
                select(ApprovalDecision.approval_level, func.count(ApprovalDecision.id))
                .where(
                    and_(
                        ApprovalDecision.approval_request_id == request.id,
                        ApprovalDecision.tenant_id == request.tenant_id,
                        ApprovalDecision.decision_type == ApprovalDecisionType.APPROVE.value,
                    )
                )
                .group_by(ApprovalDecision.approval_level)
            )
        ).all()
        approved_by_level = {int(level): int(count) for level, count in rows}
        next_level = await self._compute_decision_level(db=db, request=request, workflow=workflow)
        approved_by_level[next_level] = approved_by_level.get(next_level, 0) + 1
        for level_def in sorted(level_defs, key=lambda v: int(v.get("level", 1))):
            level = int(level_def.get("level", 1))
            quorum = int(level_def.get("quorum", workflow.default_level_quorum or 1))
            if approved_by_level.get(level, 0) < quorum:
                raise ApprovalRequirementError(
                    f"Cannot approve: level {level} quorum unmet ({approved_by_level.get(level, 0)}/{quorum})."
                )

    async def get_workflow_for_entity(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        entity_type: EntityType,
    ) -> ApprovalWorkflow | None:
        """Get the active workflow for an entity type."""
        result = await db.execute(
            select(ApprovalWorkflow).where(
                and_(
                    ApprovalWorkflow.tenant_id == tenant_id,
                    ApprovalWorkflow.entity_type == entity_type.value,
                    ApprovalWorkflow.is_active.is_(True),
                )
            )
        )
        return result.scalar_one_or_none()
