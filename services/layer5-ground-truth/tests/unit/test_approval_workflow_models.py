"""
Unit tests for Approval Workflow models.

Tests for ApprovalRequest, ApprovalDecision, and ApprovalWorkflow models.
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


class TestApprovalRequest:
    def test_create_approval_request(self):
        """Should create an approval request with required fields."""
        request = ApprovalRequest(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            entity_type=EntityType.FORMULA.value,
            entity_id=uuid.uuid4(),
            entity_version="1.0.0",
            status=ApprovalStatus.DRAFT.value,
            requested_by="user@example.com",
            requested_at=datetime.now(UTC),
        )
        assert request.status == ApprovalStatus.DRAFT.value
        assert request.entity_type == EntityType.FORMULA.value

    def test_approval_request_enum_values(self):
        """ApprovalStatus enum should have expected values."""
        assert {s.value for s in ApprovalStatus} == {
            "draft",
            "pending",
            "approved",
            "rejected",
            "deprecated",
            "archived",
        }

    def test_entity_type_enum_values(self):
        """EntityType enum should have expected values."""
        assert {s.value for s in EntityType} == {
            "formula",
            "benchmark",
            "policy",
            "assumption",
        }


class TestApprovalDecision:
    def test_create_approval_decision(self):
        """Should create an approval decision with required fields."""
        decision = ApprovalDecision(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            approval_request_id=uuid.uuid4(),
            decision_type=ApprovalDecisionType.APPROVE.value,
            decided_by="approver@example.com",
            decided_at=datetime.now(UTC),
            approval_level=1,
        )
        assert decision.decision_type == ApprovalDecisionType.APPROVE.value
        assert decision.approval_level == 1

    def test_approval_decision_enum_values(self):
        """ApprovalDecisionType enum should have expected values."""
        assert {s.value for s in ApprovalDecisionType} == {
            "approve",
            "reject",
            "request_changes",
            "escalate",
        }


class TestApprovalWorkflow:
    def test_create_approval_workflow(self):
        """Should create an approval workflow with required fields."""
        workflow = ApprovalWorkflow(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            entity_type=EntityType.FORMULA.value,
            workflow_name="Formula Approval",
            description="Approval workflow for formulas",
            required_approval_levels=1,
            approver_roles=["admin", "reviewer"],
            is_active=True,
            version="1.0",
        )
        assert workflow.entity_type == EntityType.FORMULA.value
        assert workflow.required_approval_levels == 1
        assert workflow.is_active is True


class TestApprovalRequestRelationships:
    def test_approval_request_has_decisions(self):
        """ApprovalRequest should have decisions relationship."""
        request = ApprovalRequest(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            entity_type=EntityType.ASSUMPTION.value,
            entity_id=uuid.uuid4(),
            status=ApprovalStatus.PENDING.value,
            requested_by="user@example.com",
        )
        # Relationship is defined in the model
        assert hasattr(request, "decisions")


class TestApprovalDecisionRelationships:
    def test_approval_decision_has_approval_request(self):
        """ApprovalDecision should have approval_request relationship."""
        decision = ApprovalDecision(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            approval_request_id=uuid.uuid4(),
            decision_type=ApprovalDecisionType.REJECT.value,
            decided_by="reviewer@example.com",
            approval_level=1,
        )
        # Relationship is defined in the model
        assert hasattr(decision, "approval_request")
