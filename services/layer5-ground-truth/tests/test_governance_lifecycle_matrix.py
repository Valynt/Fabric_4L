from __future__ import annotations

"""Lifecycle matrix and approval-gating regression tests for governance objects."""


import uuid
from datetime import UTC, datetime

import pytest

from layer5_ground_truth.models.approval_workflow import (
    ApprovalRequest,
    ApprovalStatus,
    ApprovalWorkflow,
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
    if from_status == ApprovalStatus.PENDING and to_status == ApprovalStatus.APPROVED:
        db.add(
            ApprovalWorkflow(
                id=uuid.uuid4(),
                tenant_id=TEST_ORG_ID,
                entity_type=EntityType.ASSUMPTION.value,
                workflow_name="Assumption lifecycle matrix approval",
                required_approval_levels=1,
                require_evidence=False,
                require_justification=False,
                approver_roles=["reviewer"],
                level_definitions=[{"level": 1, "quorum": 1}],
                default_level_quorum=1,
                is_active=True,
                created_by="owner@example.com",
            )
        )
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
        slug="strategic-dependency-risk",
        assumption_type="risk",
        description="Potential enterprise-wide blast radius",
        value={"risk": "strategic_dependency"},
        value_type="string",
        impact_level=AssumptionImpact.CRITICAL.value,
        created_by="owner@example.com",
    )
    low = Assumption(
        id=uuid.uuid4(),
        tenant_id=TEST_ORG_ID,
        name="Minor UI copy impact",
        slug="minor-ui-copy-impact",
        assumption_type="ops",
        description="No material business impact",
        value={"impact": "minor_copy"},
        value_type="string",
        impact_level=AssumptionImpact.LOW.value,
        created_by="owner@example.com",
    )

    assert await service.requires_approval(high) is True
    assert await service.requires_approval(low) is False

    with pytest.raises(ValueError, match="does not require approval"):
        await service.create_approval_request(db=db, assumption=low, requested_by="owner@example.com")
