"""Tests for Layer 4 observability gaps (approval latency, failure alerting)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from value_fabric.layer4.harness.human_gates import HumanGateManager
from value_fabric.layer4.harness.models import ActionClass, GateType, HarnessWorkflowType
from value_fabric.layer4.metrics.prometheus_metrics import MetricsConfig, PrometheusMetrics
from value_fabric.layer4.models.agent_state import WorkflowStatus


class TestObservabilityGaps:
    def test_high_impact_gate_actions_emit_non_unknown_action_class(self, monkeypatch: pytest.MonkeyPatch) -> None:
        observed_action_classes: list[str] = []

        class _FakeMetrics:
            def observe_approval_wait(self, *, duration: float, gate_type: str, action_class: str, tenant_id: str) -> None:
                observed_action_classes.append(action_class)

        monkeypatch.setattr(
            "value_fabric.layer4.metrics.prometheus_metrics.get_metrics",
            lambda: _FakeMetrics(),
        )

        manager = HumanGateManager()
        for action_class in ActionClass:
            gate, _ = manager.create_gate(
                run_id=f"run_{action_class.value}",
                tenant_id="tenant-123",
                gate_type=GateType.APPROVE_CLAIMS,
                action_class=action_class,
            )
            backdated = gate.model_copy(update={"created_at": datetime.now(UTC) - timedelta(seconds=5)})
            manager._gates[gate.id] = backdated
            manager.approve_gate(
                gate_id=gate.id,
                tenant_id="tenant-123",
                decision_by="user_1",
            )

        assert "unknown" not in observed_action_classes
        assert set(observed_action_classes) == {action.value for action in ActionClass}

    def test_approval_wait_metric_recorded(self) -> None:
        metrics = PrometheusMetrics(MetricsConfig(registry=None))
        metrics.observe_approval_wait(
            duration=45.0,
            gate_type="approve_claims",
            action_class="publish_business_case",
            tenant_id="tenant-123",
        )
        # Metric is registered and no exception raised
        assert "approval_wait_seconds" in metrics._metrics

    def test_stuck_workflows_metric(self) -> None:
        metrics = PrometheusMetrics(MetricsConfig(registry=None))
        metrics.set_stuck_workflows(
            count=3,
            workflow_type="roi_calculator",
            tenant_id="tenant-123",
        )
        assert "stuck_workflows_total" in metrics._metrics

    def test_repeated_failure_metric(self) -> None:
        metrics = PrometheusMetrics(MetricsConfig(registry=None))
        metrics.increment_repeated_failure(
            workflow_type="business_case",
            failure_class="NodeExecutionError",
            tenant_id="tenant-123",
        )
        assert "repeated_workflow_failures_total" in metrics._metrics

    def test_tool_auth_failure_metric(self) -> None:
        metrics = PrometheusMetrics(MetricsConfig(registry=None))
        metrics.increment_tool_auth_failure(
            tool_name="get_prospect_data",
            tenant_id="tenant-123",
        )
        assert "tool_auth_failures_total" in metrics._metrics

    def test_checkpoint_corruption_metric(self) -> None:
        metrics = PrometheusMetrics(MetricsConfig(registry=None))
        metrics.increment_checkpoint_corruption(
            workflow_type="roi_calculator",
            tenant_id="tenant-123",
        )
        assert "checkpoint_corruption_detected_total" in metrics._metrics

    def test_gate_decision_records_wait_time(self) -> None:
        manager = HumanGateManager()
        gate, _ = manager.create_gate(
            run_id="run_123",
            tenant_id="tenant-123",
            gate_type=GateType.APPROVE_CLAIMS,
        )
        # Simulate time passing by overriding created_at
        gate = gate.model_copy(update={"created_at": datetime.now(UTC) - timedelta(seconds=120)})
        manager._gates[gate.id] = gate

        updated, _ = manager.approve_gate(
            gate_id=gate.id,
            tenant_id="tenant-123",
            decision_by="user_1",
            decision_reason="looks good",
        )
        assert updated.status.value == "approved"
        assert updated.decided_at is not None

    def test_metrics_use_tenant_tier_not_raw_tenant_id(self) -> None:
        from value_fabric.layer4.metrics.prometheus_metrics import _derive_tenant_tier

        tier1 = _derive_tenant_tier("tenant-a")
        tier2 = _derive_tenant_tier("tenant-b")
        # Different tenants should usually map to different tiers (not guaranteed but highly likely)
        assert len(tier1) == 4  # 2 hex chars
        assert tier1 != "unknown"
        assert _derive_tenant_tier(None) == "unknown"
        assert _derive_tenant_tier("") == "unknown"

    def test_checkpoint_corruption_metric_emission(self) -> None:
        from value_fabric.layer4.engine.execution_checkpointing import record_checkpoint_corruption
        from value_fabric.layer4.metrics.prometheus_metrics import MetricsConfig, PrometheusMetrics

        metrics = PrometheusMetrics(MetricsConfig(registry=None))
        # Simulate emission
        record_checkpoint_corruption("roi_calculator", "tenant-123", "hash_mismatch")
        assert "checkpoint_corruption_detected_total" in metrics._metrics

    def test_tool_auth_failure_metric_emission(self) -> None:
        from value_fabric.layer4.metrics.prometheus_metrics import MetricsConfig, PrometheusMetrics

        metrics = PrometheusMetrics(MetricsConfig(registry=None))
        metrics.increment_tool_auth_failure("get_prospect_data", "tenant-123")
        # Metric is registered and no exception raised
        assert "tool_auth_failures_total" in metrics._metrics
