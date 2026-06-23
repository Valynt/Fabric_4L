"""
Integration tests for Assumption Approval Service.

Tests for assumption approval gating and workflow integration.
"""

import uuid
from datetime import UTC, datetime

import pytest

from layer5_ground_truth.models.assumption_registry import (
    Assumption,
    AssumptionImpact,
    AssumptionStatus,
)
from layer5_ground_truth.models.approval_workflow import (
    ApprovalRequest,
    ApprovalStatus,
    ApprovalWorkflow,
    EntityType,
)
from layer5_ground_truth.services.assumption_approval_service import (
    AssumptionApprovalService,
)
from tests.conftest import TEST_ORG_ID


async def _add_active_workflow(db, tenant_id=TEST_ORG_ID) -> ApprovalWorkflow:
    workflow = ApprovalWorkflow(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        entity_type=EntityType.ASSUMPTION.value,
        workflow_name="Assumption approval",
        required_approval_levels=1,
        require_evidence=False,
        require_justification=False,
        approver_roles=["admin"],
        is_active=True,
    )
    db.add(workflow)
    await db.flush()
    return workflow


class TestAssumptionApprovalService:
    @pytest.mark.asyncio
    async def test_high_impact_requires_approval(self, db):
        """HIGH and CRITICAL impact assumptions should require approval."""
        service = AssumptionApprovalService()

        for impact in [AssumptionImpact.HIGH.value, AssumptionImpact.CRITICAL.value]:
            assumption = Assumption(
                id=uuid.uuid4(),
                tenant_id=TEST_ORG_ID,
                name="Critical Assumption",
                slug=f"critical-{impact}",
                assumption_type="custom",
                description="Test assumption",
                value={"value": 100},
                value_type="number",
                impact_level=impact,
                status=AssumptionStatus.DRAFT.value,
            )
            assert await service.requires_approval(assumption) is True

    @pytest.mark.asyncio
    async def test_low_medium_impact_auto_approved(self, db):
        """LOW and MEDIUM impact assumptions should not require approval."""
        service = AssumptionApprovalService()

        for impact in [AssumptionImpact.LOW.value, AssumptionImpact.MEDIUM.value]:
            assumption = Assumption(
                id=uuid.uuid4(),
                tenant_id=TEST_ORG_ID,
                name="Low Impact Assumption",
                slug=f"low-{impact}",
                assumption_type="custom",
                description="Test assumption",
                value={"value": 100},
                value_type="number",
                impact_level=impact,
                status=AssumptionStatus.DRAFT.value,
            )
            assert await service.requires_approval(assumption) is False

    @pytest.mark.asyncio
    async def test_create_approval_request_for_high_impact(self, db):
        """Should create approval request for high-impact assumption."""
        service = AssumptionApprovalService()
        assumption = Assumption(
            id=uuid.uuid4(),
            tenant_id=TEST_ORG_ID,
            name="High Impact Assumption",
            slug="high-impact",
            assumption_type="custom",
            description="Test assumption",
            value={"value": 100},
            value_type="number",
            impact_level=AssumptionImpact.HIGH.value,
            status=AssumptionStatus.DRAFT.value,
        )
        db.add(assumption)
        await db.flush()

        request = await service.create_approval_request(
            db=db,
            assumption=assumption,
            requested_by="user@example.com",
            reason="High impact assumption requires approval",
        )

        assert request.entity_type == EntityType.ASSUMPTION.value
        assert request.entity_id == assumption.id
        assert request.status == ApprovalStatus.DRAFT.value
        assert assumption.approval_request_id == request.id

    @pytest.mark.asyncio
    async def test_cannot_create_request_for_low_impact(self, db):
        """Should raise error when creating approval request for low-impact assumption."""
        service = AssumptionApprovalService()
        assumption = Assumption(
            id=uuid.uuid4(),
            tenant_id=TEST_ORG_ID,
            name="Low Impact Assumption",
            slug="low-impact",
            assumption_type="custom",
            description="Test assumption",
            value={"value": 100},
            value_type="number",
            impact_level=AssumptionImpact.LOW.value,
            status=AssumptionStatus.DRAFT.value,
        )
        db.add(assumption)
        await db.flush()

        with pytest.raises(ValueError, match="does not require approval"):
            await service.create_approval_request(
                db=db,
                assumption=assumption,
                requested_by="user@example.com",
            )

    @pytest.mark.asyncio
    async def test_submit_for_approval(self, db):
        """Should submit high-impact assumption for approval."""
        service = AssumptionApprovalService()
        assumption = Assumption(
            id=uuid.uuid4(),
            tenant_id=TEST_ORG_ID,
            name="High Impact Assumption",
            slug="high-impact",
            assumption_type="custom",
            description="Test assumption",
            value={"value": 100},
            value_type="number",
            impact_level=AssumptionImpact.HIGH.value,
            status=AssumptionStatus.DRAFT.value,
        )
        db.add(assumption)
        await db.flush()

        # Create approval request
        request = await service.create_approval_request(
            db=db,
            assumption=assumption,
            requested_by="user@example.com",
        )
        await db.flush()

        # Submit for approval
        result = await service.submit_for_approval(
            db=db,
            assumption=assumption,
            submitter="user@example.com",
            notes="Ready for review",
        )

        assert result.status == AssumptionStatus.PENDING_APPROVAL.value

    @pytest.mark.asyncio
    async def test_approve_assumption(self, db):
        """Should approve a high-impact assumption."""
        service = AssumptionApprovalService()
        assumption = Assumption(
            id=uuid.uuid4(),
            tenant_id=TEST_ORG_ID,
            name="High Impact Assumption",
            slug="high-impact",
            assumption_type="custom",
            description="Test assumption",
            value={"value": 100},
            value_type="number",
            impact_level=AssumptionImpact.HIGH.value,
            status=AssumptionStatus.PENDING_APPROVAL.value,
            approval_request_id=uuid.uuid4(),
        )
        db.add(assumption)
        await db.flush()

        # Create and approve the approval request
        from layer5_ground_truth.models.approval_workflow import ApprovalRequest

        await _add_active_workflow(db)
        request = ApprovalRequest(
            id=assumption.approval_request_id,
            tenant_id=TEST_ORG_ID,
            entity_type=EntityType.ASSUMPTION.value,
            entity_id=assumption.id,
            status=ApprovalStatus.PENDING.value,
            requested_by="user@example.com",
        )
        db.add(request)
        await db.flush()

        # Approve assumption
        result = await service.approve_assumption(
            db=db,
            assumption=assumption,
            approver="approver@example.com",
            notes="Approved",
        )

        assert result.status == AssumptionStatus.APPROVED.value
        assert result.approved_by == "approver@example.com"
        assert result.approved_at is not None

    @pytest.mark.asyncio
    async def test_reject_assumption(self, db):
        """Should reject a high-impact assumption."""
        service = AssumptionApprovalService()
        assumption = Assumption(
            id=uuid.uuid4(),
            tenant_id=TEST_ORG_ID,
            name="High Impact Assumption",
            slug="high-impact",
            assumption_type="custom",
            description="Test assumption",
            value={"value": 100},
            value_type="number",
            impact_level=AssumptionImpact.HIGH.value,
            status=AssumptionStatus.PENDING_APPROVAL.value,
            approval_request_id=uuid.uuid4(),
        )
        db.add(assumption)
        await db.flush()

        # Create a pending approval request and let the service perform rejection.
        from layer5_ground_truth.models.approval_workflow import ApprovalRequest

        request = ApprovalRequest(
            id=assumption.approval_request_id,
            tenant_id=TEST_ORG_ID,
            entity_type=EntityType.ASSUMPTION.value,
            entity_id=assumption.id,
            status=ApprovalStatus.PENDING.value,
            requested_by="user@example.com",
        )
        db.add(request)
        await db.flush()

        # Reject assumption
        result = await service.reject_assumption(
            db=db,
            assumption=assumption,
            reviewer="reviewer@example.com",
            notes="Insufficient evidence",
        )

        assert result.status == AssumptionStatus.REJECTED.value

    @pytest.mark.asyncio
    async def test_submit_for_approval_blocks_cross_tenant_request_lookup(self, db):
        """Hostile case: Tenant A assumption cannot resolve Tenant B approval request."""
        service = AssumptionApprovalService()
        tenant_a = TEST_ORG_ID
        tenant_b = uuid.uuid4()
        assumption = Assumption(
            id=uuid.uuid4(),
            tenant_id=tenant_a,
            name="Cross Tenant Assumption",
            slug="cross-tenant-submit",
            assumption_type="custom",
            description="Test assumption",
            value={"value": 100},
            value_type="number",
            impact_level=AssumptionImpact.HIGH.value,
            status=AssumptionStatus.DRAFT.value,
            approval_request_id=uuid.uuid4(),
        )
        db.add(assumption)
        db.add(
            ApprovalRequest(
                id=assumption.approval_request_id,
                tenant_id=tenant_b,
                entity_type=EntityType.ASSUMPTION.value,
                entity_id=assumption.id,
                status=ApprovalStatus.DRAFT.value,
                requested_by="user@example.com",
            )
        )
        await db.flush()

        with pytest.raises(ValueError, match="not found"):
            await service.submit_for_approval(
                db=db,
                assumption=assumption,
                submitter="user@example.com",
            )

    @pytest.mark.asyncio
    async def test_create_approval_request_fails_closed_when_tenant_missing(self, db):
        """Fail closed when assumption lacks tenant ownership metadata."""
        service = AssumptionApprovalService()
        assumption = Assumption(
            id=uuid.uuid4(),
            tenant_id=None,
            name="No Tenant Assumption",
            slug="no-tenant",
            assumption_type="custom",
            description="Test assumption",
            value={"value": 100},
            value_type="number",
            impact_level=AssumptionImpact.HIGH.value,
            status=AssumptionStatus.DRAFT.value,
        )
        with pytest.raises(ValueError, match="missing tenant_id"):
            await service.create_approval_request(
                db=db,
                assumption=assumption,
                requested_by="user@example.com",
            )

    @pytest.mark.asyncio
    async def test_check_approval_status_auto_approved(self, db):
        """Should return auto-approved for low/medium impact assumptions."""
        service = AssumptionApprovalService()
        assumption = Assumption(
            id=uuid.uuid4(),
            tenant_id=TEST_ORG_ID,
            name="Low Impact Assumption",
            slug="low-impact",
            assumption_type="custom",
            description="Test assumption",
            value={"value": 100},
            value_type="number",
            impact_level=AssumptionImpact.LOW.value,
            status=AssumptionStatus.DRAFT.value,
        )
        db.add(assumption)
        await db.flush()

        is_approved, message = await service.check_approval_status(db=db, assumption=assumption)

        assert is_approved is True
        assert "Auto-approved" in message

    @pytest.mark.asyncio
    async def test_check_approval_status_approved(self, db):
        """Should return approved for explicitly approved assumptions."""
        service = AssumptionApprovalService()
        assumption = Assumption(
            id=uuid.uuid4(),
            tenant_id=TEST_ORG_ID,
            name="High Impact Assumption",
            slug="high-impact",
            assumption_type="custom",
            description="Test assumption",
            value={"value": 100},
            value_type="number",
            impact_level=AssumptionImpact.HIGH.value,
            status=AssumptionStatus.APPROVED.value,
            approved_by="approver@example.com",
            approved_at=datetime.now(UTC),
        )
        db.add(assumption)
        await db.flush()

        is_approved, message = await service.check_approval_status(db=db, assumption=assumption)

        assert is_approved is True
        assert "Approved by" in message

    @pytest.mark.asyncio
    async def test_check_approval_status_pending(self, db):
        """Should return pending for assumptions awaiting approval."""
        service = AssumptionApprovalService()
        assumption = Assumption(
            id=uuid.uuid4(),
            tenant_id=TEST_ORG_ID,
            name="High Impact Assumption",
            slug="high-impact",
            assumption_type="custom",
            description="Test assumption",
            value={"value": 100},
            value_type="number",
            impact_level=AssumptionImpact.HIGH.value,
            status=AssumptionStatus.PENDING_APPROVAL.value,
        )
        db.add(assumption)
        await db.flush()

        is_approved, message = await service.check_approval_status(db=db, assumption=assumption)

        assert is_approved is False
        assert "Pending approval" in message

    @pytest.mark.asyncio
    async def test_check_approval_status_rejected(self, db):
        """Should return rejected for rejected assumptions."""
        service = AssumptionApprovalService()
        assumption = Assumption(
            id=uuid.uuid4(),
            tenant_id=TEST_ORG_ID,
            name="High Impact Assumption",
            slug="high-impact",
            assumption_type="custom",
            description="Test assumption",
            value={"value": 100},
            value_type="number",
            impact_level=AssumptionImpact.HIGH.value,
            status=AssumptionStatus.REJECTED.value,
        )
        db.add(assumption)
        await db.flush()

        is_approved, message = await service.check_approval_status(db=db, assumption=assumption)

        assert is_approved is False
        assert "Rejected" in message
