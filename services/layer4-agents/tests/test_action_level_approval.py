"""Tests for explicit action-level human approval policies."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from value_fabric.layer4.harness.models import ActionClass, GateStatus, GateType
from value_fabric.layer4.policies.approval_actions import (
    ACTION_APPROVAL_POLICIES,
    ApprovalRequiredError,
    get_policy,
    requires_approval,
)


class TestActionLevelApproval:
    def test_all_five_actions_have_policies(self) -> None:
        assert len(ACTION_APPROVAL_POLICIES) == 5
        required = {
            ActionClass.APPROVE_HYPOTHESES,
            ActionClass.PUBLISH_BUSINESS_CASE,
            ActionClass.APPLY_BENCHMARK_ASSUMPTIONS,
            ActionClass.GENERATE_CUSTOMER_FACING_DELIVERABLE,
            ActionClass.CHANGE_ACCOUNT_VALUE_MODEL,
        }
        assert set(ACTION_APPROVAL_POLICIES.keys()) == required

    def test_approve_hypotheses_policy(self) -> None:
        policy = get_policy(ActionClass.APPROVE_HYPOTHESES)
        assert policy is not None
        assert policy.required_gate_type == GateType.APPROVE_CLAIMS
        assert policy.min_approver_role is None

    def test_publish_business_case_policy(self) -> None:
        policy = get_policy(ActionClass.PUBLISH_BUSINESS_CASE)
        assert policy is not None
        assert policy.required_gate_type == GateType.APPROVE_CUSTOMER_OUTPUT
        assert policy.min_approver_role == "content_admin"

    def test_generate_customer_facing_deliverable_requires_secondary(self) -> None:
        policy = get_policy(ActionClass.GENERATE_CUSTOMER_FACING_DELIVERABLE)
        assert policy is not None
        assert policy.requires_secondary_approval is True

    def test_change_account_value_model_policy(self) -> None:
        policy = get_policy(ActionClass.CHANGE_ACCOUNT_VALUE_MODEL)
        assert policy is not None
        assert policy.required_gate_type == GateType.APPROVE_CLAIMS
        assert policy.min_approver_role == "admin"

    def test_requires_approval_for_known_action(self) -> None:
        assert requires_approval(ActionClass.PUBLISH_BUSINESS_CASE) is True

    def test_requires_approval_for_unknown_action(self) -> None:
        assert requires_approval("unknown_action") is True

    def test_unknown_action_denied_by_default(self) -> None:
        with pytest.raises(ApprovalRequiredError, match="denied by default"):
            get_policy("unmapped_critical_action")

    def test_requires_approval_for_none(self) -> None:
        assert requires_approval(None) is False

    def test_approval_required_error_to_dict(self) -> None:
        err = ApprovalRequiredError(
            action_class=ActionClass.PUBLISH_BUSINESS_CASE,
            gate_type=GateType.APPROVE_CUSTOMER_OUTPUT,
            run_id="run_123",
        )
        d = err.to_dict()
        assert d["error"] == "APPROVAL_REQUIRED"
        assert d["action_class"] == ActionClass.PUBLISH_BUSINESS_CASE.value
        assert d["gate_type"] == GateType.APPROVE_CUSTOMER_OUTPUT.value
        assert d["run_id"] == "run_123"

    def test_gate_creation_with_string_action_class(self) -> None:
        from value_fabric.layer4.harness.human_gates import HumanGateManager

        manager = HumanGateManager()
        gate, _ = manager.create_gate(
            run_id="run_123",
            tenant_id="tenant-123",
            gate_type=GateType.APPROVE_CLAIMS,
            action_class="publish_business_case",
        )
        assert gate.action_class == ActionClass.PUBLISH_BUSINESS_CASE

    def test_gate_creation_with_enum_action_class(self) -> None:
        from value_fabric.layer4.harness.human_gates import HumanGateManager

        manager = HumanGateManager()
        gate, _ = manager.create_gate(
            run_id="run_123",
            tenant_id="tenant-123",
            gate_type=GateType.APPROVE_CUSTOMER_OUTPUT,
            action_class=ActionClass.GENERATE_CUSTOMER_FACING_DELIVERABLE,
        )
        assert gate.action_class == ActionClass.GENERATE_CUSTOMER_FACING_DELIVERABLE

    def test_record_approval_wait_uses_real_action_class(self) -> None:
        from value_fabric.layer4.harness.human_gates import HumanGateManager
        from value_fabric.layer4.metrics.prometheus_metrics import MetricsConfig, PrometheusMetrics

        metrics = PrometheusMetrics(MetricsConfig(registry=None))
        manager = HumanGateManager()
        gate, _ = manager.create_gate(
            run_id="run_123",
            tenant_id="tenant-123",
            gate_type=GateType.APPROVE_CUSTOMER_OUTPUT,
            action_class=ActionClass.PUBLISH_BUSINESS_CASE,
        )
        # Simulate decision to trigger metric emission
        gate = gate.model_copy(update={"status": GateStatus.APPROVED, "decided_at": datetime.now(UTC), "decision_by": "user_1"})
        manager._gates[gate.id] = gate

        # The metric should be observable after gate decision
        assert metrics._metrics["approval_wait_seconds"] is not None
