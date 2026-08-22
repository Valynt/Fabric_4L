from __future__ import annotations

from ..harness.models import GateStatus, GateType, HumanGate
from ..harness.policies import PolicyViolationError, enforce_action_approval


def ensure_controller_accepts_execution(*, is_shutdown: bool, error_cls: type[Exception]) -> None:
    if is_shutdown:
        raise error_cls("OrchestrationController is shutting down")


def validate_workflow_start_invariants(
    *,
    workflow_type: str,
    supported_types: set[str] | frozenset[str] | list[str],
    tenant_id: str | None,
    checkpoint_saver: object,
    error_cls: type[Exception],
) -> None:
    """Validate common start invariants (type, tenant context, checkpoint saver in prod)."""
    if workflow_type not in supported_types:
        raise error_cls(
            f"Unknown workflow type: {workflow_type!r}. "
            f"Supported types: {', '.join(sorted(supported_types))}"
        )

    tenant_id_str = str(tenant_id) if tenant_id else ""
    if not tenant_id_str or not tenant_id_str.strip():
        raise error_cls("tenant_id is required: workflow start rejected")

    if checkpoint_saver is None:
        import os

        from value_fabric.shared.security.config import is_production_like_environment

        environment = os.getenv("ENVIRONMENT") or os.getenv("ENV") or os.getenv("APP_ENV")
        if is_production_like_environment(environment):
            raise error_cls("Production workflow execution requires a durable checkpoint saver")


def parse_and_enforce_approval_gate(
    *,
    workflow_id: str | None,
    input_data: dict[str, object],
    tenant_id: str | None,
    error_cls: type[Exception],
) -> object:
    """Parse HumanGate definition and enforce action approval policy."""
    action_class = input_data.get("action_class")
    gate_data = input_data.get("approval_gate")
    gate: HumanGate | None = None
    if isinstance(gate_data, dict):
        gate = HumanGate(
            id=str(gate_data["id"]),
            run_id=str(gate_data.get("run_id") or ""),
            tenant_id=tenant_id,
            gate_type=GateType(gate_data["gate_type"]),
            status=GateStatus(gate_data.get("status", GateStatus.APPROVED.value)),
        )
    try:
        return enforce_action_approval(
            run_id=workflow_id or "pending_workflow_id",
            action_class=action_class if isinstance(action_class, str) else None,
            gate=gate,
        )
    except (ValueError, PolicyViolationError) as exc:
        raise error_cls(f"{type(exc).__name__}: workflow_execution_failed") from exc

