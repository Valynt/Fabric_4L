"""
Harness Registry — coordinates runs, checkpoints, gates, and validation.

This is the top-level orchestrator that ties together all harness components.
It does not replace individual layers but governs how they interact.
"""

from __future__ import annotations

from typing import Any

from .checkpoints import CheckpointManager
from .human_gates import HumanGateManager
from .models import (
    ActionClass,
    ClaimValidationResult,
    GateStatus,
    GateType,
    HarnessCheckpoint,
    HarnessRun,
    HarnessRunStatus,
    HarnessState,
    HarnessTraceEvent,
    HarnessWorkflowType,
    HumanGate,
    InitiatedBy,
    ToolContract,
    ValidationState,
)
from .state_machine import (
    StateMachine,
)
from .telemetry import TelemetryEmitter
from .tool_contracts import ToolContractRegistry
from .validation_hooks import ClaimValidationRequest, ValidationHook


class HarnessRegistryError(RuntimeError):
    """Raised when a registry operation fails."""

    pass


class RunNotFoundError(KeyError):
    """Raised when a run does not exist or is not visible to the requesting tenant.

    Subclasses KeyError so route handlers that catch KeyError → 404 work
    correctly without modification, parallel to GateNotFoundError(KeyError).
    """

    pass


class HarnessRegistry:
    """
    Top-level harness orchestrator.

    Coordinates:
      - Run lifecycle
      - State transitions
      - Checkpoint management
      - Human gates
      - Tool contract enforcement
      - Validation hooks
      - Telemetry emission
    """

    def __init__(
        self,
        state_machine: StateMachine | None = None,
        tool_registry: ToolContractRegistry | None = None,
        gate_manager: HumanGateManager | None = None,
        checkpoint_manager: CheckpointManager | None = None,
        telemetry: TelemetryEmitter | None = None,
        validation_hook: ValidationHook | None = None,
    ) -> None:
        self._sm = state_machine or StateMachine()
        self._tools = tool_registry or ToolContractRegistry()
        self._gates = gate_manager or HumanGateManager()
        self._checkpoints = checkpoint_manager or CheckpointManager()
        self._telemetry = telemetry or TelemetryEmitter()
        self._validation = validation_hook or ValidationHook()

        # Run store
        self._runs: dict[str, HarnessRun] = {}

    # ---- Run Lifecycle ----

    def create_run(
        self,
        tenant_id: str,
        workflow_type: HarnessWorkflowType,
        initiated_by: InitiatedBy,
        account_id: str | None = None,
        value_pack_id: str | None = None,
    ) -> HarnessRun:
        """Create a new harness run."""
        run = HarnessRun(
            tenant_id=tenant_id,
            account_id=account_id,
            workflow_type=workflow_type,
            initiated_by=initiated_by,
            value_pack_id=value_pack_id,
        )
        self._runs[run.id] = run

        # Emit creation event
        self._telemetry.emit_transition_event(
            run=run,
            from_state=None,  # type: ignore[arg-type]
            to_state=HarnessState.INIT,
        )

        return run

    def get_run(self, run_id: str, tenant_id: str) -> HarnessRun:
        """Get a run with tenant scoping."""
        run = self._runs.get(run_id)
        if run is None:
            raise RunNotFoundError(f"Run '{run_id}' not found")
        if run.tenant_id != tenant_id:
            # Return the same error shape as a missing run to avoid leaking
            # the existence of runs belonging to other tenants.
            raise RunNotFoundError(
                f"Run '{run_id}' not found for tenant '{tenant_id}'"
            )
        return run

    # ---- State Transitions ----

    def transition(
        self,
        run_id: str,
        tenant_id: str,
        to_state: HarnessState,
        validation_results: list[ClaimValidationResult] | None = None,
        human_override: bool = False,
        state_payload: dict[str, Any] | None = None,
    ) -> tuple[HarnessRun, HarnessTraceEvent]:
        """
        Execute a state transition.

        Returns:
            Tuple of (updated_run, trace_event).
        """
        run = self.get_run(run_id, tenant_id)

        # Derive validation state from results
        validation_state: ValidationState | None = None
        if validation_results is not None:
            # Aggregate: if any failed, use failed; if any need review, use needs_review
            states = [vr.validation_state for vr in validation_results]
            if ValidationState.FAILED in states:
                validation_state = ValidationState.FAILED
            elif ValidationState.INSUFFICIENT_EVIDENCE in states:
                validation_state = ValidationState.INSUFFICIENT_EVIDENCE
            elif ValidationState.NEEDS_REVIEW in states:
                validation_state = ValidationState.NEEDS_REVIEW
            elif states and all(s == ValidationState.PASSED for s in states):
                validation_state = ValidationState.PASSED

        updated, event = self._sm.transition(
            run=run,
            to_state=to_state,
            validation_state=validation_state,
            human_override=human_override,
        )

        # Emit telemetry directly (avoids mutating injected StateMachine hooks)
        self._telemetry.emit_transition_event(
            run=updated,
            from_state=run.current_state,
            to_state=to_state,
        )

        # Persist updated run
        self._runs[run_id] = updated

        # Checkpoint
        if state_payload is not None:
            self._checkpoints.create_checkpoint(
                run_id=run_id,
                tenant_id=tenant_id,
                state_name=to_state,
                state_payload=state_payload,
            )

        return updated, event

    # ---- Human Gates ----

    def create_human_gate(
        self,
        run_id: str,
        tenant_id: str,
        gate_type: GateType,
        action_class: ActionClass | None = None,
    ) -> HumanGate:
        """Create a human gate for a run."""
        run = self.get_run(run_id, tenant_id)
        gate, event = self._gates.create_gate(run_id, tenant_id, gate_type, action_class)
        event = event.model_copy(
            update={
                "trace_id": run.trace_id,
                "workflow_type": run.workflow_type,
            }
        )
        self._telemetry._dispatch(event)
        return gate

    def decide_gate(
        self,
        gate_id: str,
        tenant_id: str,
        decision: GateStatus,
        decision_by: str,
        decision_reason: str | None = None,
    ) -> HumanGate:
        """Make a decision on a human gate."""
        if decision == GateStatus.APPROVED:
            gate, event = self._gates.approve_gate(
                gate_id, tenant_id, decision_by, decision_reason
            )
        elif decision == GateStatus.REJECTED:
            gate, event = self._gates.reject_gate(
                gate_id, tenant_id, decision_by, decision_reason
            )
        elif decision == GateStatus.MODIFIED:
            gate, event = self._gates.modify_gate(
                gate_id, tenant_id, decision_by, decision_reason
            )
        elif decision == GateStatus.EXPIRED:
            gate, event = self._gates.expire_gate(gate_id, tenant_id)
        else:
            raise HarnessRegistryError(f"Invalid gate decision: {decision}")

        # Enrich event with run trace
        run = self._runs.get(gate.run_id)
        if run is not None:
            event = event.model_copy(
                update={
                    "trace_id": run.trace_id,
                    "workflow_type": run.workflow_type,
                }
            )
            self._telemetry._dispatch(event)

        return gate

    def get_gate(self, gate_id: str, tenant_id: str) -> HumanGate:
        """Get a gate with tenant scoping."""
        return self._gates.get_gate(gate_id, tenant_id)

    def list_gates_for_run(self, run_id: str, tenant_id: str) -> list[HumanGate]:
        """List gates for a run."""
        return self._gates.list_gates_for_run(run_id, tenant_id)

    # ---- Validation ----

    async def validate_claims(
        self,
        tenant_id: str,
        requests: list[ClaimValidationRequest],
        run_id: str | None = None,
    ) -> list[ClaimValidationResult]:
        """Validate claims through the L5 hook.

        run_id is accepted for interface parity with SqlHarnessRegistry but
        is not persisted in the in-memory implementation (tests only).

        Raises HarnessRegistryError if any request carries a tenant_id that
        does not match the authenticated tenant_id, preventing cross-tenant
        claim submission.
        """
        mismatched = [r.claim_id for r in requests if r.tenant_id != tenant_id]
        if mismatched:
            raise HarnessRegistryError(
                f"tenant_id mismatch in validate_claims: "
                f"claims {mismatched} do not belong to tenant '{tenant_id}'"
            )
        return await self._validation.validate_claims(requests)

    # ---- Checkpoints ----

    def get_checkpoints(self, run_id: str, tenant_id: str) -> list[HarnessCheckpoint]:
        """List checkpoints for a run."""
        return self._checkpoints.list_checkpoints_for_run(run_id, tenant_id)

    # ---- Tool Registry ----

    def register_tool(self, tool: ToolContract, tenant_id: str) -> ToolContract:
        """Register a tool contract."""
        return self._tools.register_tool(tool, tenant_id)

    def get_tool(self, tool_id: str, tenant_id: str) -> ToolContract:
        """Get a tool with tenant scoping."""
        return self._tools.get_tool(tool_id, tenant_id)

    # ---- Queries ----

    def list_runs(
        self,
        tenant_id: str | None = None,
        status: HarnessRunStatus | None = None,
    ) -> list[HarnessRun]:
        """List runs with optional filtering."""
        runs = list(self._runs.values())
        if tenant_id is not None:
            runs = [r for r in runs if r.tenant_id == tenant_id]
        if status is not None:
            runs = [r for r in runs if r.status == status]
        return runs

    @property
    def telemetry(self) -> TelemetryEmitter:
        return self._telemetry

    @property
    def validation_available(self) -> bool:
        """Sync property — returns True only if primary validator is configured.
        Use await registry._validation.is_available() for a live health check."""
        return self._validation._primary is not None
