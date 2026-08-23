from __future__ import annotations

"""
Structured telemetry emitter for the Fabric_4L Harness.

Invariants:
  - Every event includes tenant_id and trace_id.
  - No free-text-only events — all events are structured Pydantic models.
  - Events support audit and replay.
"""
import asyncio
from collections.abc import Callable
from typing import Any

from .models import (
    ClaimValidationResult,
    HarnessCheckpoint,
    HarnessRun,
    HarnessState,
    HarnessTraceEvent,
    HumanGate,
    ToolContract,
    ValidationState,
)

# Event handler type
EventHandler = Callable[[HarnessTraceEvent], None]


class TelemetryEmitter:
    """
    Emits structured trace events for harness operations.

    Handlers can be registered to forward events to logging, metrics, or external systems.
    """

    def __init__(self) -> None:
        self._handlers: list[EventHandler] = []
        self._events: list[HarnessTraceEvent] = []  # In-memory store for testing

    def add_handler(self, handler: EventHandler) -> None:
        """Register an event handler."""
        self._handlers.append(handler)

    def emit_transition_event(
        self,
        run: HarnessRun,
        from_state: HarnessState,
        to_state: HarnessState,
        validation_state: ValidationState | None = None,
    ) -> HarnessTraceEvent:
        """Emit a state transition event."""
        event = HarnessTraceEvent(
            trace_id=run.trace_id,
            run_id=run.id,
            tenant_id=run.tenant_id,
            account_id=run.account_id,
            workflow_type=run.workflow_type,
            from_state=from_state,
            to_state=to_state,
            status=run.status,
            value_pack_id=run.value_pack_id,
            validation_state=validation_state,
            event_type="transition",
        )
        self._dispatch(event)
        return event

    def emit_checkpoint_event(
        self,
        run: HarnessRun,
        checkpoint: HarnessCheckpoint,
    ) -> HarnessTraceEvent:
        """Emit a checkpoint creation event."""
        event = HarnessTraceEvent(
            trace_id=run.trace_id,
            run_id=run.id,
            tenant_id=run.tenant_id,
            account_id=run.account_id,
            workflow_type=run.workflow_type,
            to_state=checkpoint.state_name,
            value_pack_id=run.value_pack_id,
            event_type="checkpoint",
            metadata={
                "checkpoint_id": checkpoint.id,
                "input_hash": checkpoint.input_hash,
                "tool_call_count": len(checkpoint.tool_calls),
            },
        )
        self._dispatch(event)
        return event

    def emit_human_gate_event(
        self,
        run: HarnessRun,
        gate: HumanGate,
    ) -> HarnessTraceEvent:
        """Emit a human gate event."""
        event = HarnessTraceEvent(
            trace_id=run.trace_id,
            run_id=run.id,
            tenant_id=run.tenant_id,
            account_id=run.account_id,
            workflow_type=run.workflow_type,
            human_gate_id=gate.id,
            event_type=f"human_gate_{gate.status.value}",
            metadata={
                "gate_type": gate.gate_type.value,
                "action_class": gate.action_class.value if gate.action_class else None,
                "decision_by": gate.decision_by,
                "decision_reason": gate.decision_reason,
            },
        )
        self._dispatch(event)
        return event

    def emit_validation_event(
        self,
        run: HarnessRun,
        result: ClaimValidationResult,
    ) -> HarnessTraceEvent:
        """Emit a validation result event."""
        event = HarnessTraceEvent(
            trace_id=run.trace_id,
            run_id=run.id,
            tenant_id=run.tenant_id,
            account_id=run.account_id,
            workflow_type=run.workflow_type,
            validation_state=result.validation_state,
            event_type="validation",
            metadata={
                "claim_id": result.claim_id,
                "confidence": result.confidence,
                "trust_score": result.trust_score,
                "validator": result.validator,
                "reason": result.reason,
                "evidence_refs": result.evidence_refs,
            },
        )
        self._dispatch(event)
        return event

    def emit_policy_decision_event(
        self,
        run: HarnessRun,
        decision: str,
        tool_contract: ToolContract | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> HarnessTraceEvent:
        """Emit a policy decision event."""
        event = HarnessTraceEvent(
            trace_id=run.trace_id,
            run_id=run.id,
            tenant_id=run.tenant_id,
            account_id=run.account_id,
            workflow_type=run.workflow_type,
            tool_contract_id=tool_contract.id if tool_contract else None,
            event_type="policy_decision",
            metadata={
                "decision": decision,
                **(metadata or {}),
            },
        )
        self._dispatch(event)
        return event

    def emit(self, event: HarnessTraceEvent) -> None:
        """Public entry point for emitting a pre-built trace event."""
        self._dispatch(event)

    def _dispatch(self, event: HarnessTraceEvent) -> None:
        """Send event to all handlers and in-memory store."""
        self._events.append(event)
        for handler in self._handlers:
            try:
                handler(event)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                # Telemetry handlers must not break workflow.
                # Log but don't raise.
                import logging

                logging.getLogger(__name__).warning(
                    f"Telemetry handler failed: {exc}",
                    exc_info=True,
                )

    def get_events(
        self,
        run_id: str | None = None,
        tenant_id: str | None = None,
    ) -> list[HarnessTraceEvent]:
        """Retrieve emitted events, optionally filtered."""
        events = list(self._events)
        if run_id is not None:
            events = [e for e in events if e.run_id == run_id]
        if tenant_id is not None:
            events = [e for e in events if e.tenant_id == tenant_id]
        return events

    def clear(self) -> None:
        """Clear in-memory events (testing only)."""
        self._events.clear()
