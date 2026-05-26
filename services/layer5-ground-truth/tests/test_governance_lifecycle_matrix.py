"""Lifecycle matrix and approval-gating regression tests for governance objects."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from layer5_ground_truth.models.approval_workflow import (
    ApprovalRequest,
    ApprovalStatus,
    EntityType,
)
from layer5_ground_truth.models.assumption_registry import Assumption, AssumptionImpact
from layer5_ground_truth.services.approval_state_machine import (
    ALLOWED_APPROVAL_TRANSITIONS,
    ApprovalStateMachine,
    InvalidApprovalTransitionError,
)
from layer5_ground_truth.services.assumption_approval_service import AssumptionApprovalService
from tests.conftest import TEST_ORG_ID


_TRANSITION_FN = {
    ApprovalStatus.PENDING: "submit_for_approval",
    ApprovalStatus.APPROVED: "approve",
    ApprovalStatus.REJECTED: "reject",
    ApprovalStatus.DRAFT: "request_changes",
    ApprovalStatus.DEPRECATED: "deprecate",
    ApprovalStatus.ARCHIVED: "archive",
}


@pytest.mark.asyncio
@pytest.mark.parametrize("from_status", list(ApprovalStatus))
@pytest.mark.parametrize("to_status", list(ApprovalStatus))
async def test_approval_lifecycle_matrix_enforces_legal_and_illegal_transitions(db, from_status, to_status):
    """Validate all lifecycle transitions: legal transitions pass; illegal transitions fail closed."""
    if to_status not in _TRANSITION_FN:
        pytest.skip("No direct state-machine entrypoint for target status")

    request = ApprovalRequest(
        id=uuid.uuid4(),
        tenant_id=TEST_ORG_ID,
        entity_type=EntityType.ASSUMPTION.value,
        entity_id=uuid.uuid4(),
        status=from_status.value,
        requested_by="owner@example.com",
        requested_at=datetime.now(UTC),
    )
    db.add(request)
    await db.flush()

    sm = ApprovalStateMachine()
    call = getattr(sm, _TRANSITION_FN[to_status])

    kwargs = {"db": db, "request": request}
    if to_status == ApprovalStatus.PENDING:
        kwargs.update(submitter="owner@example.com")
    elif to_status == ApprovalStatus.APPROVED:
        kwargs.update(approver="approver@example.com")
    elif to_status == ApprovalStatus.REJECTED:
        kwargs.update(reviewer="reviewer@example.com")
    elif to_status == ApprovalStatus.DRAFT:
        kwargs.update(reviewer="reviewer@example.com")
    elif to_status == ApprovalStatus.DEPRECATED:
        kwargs.update(deprecator="admin@example.com")
    elif to_status == ApprovalStatus.ARCHIVED:
        kwargs.update(archiver="admin@example.com")

    is_legal = to_status in ALLOWED_APPROVAL_TRANSITIONS[from_status]

    if is_legal:
        updated = await call(**kwargs)
        assert updated.status == to_status.value
    else:
        with pytest.raises(InvalidApprovalTransitionError):
            await call(**kwargs)


@pytest.mark.asyncio
async def test_high_impact_assumptions_are_approval_gated_and_low_impact_are_not(db):
    """Critical/high impact assumptions must be gated; low impact assumptions must not be gated."""
    service = AssumptionApprovalService()

    high = Assumption(
        id=uuid.uuid4(),
        tenant_id=TEST_ORG_ID,
        name="Strategic dependency risk",
        assumption_type="risk",
        impact_level=AssumptionImpact.CRITICAL.value,
        confidence=0.72,
        rationale="Potential enterprise-wide blast radius",
        created_by="owner@example.com",
    )
    low = Assumption(
        id=uuid.uuid4(),
        tenant_id=TEST_ORG_ID,
        name="Minor UI copy impact",
        assumption_type="ops",
        impact_level=AssumptionImpact.LOW.value,
        confidence=0.72,
        rationale="No material business impact",
        created_by="owner@example.com",
    )

    assert await service.requires_approval(high) is True
    assert await service.requires_approval(low) is False

    with pytest.raises(ValueError, match="does not require approval"):
        await service.create_approval_request(db=db, assumption=low, requested_by="owner@example.com")
