"""
Integration tests for Approval State Machine.

Tests for the approval workflow state transitions.
"""

import uuid
from datetime import UTC, datetime

import pytest

from layer5_ground_truth.models.approval_workflow import (
    ApprovalDecision,
    ApprovalDecisionType,
    ApprovalRequest,
    ApprovalStatus,
    ApprovalWorkflow,
    EntityType,
)
from layer5_ground_truth.services.approval_state_machine import (
    ApprovalConflictError,
    ApprovalStateMachine,
    InvalidApprovalTransitionError,
)
from tests.conftest import TEST_ORG_ID


class TestApprovalStateMachine:
    @staticmethod
    async def _add_active_workflow(db, tenant_id, levels=1, level_definitions=None):
        workflow = ApprovalWorkflow(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            entity_type=EntityType.FORMULA.value,
            workflow_name="Formula Approval",
            required_approval_levels=levels,
            approver_roles=["admin"],
            is_active=True,
            level_definitions=level_definitions,
            default_level_quorum=1,
        )
        db.add(workflow)
        await db.flush()
        return workflow

    @pytest.mark.asyncio
    async def test_submit_for_approval(self, db):
        """Should transition DRAFT → PENDING when submitted."""
        sm = ApprovalStateMachine()
        request = ApprovalRequest(
            id=uuid.uuid4(),
            tenant_id=TEST_ORG_ID,
            entity_type=EntityType.FORMULA.value,
            entity_id=uuid.uuid4(),
            status=ApprovalStatus.DRAFT.value,
            requested_by="user@example.com",
            requested_at=datetime.now(UTC),
        )
        db.add(request)
        await db.flush()

        result = await sm.submit_for_approval(
            db=db,
            request=request,
            submitter="user@example.com",
            notes="Ready for review",
        )

        assert result.status == ApprovalStatus.PENDING.value
        assert result.requested_by == "user@example.com"

    @pytest.mark.asyncio
    async def test_submit_for_approval_requires_original_requester(self, db):
        """Should only allow original requester to submit."""
        sm = ApprovalStateMachine()
        request = ApprovalRequest(
            id=uuid.uuid4(),
            tenant_id=TEST_ORG_ID,
            entity_type=EntityType.FORMULA.value,
            entity_id=uuid.uuid4(),
            status=ApprovalStatus.DRAFT.value,
            requested_by="original@example.com",
            requested_at=datetime.now(UTC),
        )
        db.add(request)
        await db.flush()

        with pytest.raises(Exception, match="Only the original requester"):
            await sm.submit_for_approval(
                db=db,
                request=request,
                submitter="other@example.com",
            )

    @pytest.mark.asyncio
    async def test_approve_pending_request(self, db):
        """Should transition PENDING → APPROVED when approved."""
        sm = ApprovalStateMachine()
        request = ApprovalRequest(
            id=uuid.uuid4(),
            tenant_id=TEST_ORG_ID,
            entity_type=EntityType.FORMULA.value,
            entity_id=uuid.uuid4(),
            status=ApprovalStatus.PENDING.value,
            requested_by="user@example.com",
            requested_at=datetime.now(UTC),
        )
        db.add(request)
        await db.flush()

        await self._add_active_workflow(db, TEST_ORG_ID)
        result = await sm.approve(
            db=db,
            request=request,
            approver="approver@example.com",
            notes="Approved",
        )

        assert result.status == ApprovalStatus.APPROVED.value
        assert result.reviewed_by == "approver@example.com"
        assert result.approved_at is not None

    @pytest.mark.asyncio
    async def test_approve_rejects_when_multilevel_quorum_not_met(self, db):
        sm = ApprovalStateMachine()
        await self._add_active_workflow(
            db,
            TEST_ORG_ID,
            levels=2,
            level_definitions=[{"level": 1, "quorum": 1}, {"level": 2, "quorum": 1}],
        )
        request = ApprovalRequest(
            id=uuid.uuid4(),
            tenant_id=TEST_ORG_ID,
            entity_type=EntityType.FORMULA.value,
            entity_id=uuid.uuid4(),
            status=ApprovalStatus.PENDING.value,
            requested_by="user@example.com",
            requested_at=datetime.now(UTC),
        )
        db.add(request)
        await db.flush()
        with pytest.raises(Exception, match="quorum unmet"):
            await sm.approve(db=db, request=request, approver="approver@example.com")

    @pytest.mark.asyncio
    async def test_approve_blocks_cross_tenant_workflow_and_decisions(self, db):
        sm = ApprovalStateMachine()
        tenant_a = TEST_ORG_ID
        tenant_b = uuid.uuid4()
        await self._add_active_workflow(db, tenant_b)
        request = ApprovalRequest(
            id=uuid.uuid4(),
            tenant_id=tenant_a,
            entity_type=EntityType.FORMULA.value,
            entity_id=uuid.uuid4(),
            status=ApprovalStatus.PENDING.value,
            requested_by="user@example.com",
            requested_at=datetime.now(UTC),
        )
        db.add(request)
        await db.flush()
        with pytest.raises(Exception, match="No active approval workflow"):
            await sm.approve(db=db, request=request, approver="approver@example.com")

    @pytest.mark.asyncio
    async def test_reject_pending_request(self, db):
        """Should transition PENDING → REJECTED when rejected."""
        sm = ApprovalStateMachine()
        request = ApprovalRequest(
            id=uuid.uuid4(),
            tenant_id=TEST_ORG_ID,
            entity_type=EntityType.FORMULA.value,
            entity_id=uuid.uuid4(),
            status=ApprovalStatus.PENDING.value,
            requested_by="user@example.com",
            requested_at=datetime.now(UTC),
        )
        db.add(request)
        await db.flush()

        result = await sm.reject(
            db=db,
            request=request,
            reviewer="reviewer@example.com",
            notes="Insufficient evidence",
        )

        assert result.status == ApprovalStatus.REJECTED.value
        assert result.reviewed_by == "reviewer@example.com"
        assert result.rejected_at is not None

    @pytest.mark.asyncio
    async def test_request_changes_returns_to_draft(self, db):
        """Should transition PENDING → DRAFT when changes requested."""
        sm = ApprovalStateMachine()
        request = ApprovalRequest(
            id=uuid.uuid4(),
            tenant_id=TEST_ORG_ID,
            entity_type=EntityType.FORMULA.value,
            entity_id=uuid.uuid4(),
            status=ApprovalStatus.PENDING.value,
            requested_by="user@example.com",
            requested_at=datetime.now(UTC),
        )
        db.add(request)
        await db.flush()

        result = await sm.request_changes(
            db=db,
            request=request,
            reviewer="reviewer@example.com",
            notes="Please add more documentation",
        )

        assert result.status == ApprovalStatus.DRAFT.value
        assert result.reviewed_by == "reviewer@example.com"

    @pytest.mark.asyncio
    async def test_deprecate_approved_request(self, db):
        """Should transition APPROVED → DEPRECATED."""
        sm = ApprovalStateMachine()
        request = ApprovalRequest(
            id=uuid.uuid4(),
            tenant_id=TEST_ORG_ID,
            entity_type=EntityType.FORMULA.value,
            entity_id=uuid.uuid4(),
            status=ApprovalStatus.APPROVED.value,
            requested_by="user@example.com",
            requested_at=datetime.now(UTC),
        )
        db.add(request)
        await db.flush()

        result = await sm.deprecate(
            db=db,
            request=request,
            deprecator="admin@example.com",
            notes="Replaced by new version",
        )

        assert result.status == ApprovalStatus.DEPRECATED.value
        assert result.deprecated_at is not None

    @pytest.mark.asyncio
    async def test_archive_deprecated_request(self, db):
        """Should transition DEPRECATED → ARCHIVED."""
        sm = ApprovalStateMachine()
        request = ApprovalRequest(
            id=uuid.uuid4(),
            tenant_id=TEST_ORG_ID,
            entity_type=EntityType.FORMULA.value,
            entity_id=uuid.uuid4(),
            status=ApprovalStatus.DEPRECATED.value,
            requested_by="user@example.com",
            requested_at=datetime.now(UTC),
        )
        db.add(request)
        await db.flush()

        result = await sm.archive(
            db=db,
            request=request,
            archiver="admin@example.com",
        )

        assert result.status == ApprovalStatus.ARCHIVED.value
        assert result.archived_at is not None

    @pytest.mark.asyncio
    async def test_invalid_transition_raises_error(self, db):
        """Should raise InvalidApprovalTransitionError for invalid transitions."""
        sm = ApprovalStateMachine()
        request = ApprovalRequest(
            id=uuid.uuid4(),
            tenant_id=TEST_ORG_ID,
            entity_type=EntityType.FORMULA.value,
            entity_id=uuid.uuid4(),
            status=ApprovalStatus.APPROVED.value,
            requested_by="user@example.com",
            requested_at=datetime.now(UTC),
        )
        db.add(request)
        await db.flush()

        with pytest.raises(InvalidApprovalTransitionError):
            await sm.submit_for_approval(
                db=db,
                request=request,
                submitter="user@example.com",
            )

    @pytest.mark.asyncio
    async def test_creates_approval_decision(self, db):
        """Should create an ApprovalDecision record on transition."""
        sm = ApprovalStateMachine()
        await self._add_active_workflow(db, TEST_ORG_ID)
        request = ApprovalRequest(
            id=uuid.uuid4(),
            tenant_id=TEST_ORG_ID,
            entity_type=EntityType.FORMULA.value,
            entity_id=uuid.uuid4(),
            status=ApprovalStatus.PENDING.value,
            requested_by="user@example.com",
            requested_at=datetime.now(UTC),
        )
        db.add(request)
        await db.flush()

        await sm.approve(
            db=db,
            request=request,
            approver="approver@example.com",
            notes="Approved",
        )
        await db.flush()

        from sqlalchemy import select

        decisions = (
            await db.execute(
                select(ApprovalDecision).where(
                    ApprovalDecision.approval_request_id == request.id
                )
            )
        ).scalars().all()

        assert len(decisions) == 1
        assert decisions[0].decision_type == ApprovalDecisionType.APPROVE.value
        assert decisions[0].decided_by == "approver@example.com"

    @pytest.mark.asyncio
    async def test_concurrent_transition_conflict(self, db):
        """Should raise ApprovalConflictError on concurrent state changes."""
        sm = ApprovalStateMachine()
        await self._add_active_workflow(db, TEST_ORG_ID)
        request = ApprovalRequest(
            id=uuid.uuid4(),
            tenant_id=TEST_ORG_ID,
            entity_type=EntityType.FORMULA.value,
            entity_id=uuid.uuid4(),
            status=ApprovalStatus.PENDING.value,
            requested_by="user@example.com",
            requested_at=datetime.now(UTC),
        )
        db.add(request)
        await db.flush()

        # Simulate a concurrent row-level state change while this ORM object
        # still represents the stale pending state held by the caller.
        from sqlalchemy import update

        await db.execute(
            update(ApprovalRequest)
            .where(ApprovalRequest.id == request.id)
            .values(status=ApprovalStatus.REJECTED.value)
            .execution_options(synchronize_session=False)
        )
        request.status = ApprovalStatus.PENDING.value

        with pytest.raises(ApprovalConflictError, match="Concurrent"):
            await sm.approve(
                db=db,
                request=request,
                approver="approver@example.com",
            )

    @pytest.mark.asyncio
    async def test_get_workflow_for_entity(self, db):
        """Should retrieve workflow for an entity type."""
        from layer5_ground_truth.models.approval_workflow import ApprovalWorkflow

        sm = ApprovalStateMachine()
        workflow = ApprovalWorkflow(
            id=uuid.uuid4(),
            tenant_id=TEST_ORG_ID,
            entity_type=EntityType.FORMULA.value,
            workflow_name="Formula Approval",
            required_approval_levels=1,
            approver_roles=["admin"],
            is_active=True,
        )
        db.add(workflow)
        await db.flush()

        result = await sm.get_workflow_for_entity(
            db=db,
            tenant_id=TEST_ORG_ID,
            entity_type=EntityType.FORMULA,
        )

        assert result is not None
        assert result.entity_type == EntityType.FORMULA.value

    @pytest.mark.asyncio
    async def test_get_workflow_returns_none_for_inactive(self, db):
        """Should return None for inactive workflows."""
        from layer5_ground_truth.models.approval_workflow import ApprovalWorkflow

        sm = ApprovalStateMachine()
        workflow = ApprovalWorkflow(
            id=uuid.uuid4(),
            tenant_id=TEST_ORG_ID,
            entity_type=EntityType.FORMULA.value,
            workflow_name="Formula Approval",
            required_approval_levels=1,
            approver_roles=["admin"],
            is_active=False,  # Inactive
        )
        db.add(workflow)
        await db.flush()

        result = await sm.get_workflow_for_entity(
            db=db,
            tenant_id=TEST_ORG_ID,
            entity_type=EntityType.FORMULA,
        )

        assert result is None
