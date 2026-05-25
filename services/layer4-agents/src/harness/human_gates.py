"""
Human Gate Manager — manages approval gates with decision immutability.

Invariants:
  - Decided gates cannot be re-decided.
  - Expired gates cannot be decided.
  - All decisions are traceable (who, when, why).
"""

from __future__ import annotations

from .models import (
    ActionClass,
    GateStatus,
    GateType,
    HarnessTraceEvent,
    HarnessWorkflowType,
    HumanGate,
)


def _record_approval_wait(gate: HumanGate, tenant_id: str) -> None:
    """Emit approval-wait metric if metrics are initialized."""
    try:
        from ..metrics.prometheus_metrics import get_metrics

        metrics = get_metrics()
        if metrics and gate.created_at and gate.decided_at:
            duration = (gate.decided_at - gate.created_at).total_seconds()
            metrics.observe_approval_wait(
                duration=duration,
                gate_type=gate.gate_type.value,
                action_class=(gate.action_class.value if gate.action_class else "unknown"),
                tenant_id=tenant_id,
            )
    except Exception:
        # Metrics are best-effort; do not fail gate decisions.
        pass


class GateDecisionError(ValueError):
    """Raised when a gate decision operation is invalid."""

    pass


class GateExpiredError(GateDecisionError):
    """Raised when operating on an expired gate."""

    pass


class GateNotFoundError(KeyError):
    """Raised when a gate is not found."""

    pass


class HumanGateManager:
    """
    In-memory manager for HumanGate lifecycle.

    Production upgrade: persist to SQL with tenant_id RLS.
    """

    def __init__(self) -> None:
        # Primary store: gate_id -> HumanGate
        self._gates: dict[str, HumanGate] = {}
        # Run index: run_id -> set(gate_id)
        self._run_gates: dict[str, set[str]] = {}

    def create_gate(
        self,
        run_id: str,
        tenant_id: str,
        gate_type: GateType,
        action_class: ActionClass | str | None = None,
    ) -> tuple[HumanGate, HarnessTraceEvent]:
        """Create a new pending human gate.

        Args:
            run_id: Associated workflow run
            tenant_id: Owning tenant
            gate_type: Type of gate
            action_class: Optional high-impact action class (enum or string)
        """
        # Resolve string action_class to enum
        resolved_action: ActionClass | None = None
        if action_class is not None:
            if isinstance(action_class, str):
                try:
                    resolved_action = ActionClass(action_class)
                except ValueError:
                    resolved_action = None
            else:
                resolved_action = action_class

        gate = HumanGate(
            run_id=run_id,
            tenant_id=tenant_id,
            gate_type=gate_type,
            action_class=resolved_action,
        )
        self._gates[gate.id] = gate
        self._run_gates.setdefault(run_id, set()).add(gate.id)

        event = HarnessTraceEvent(
            trace_id=f"trace_gate_{gate.id}",
            run_id=run_id,
            tenant_id=tenant_id,
            workflow_type=HarnessWorkflowType.VALUE_MODEL_GENERATION,
            human_gate_id=gate.id,
            status=None,
            event_type="human_gate_created",
            from_state=None,  # type: ignore[arg-type]
            to_state=None,  # type: ignore[arg-type]
            metadata={"action_class": resolved_action.value if resolved_action else None},
        )
        return gate, event

    def get_gate(self, gate_id: str, tenant_id: str) -> HumanGate:
        """
        Retrieve a gate by ID with tenant scoping.

        Raises:
            GateNotFoundError: if gate missing or tenant mismatch.
        """
        gate = self._gates.get(gate_id)
        if gate is None:
            raise GateNotFoundError(f"Gate '{gate_id}' not found")
        if gate.tenant_id != tenant_id:
            raise GateNotFoundError(
                f"Gate '{gate_id}' not found for tenant '{tenant_id}'"
            )
        return gate

    def list_gates_for_run(self, run_id: str, tenant_id: str) -> list[HumanGate]:
        """List all gates for a run, scoped to tenant."""
        gate_ids = self._run_gates.get(run_id, set())
        gates: list[HumanGate] = []
        for gid in gate_ids:
            gate = self._gates.get(gid)
            if gate is not None and gate.tenant_id == tenant_id:
                gates.append(gate)
        return gates

    def approve_gate(
        self,
        gate_id: str,
        tenant_id: str,
        decision_by: str,
        decision_reason: str | None = None,
    ) -> tuple[HumanGate, HarnessTraceEvent]:
        """
        Approve a pending gate.

        Raises:
            GateDecisionError: if gate already decided.
            GateExpiredError: if gate expired.
            GateNotFoundError: if gate missing or tenant mismatch.
        """
        gate = self._get_gate_mutable(gate_id, tenant_id)

        if gate.status == GateStatus.EXPIRED:
            raise GateExpiredError(f"Gate '{gate_id}' has expired")
        if gate.is_terminal and gate.status != GateStatus.MODIFIED:
            raise GateDecisionError(
                f"Gate '{gate_id}' already decided with status {gate.status.value}"
            )

        updated = gate.decide(
            GateStatus.APPROVED,
            decision_by=decision_by,
            decision_reason=decision_reason,
        )
        self._gates[gate_id] = updated
        _record_approval_wait(updated, tenant_id)

        event = HarnessTraceEvent(
            trace_id=f"trace_gate_{gate_id}",
            run_id=gate.run_id,
            tenant_id=tenant_id,
            workflow_type=HarnessWorkflowType.VALUE_MODEL_GENERATION,
            human_gate_id=gate_id,
            event_type="human_gate_approved",
            metadata={"action_class": updated.action_class.value if updated.action_class else None},
        )
        return updated, event

    def reject_gate(
        self,
        gate_id: str,
        tenant_id: str,
        decision_by: str,
        decision_reason: str | None = None,
    ) -> tuple[HumanGate, HarnessTraceEvent]:
        """Reject a pending gate."""
        gate = self._get_gate_mutable(gate_id, tenant_id)

        if gate.status == GateStatus.EXPIRED:
            raise GateExpiredError(f"Gate '{gate_id}' has expired")
        if gate.is_terminal and gate.status != GateStatus.MODIFIED:
            raise GateDecisionError(
                f"Gate '{gate_id}' already decided with status {gate.status.value}"
            )

        updated = gate.decide(
            GateStatus.REJECTED,
            decision_by=decision_by,
            decision_reason=decision_reason,
        )
        self._gates[gate_id] = updated
        _record_approval_wait(updated, tenant_id)

        event = HarnessTraceEvent(
            trace_id=f"trace_gate_{gate_id}",
            run_id=gate.run_id,
            tenant_id=tenant_id,
            workflow_type=HarnessWorkflowType.VALUE_MODEL_GENERATION,
            human_gate_id=gate_id,
            event_type="human_gate_rejected",
            metadata={"action_class": updated.action_class.value if updated.action_class else None},
        )
        return updated, event

    def modify_gate(
        self,
        gate_id: str,
        tenant_id: str,
        decision_by: str,
        decision_reason: str | None = None,
    ) -> tuple[HumanGate, HarnessTraceEvent]:
        """Mark a gate as modified (decision with changes)."""
        gate = self._get_gate_mutable(gate_id, tenant_id)

        if gate.is_terminal and gate.status != GateStatus.MODIFIED:
            raise GateDecisionError(
                f"Gate '{gate_id}' already decided with status {gate.status.value}"
            )

        updated = gate.decide(
            GateStatus.MODIFIED,
            decision_by=decision_by,
            decision_reason=decision_reason,
        )
        self._gates[gate_id] = updated
        _record_approval_wait(updated, tenant_id)

        event = HarnessTraceEvent(
            trace_id=f"trace_gate_{gate_id}",
            run_id=gate.run_id,
            tenant_id=tenant_id,
            workflow_type=HarnessWorkflowType.VALUE_MODEL_GENERATION,
            human_gate_id=gate_id,
            event_type="human_gate_modified",
            metadata={"action_class": updated.action_class.value if updated.action_class else None},
        )
        return updated, event

    def expire_gate(
        self,
        gate_id: str,
        tenant_id: str,
    ) -> tuple[HumanGate, HarnessTraceEvent]:
        """Expire a pending gate (system-initiated)."""
        gate = self._get_gate_mutable(gate_id, tenant_id)

        if gate.status != GateStatus.PENDING:
            raise GateDecisionError(
                f"Cannot expire gate '{gate_id}' with status {gate.status.value}"
            )

        updated = gate.decide(
            GateStatus.EXPIRED,
            decision_by="system",
            decision_reason="Gate expired due to timeout",
        )
        self._gates[gate_id] = updated

        event = HarnessTraceEvent(
            trace_id=f"trace_gate_{gate_id}",
            run_id=gate.run_id,
            tenant_id=tenant_id,
            workflow_type=HarnessWorkflowType.VALUE_MODEL_GENERATION,
            human_gate_id=gate_id,
            event_type="human_gate_expired",
            metadata={"action_class": updated.action_class.value if updated.action_class else None},
        )
        return updated, event

    def _get_gate_mutable(self, gate_id: str, tenant_id: str) -> HumanGate:
        """Internal: fetch gate for mutation with tenant check."""
        gate = self._gates.get(gate_id)
        if gate is None:
            raise GateNotFoundError(f"Gate '{gate_id}' not found")
        if gate.tenant_id != tenant_id:
            raise GateNotFoundError(
                f"Gate '{gate_id}' not found for tenant '{tenant_id}'"
            )
        return gate
