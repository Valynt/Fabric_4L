"""SQL-backed drop-in replacements for the five harness in-memory stores.

Each class satisfies the same interface as its in-memory counterpart so
callers (including HarnessRegistry) need no conditional logic. The only
difference is that state survives process restarts.

Invariants preserved from in-memory stores:
  - Same method signatures and error types.
  - SqlTelemetryEmitter._dispatch() never raises even on DB failure.
  - SqlToolContractRegistry enforces high-risk approval policy at registration.
  - Cross-tenant access raises the same domain errors.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from harness.checkpoints import CheckpointError
from harness.db_models import ClaimValidationResultRow
from harness.human_gates import GateDecisionError, GateExpiredError
from harness.models import (
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
    ToolCallRef,
    ToolContract,
    ToolRiskLevel,
    ValidationState,
)
from harness.repositories import (
    CheckpointRepository,
    HarnessRunRepository,
    HumanGateRepository,
    ToolContractRepository,
    TraceEventRepository,
)
from harness.telemetry import EventHandler

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# SqlHumanGateManager
# ---------------------------------------------------------------------------


class SqlHumanGateManager:
    """SQL-backed HumanGate lifecycle manager.

    Drop-in replacement for HumanGateManager. Same method signatures,
    same error types. Delegates to HumanGateRepository.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._repo = HumanGateRepository(session)

    async def create_gate(
        self,
        run_id: str,
        tenant_id: str,
        gate_type: GateType,
    ) -> tuple[HumanGate, HarnessTraceEvent]:
        gate = HumanGate(
            run_id=run_id,
            tenant_id=tenant_id,
            gate_type=gate_type,
        )
        await self._repo.create(gate)

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
        )
        return gate, event

    async def get_gate(self, gate_id: str, tenant_id: str) -> HumanGate:
        return await self._repo.get(gate_id, tenant_id)

    async def list_gates_for_run(self, run_id: str, tenant_id: str) -> list[HumanGate]:
        return await self._repo.list_for_run(run_id, tenant_id)

    async def approve_gate(
        self,
        gate_id: str,
        tenant_id: str,
        decision_by: str,
        decision_reason: str | None = None,
    ) -> tuple[HumanGate, HarnessTraceEvent]:
        gate = await self._repo.get(gate_id, tenant_id)
        if gate.status == GateStatus.EXPIRED:
            raise GateExpiredError(f"Gate '{gate_id}' has expired")
        if gate.is_terminal and gate.status != GateStatus.MODIFIED:
            raise GateDecisionError(
                f"Gate '{gate_id}' already decided with status {gate.status.value}"
            )
        updated = gate.decide(GateStatus.APPROVED, decision_by=decision_by, decision_reason=decision_reason)
        await self._repo.update(updated)
        event = HarnessTraceEvent(
            trace_id=f"trace_gate_{gate_id}",
            run_id=gate.run_id,
            tenant_id=tenant_id,
            workflow_type=HarnessWorkflowType.VALUE_MODEL_GENERATION,
            human_gate_id=gate_id,
            event_type="human_gate_approved",
        )
        return updated, event

    async def reject_gate(
        self,
        gate_id: str,
        tenant_id: str,
        decision_by: str,
        decision_reason: str | None = None,
    ) -> tuple[HumanGate, HarnessTraceEvent]:
        gate = await self._repo.get(gate_id, tenant_id)
        if gate.status == GateStatus.EXPIRED:
            raise GateExpiredError(f"Gate '{gate_id}' has expired")
        if gate.is_terminal and gate.status != GateStatus.MODIFIED:
            raise GateDecisionError(
                f"Gate '{gate_id}' already decided with status {gate.status.value}"
            )
        updated = gate.decide(GateStatus.REJECTED, decision_by=decision_by, decision_reason=decision_reason)
        await self._repo.update(updated)
        event = HarnessTraceEvent(
            trace_id=f"trace_gate_{gate_id}",
            run_id=gate.run_id,
            tenant_id=tenant_id,
            workflow_type=HarnessWorkflowType.VALUE_MODEL_GENERATION,
            human_gate_id=gate_id,
            event_type="human_gate_rejected",
        )
        return updated, event

    async def modify_gate(
        self,
        gate_id: str,
        tenant_id: str,
        decision_by: str,
        decision_reason: str | None = None,
    ) -> tuple[HumanGate, HarnessTraceEvent]:
        gate = await self._repo.get(gate_id, tenant_id)
        if gate.is_terminal and gate.status != GateStatus.MODIFIED:
            raise GateDecisionError(
                f"Gate '{gate_id}' already decided with status {gate.status.value}"
            )
        updated = gate.decide(GateStatus.MODIFIED, decision_by=decision_by, decision_reason=decision_reason)
        await self._repo.update(updated)
        event = HarnessTraceEvent(
            trace_id=f"trace_gate_{gate_id}",
            run_id=gate.run_id,
            tenant_id=tenant_id,
            workflow_type=HarnessWorkflowType.VALUE_MODEL_GENERATION,
            human_gate_id=gate_id,
            event_type="human_gate_modified",
        )
        return updated, event

    async def expire_gate(
        self,
        gate_id: str,
        tenant_id: str,
    ) -> tuple[HumanGate, HarnessTraceEvent]:
        gate = await self._repo.get(gate_id, tenant_id)
        if gate.status != GateStatus.PENDING:
            raise GateDecisionError(
                f"Cannot expire gate '{gate_id}' with status {gate.status.value}"
            )
        updated = gate.decide(GateStatus.EXPIRED, decision_by="system", decision_reason="Gate expired due to timeout")
        await self._repo.update(updated)
        event = HarnessTraceEvent(
            trace_id=f"trace_gate_{gate_id}",
            run_id=gate.run_id,
            tenant_id=tenant_id,
            workflow_type=HarnessWorkflowType.VALUE_MODEL_GENERATION,
            human_gate_id=gate_id,
            event_type="human_gate_expired",
        )
        return updated, event


# ---------------------------------------------------------------------------
# SqlCheckpointManager
# ---------------------------------------------------------------------------


class SqlCheckpointManager:
    """SQL-backed checkpoint manager.

    Drop-in replacement for CheckpointManager. Deterministic hashing is
    preserved — the hash is computed before storage, not by the DB.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._repo = CheckpointRepository(session)

    async def create_checkpoint(
        self,
        run_id: str,
        tenant_id: str,
        state_name: HarnessState,
        state_payload: dict[str, Any],
        tool_calls: list[ToolCallRef] | None = None,
        output_hash: str | None = None,
    ) -> HarnessCheckpoint:
        if not run_id or not run_id.strip():
            raise CheckpointError("run_id is required and must be non-empty")
        if not tenant_id or not tenant_id.strip():
            raise CheckpointError("tenant_id is required and must be non-empty")

        tool_calls = tool_calls or []
        input_hash = HarnessCheckpoint.compute_input_hash(
            run_id=run_id,
            tenant_id=tenant_id,
            state_name=state_name,
            state_payload=state_payload,
            tool_calls=tool_calls,
        )
        checkpoint = HarnessCheckpoint(
            run_id=run_id,
            tenant_id=tenant_id,
            state_name=state_name,
            state_payload=state_payload,
            input_hash=input_hash,
            output_hash=output_hash,
            tool_calls=tool_calls,
        )
        return await self._repo.create(checkpoint)

    async def get_checkpoint(
        self, checkpoint_id: str, run_id: str, tenant_id: str
    ) -> HarnessCheckpoint:
        return await self._repo.get(checkpoint_id, run_id, tenant_id)

    async def list_checkpoints_for_run(
        self, run_id: str, tenant_id: str
    ) -> list[HarnessCheckpoint]:
        return await self._repo.list_for_run(run_id, tenant_id)

    async def get_latest_checkpoint(
        self, run_id: str, tenant_id: str
    ) -> HarnessCheckpoint | None:
        return await self._repo.get_latest(run_id, tenant_id)

    def verify_payload_unchanged(
        self,
        checkpoint: HarnessCheckpoint,
        state_payload: dict[str, Any],
    ) -> bool:
        current_hash = HarnessCheckpoint.compute_input_hash(
            run_id=checkpoint.run_id,
            tenant_id=checkpoint.tenant_id,
            state_name=checkpoint.state_name,
            state_payload=state_payload,
            tool_calls=list(checkpoint.tool_calls),
        )
        return current_hash == checkpoint.input_hash


# ---------------------------------------------------------------------------
# SqlToolContractRegistry
# ---------------------------------------------------------------------------


class SqlToolContractRegistry:
    """SQL-backed tool contract registry.

    Drop-in replacement for ToolContractRegistry. Enforces the same
    registration invariants (high-risk needs approval_policy_id, no
    duplicate tool_id per tenant).
    """

    def __init__(self, session: AsyncSession) -> None:
        self._repo = ToolContractRepository(session)

    async def register_tool(self, tool: ToolContract, tenant_id: str) -> ToolContract:
        return await self._repo.register(tool, tenant_id)

    async def get_tool(self, tool_id: str, tenant_id: str | None = None) -> ToolContract:
        from harness.tool_contracts import ToolNotFoundError

        if tenant_id is None:
            raise ToolNotFoundError(
                f"Tool '{tool_id}' lookup requires tenant_id in SQL registry"
            )
        return await self._repo.get(tool_id, tenant_id)

    async def list_tools(
        self,
        tenant_id: str | None = None,
        layer: str | None = None,
        risk_level: ToolRiskLevel | None = None,
    ) -> list[ToolContract]:
        from harness.tool_contracts import ToolNotFoundError

        if tenant_id is None:
            raise ToolNotFoundError("list_tools requires tenant_id in SQL registry")
        return await self._repo.list(tenant_id, layer=layer, risk_level=risk_level)

    async def validate_tool_invocation_policy(
        self,
        tool_id: str,
        tenant_id: str,
        has_approval: bool = False,
        account_context_present: bool = False,
    ) -> ToolContract:
        from harness.policies import evaluate_tool_invocation_policy

        tool = await self._repo.get(tool_id, tenant_id)
        evaluate_tool_invocation_policy(
            tool=tool,
            has_approval=has_approval,
            tenant_context_present=True,
            account_context_present=account_context_present,
        )
        return tool

    async def unregister_tool(self, tool_id: str, tenant_id: str) -> None:
        await self._repo.delete(tool_id, tenant_id)


# ---------------------------------------------------------------------------
# SqlClaimValidationStore
# ---------------------------------------------------------------------------


class SqlClaimValidationStore:
    """Persists and retrieves ClaimValidationResult rows for a harness run.

    Separate from ValidationHook — this store handles the write-through
    after validation completes and the read path for the GET /validation
    endpoint. ValidationHook continues to own the live L5 query logic.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save_results(
        self,
        run_id: str,
        results: list[ClaimValidationResult],
    ) -> None:
        """Persist a batch of validation results for a run.

        Idempotent on the claim_id+run_id pair: existing rows for the same
        claim are deleted before inserting the new result so re-validation
        always reflects the latest state.

        Uses core INSERT (not ORM add) to avoid flush-within-flush issues
        when called from within an active session transaction.
        """
        from sqlalchemy import delete, insert

        if not results:
            return

        claim_ids = [r.claim_id for r in results]
        await self._session.execute(
            delete(ClaimValidationResultRow).where(
                ClaimValidationResultRow.run_id == run_id,
                ClaimValidationResultRow.claim_id.in_(claim_ids),
            )
        )

        rows = [
            {
                "id": r.id,
                "run_id": run_id,
                "tenant_id": r.tenant_id,
                "claim_id": r.claim_id,
                "validation_state": r.validation_state.value,
                "evidence_refs": r.evidence_refs,
                "confidence": r.confidence,
                "trust_score": r.trust_score,
                "validator": r.validator,
                "reason": r.reason,
                "created_at": r.created_at,
            }
            for r in results
        ]
        await self._session.execute(insert(ClaimValidationResultRow), rows)

    async def get_results_for_run(
        self,
        run_id: str,
        tenant_id: str,
    ) -> list[ClaimValidationResult]:
        """Return all stored validation results for a run, tenant-scoped."""
        from sqlalchemy import select

        stmt = (
            select(ClaimValidationResultRow)
            .where(
                ClaimValidationResultRow.run_id == run_id,
                ClaimValidationResultRow.tenant_id == tenant_id,
            )
            .order_by(ClaimValidationResultRow.created_at)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [self._to_domain(row) for row in rows]

    @staticmethod
    def _to_domain(row: ClaimValidationResultRow) -> ClaimValidationResult:
        return ClaimValidationResult(
            id=row.id,
            tenant_id=row.tenant_id,
            claim_id=row.claim_id,
            validation_state=ValidationState(row.validation_state),
            evidence_refs=row.evidence_refs or [],
            confidence=row.confidence,
            trust_score=row.trust_score,
            validator=row.validator,  # type: ignore[arg-type]
            reason=row.reason or "",
            created_at=row.created_at,
        )


# ---------------------------------------------------------------------------
# SqlTelemetryEmitter
# ---------------------------------------------------------------------------


class SqlTelemetryEmitter:
    """SQL-backed telemetry emitter.

    Drop-in replacement for TelemetryEmitter. Events are persisted to DB
    AND dispatched to in-memory handlers. DB write failure is caught and
    logged — it must never break the workflow (same invariant as in-memory).
    """

    def __init__(self, session: AsyncSession) -> None:
        self._repo = TraceEventRepository(session)
        self._handlers: list[EventHandler] = []
        self._events: list[HarnessTraceEvent] = []

    def add_handler(self, handler: EventHandler) -> None:
        self._handlers.append(handler)

    def emit_transition_event(
        self,
        run: HarnessRun,
        from_state: HarnessState,
        to_state: HarnessState,
        validation_state: ValidationState | None = None,
    ) -> HarnessTraceEvent:

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
        event = HarnessTraceEvent(
            trace_id=run.trace_id,
            run_id=run.id,
            tenant_id=run.tenant_id,
            account_id=run.account_id,
            workflow_type=run.workflow_type,
            tool_contract_id=tool_contract.id if tool_contract else None,
            event_type="policy_decision",
            metadata={"decision": decision, **(metadata or {})},
        )
        self._dispatch(event)
        return event

    def _dispatch(self, event: HarnessTraceEvent) -> None:
        """Persist event to DB and call handlers. Never raises."""
        import asyncio

        self._events.append(event)

        # Schedule DB write as a fire-and-forget task after the current
        # call stack unwinds (avoids Session.add() inside an active flush).
        try:
            loop = asyncio.get_running_loop()
            loop.call_soon(lambda: loop.create_task(self._persist(event)))
        except RuntimeError:
            # No running event loop — skip DB write (sync test context).
            pass
        except Exception as exc:
            logger.warning("SqlTelemetryEmitter: could not schedule DB write: %s", exc)

        # Call in-memory handlers synchronously (same as base TelemetryEmitter)
        for handler in self._handlers:
            try:
                handler(event)
            except Exception as exc:
                logger.warning("Telemetry handler failed: %s", exc, exc_info=True)

    async def _persist(self, event: HarnessTraceEvent) -> None:
        """Write event to DB. Failure is logged, not raised."""
        try:
            # Skip if session is mid-flush to avoid SAWarning in nested contexts.
            if getattr(self._repo._session, "_flushing", False):
                return
            await self._repo.append(event)
        except Exception as exc:
            logger.warning("SqlTelemetryEmitter: DB persist failed (non-blocking): %s", exc)

    def get_events(
        self,
        run_id: str | None = None,
        tenant_id: str | None = None,
    ) -> list[HarnessTraceEvent]:
        """Retrieve emitted events from in-memory dispatch history."""
        events = list(self._events)
        if run_id is not None:
            events = [event for event in events if event.run_id == run_id]
        if tenant_id is not None:
            events = [event for event in events if event.tenant_id == tenant_id]
        return events

    async def get_events_async(
        self,
        run_id: str | None = None,
        tenant_id: str | None = None,
    ) -> list[HarnessTraceEvent]:
        """Async version of get_events for SQL-backed queries."""
        return await self._repo.list(run_id=run_id, tenant_id=tenant_id)

    def clear(self) -> None:
        """Clear in-memory event cache (testing compatibility)."""
        self._events.clear()


# ---------------------------------------------------------------------------
# SqlHarnessRegistry
# ---------------------------------------------------------------------------


class SqlHarnessRegistry:
    """SQL-backed top-level harness orchestrator.

    Drop-in replacement for HarnessRegistry. Wires SQL-backed stores
    for runs, gates, checkpoints, tools, and telemetry.
    """

    def __init__(
        self,
        session: AsyncSession,
        state_machine=None,
        tool_registry: SqlToolContractRegistry | None = None,
        gate_manager: SqlHumanGateManager | None = None,
        checkpoint_manager: SqlCheckpointManager | None = None,
        telemetry: SqlTelemetryEmitter | None = None,
        validation_hook=None,
    ) -> None:
        from harness.state_machine import StateMachine
        from harness.validation_hooks import ValidationHook

        self._run_repo = HarnessRunRepository(session)
        self._sm = state_machine or StateMachine()
        self._tools = tool_registry or SqlToolContractRegistry(session)
        self._gates = gate_manager or SqlHumanGateManager(session)
        self._checkpoints = checkpoint_manager or SqlCheckpointManager(session)
        self._telemetry = telemetry or SqlTelemetryEmitter(session)
        self._validation = validation_hook or ValidationHook()
        self._cvr_store = SqlClaimValidationStore(session)

    # ---- Run Lifecycle ----

    async def create_run(
        self,
        tenant_id: str,
        workflow_type: HarnessWorkflowType,
        initiated_by: InitiatedBy,
        account_id: str | None = None,
        value_pack_id: str | None = None,
    ) -> HarnessRun:
        run = HarnessRun(
            tenant_id=tenant_id,
            account_id=account_id,
            workflow_type=workflow_type,
            initiated_by=initiated_by,
            value_pack_id=value_pack_id,
        )
        await self._run_repo.create(run)
        self._telemetry.emit_transition_event(
            run=run,
            from_state=None,  # type: ignore[arg-type]
            to_state=HarnessState.INIT,
        )
        return run

    async def get_run(self, run_id: str, tenant_id: str) -> HarnessRun:
        return await self._run_repo.get(run_id, tenant_id)

    # ---- State Transitions ----

    async def transition(
        self,
        run_id: str,
        tenant_id: str,
        to_state: HarnessState,
        validation_results: list[ClaimValidationResult] | None = None,
        human_override: bool = False,
        state_payload: dict[str, Any] | None = None,
    ) -> tuple[HarnessRun, HarnessTraceEvent]:
        run = await self._run_repo.get(run_id, tenant_id)

        validation_state: ValidationState | None = None
        if validation_results is not None:
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

        self._telemetry.emit_transition_event(
            run=updated,
            from_state=run.current_state,
            to_state=to_state,
        )

        await self._run_repo.update(updated)

        if state_payload is not None:
            await self._checkpoints.create_checkpoint(
                run_id=run_id,
                tenant_id=tenant_id,
                state_name=to_state,
                state_payload=state_payload,
            )

        return updated, event

    # ---- Human Gates ----

    async def create_human_gate(
        self,
        run_id: str,
        tenant_id: str,
        gate_type: GateType,
    ) -> HumanGate:
        run = await self._run_repo.get(run_id, tenant_id)
        gate, event = await self._gates.create_gate(run_id, tenant_id, gate_type)
        event = event.model_copy(
            update={"trace_id": run.trace_id, "workflow_type": run.workflow_type}
        )
        self._telemetry._dispatch(event)
        return gate

    async def decide_gate(
        self,
        gate_id: str,
        tenant_id: str,
        decision: GateStatus,
        decision_by: str,
        decision_reason: str | None = None,
    ) -> HumanGate:
        from harness.registry import HarnessRegistryError

        if decision == GateStatus.APPROVED:
            gate, event = await self._gates.approve_gate(gate_id, tenant_id, decision_by, decision_reason)
        elif decision == GateStatus.REJECTED:
            gate, event = await self._gates.reject_gate(gate_id, tenant_id, decision_by, decision_reason)
        elif decision == GateStatus.MODIFIED:
            gate, event = await self._gates.modify_gate(gate_id, tenant_id, decision_by, decision_reason)
        elif decision == GateStatus.EXPIRED:
            gate, event = await self._gates.expire_gate(gate_id, tenant_id)
        else:
            raise HarnessRegistryError(f"Invalid gate decision: {decision}")

        try:
            run = await self._run_repo.get(gate.run_id, tenant_id)
        except HarnessRegistryError:
            run = None
        if run is not None:
            event = event.model_copy(
                update={"trace_id": run.trace_id, "workflow_type": run.workflow_type}
            )
            self._telemetry._dispatch(event)

        return gate

    async def get_gate(self, gate_id: str, tenant_id: str) -> HumanGate:
        return await self._gates.get_gate(gate_id, tenant_id)

    async def list_gates_for_run(self, run_id: str, tenant_id: str) -> list[HumanGate]:
        return await self._gates.list_gates_for_run(run_id, tenant_id)

    # ---- Validation ----

    async def validate_claims(
        self,
        tenant_id: str,
        requests: list,
        run_id: str | None = None,
    ) -> list[ClaimValidationResult]:
        """Validate claims and persist results when run_id is provided.

        run_id is optional for backwards compatibility with callers that
        validate outside a specific run context. When provided, results are
        written to harness_claim_validation_results so the GET /validation
        endpoint can return them without re-running validation.
        """
        from harness.registry import HarnessRegistryError
        from harness.validation_hooks import ClaimValidationRequest

        mismatched = [
            r.claim_id
            for r in requests
            if isinstance(r, ClaimValidationRequest) and r.tenant_id != tenant_id
        ]
        if mismatched:
            raise HarnessRegistryError(
                f"tenant_id mismatch in validate_claims: "
                f"claims {mismatched} do not belong to tenant '{tenant_id}'"
            )

        results = await self._validation.validate_claims(requests)

        if run_id is not None and results:
            try:
                await self._cvr_store.save_results(run_id, results)
            except Exception as exc:
                # Persist failure must not block the caller — log and continue.
                logger.warning(
                    "validate_claims: failed to persist results for run %s: %s",
                    run_id,
                    exc,
                )

        return results

    async def get_validation_results(
        self,
        run_id: str,
        tenant_id: str,
    ) -> list[ClaimValidationResult]:
        """Return stored validation results for a run, tenant-scoped."""
        return await self._cvr_store.get_results_for_run(run_id, tenant_id)

    # ---- Checkpoints ----

    async def get_checkpoints(self, run_id: str, tenant_id: str) -> list[HarnessCheckpoint]:
        return await self._checkpoints.list_checkpoints_for_run(run_id, tenant_id)

    # ---- Tool Registry ----

    async def register_tool(self, tool: ToolContract, tenant_id: str) -> ToolContract:
        return await self._tools.register_tool(tool, tenant_id)

    async def get_tool(self, tool_id: str, tenant_id: str) -> ToolContract:
        return await self._tools.get_tool(tool_id, tenant_id)

    # ---- Queries ----

    async def list_runs(
        self,
        tenant_id: str | None = None,
        status: HarnessRunStatus | None = None,
        workflow_type: HarnessWorkflowType | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[HarnessRun], int]:
        """Return (items, total_count) for the given filters.

        Returns an empty result rather than raising when tenant_id is None.
        """
        if tenant_id is None:
            return [], 0
        return await self._run_repo.list(
            tenant_id=tenant_id,
            status=status,
            workflow_type=workflow_type,
            limit=limit,
            offset=offset,
        )

    @property
    def telemetry(self) -> SqlTelemetryEmitter:
        return self._telemetry

    @property
    def validation_available(self) -> bool:
        """Sync property — returns True only if primary validator is configured.
        Use await registry._validation.is_available() for a live health check."""
        return self._validation._primary is not None
