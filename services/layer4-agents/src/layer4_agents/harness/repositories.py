from __future__ import annotations

"""Async repository layer for Fabric Harness persistence.

Each repository translates between Pydantic v2 domain models and SQLAlchemy
ORM rows. No ORM objects leak outside this module — callers always receive
domain model instances.

All queries filter by tenant_id. Cross-tenant access raises the same domain
errors as the in-memory stores so callers need no conditional logic.
"""


import logging
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from .db_models import (
    HarnessCheckpointRow,
    HarnessRunRow,
    HarnessTraceEventRow,
    HumanGateRow,
    ToolContractRow,
)
from .models import (
    ActionClass,
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
    ToolLayer,
    ToolRiskLevel,
    ToolSideEffectClass,
    ValidationState,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Mapping helpers — domain model ↔ ORM row
# ---------------------------------------------------------------------------


def _run_to_row(run: HarnessRun) -> HarnessRunRow:
    return HarnessRunRow(
        id=run.id,
        tenant_id=run.tenant_id,
        account_id=run.account_id,
        workflow_type=run.workflow_type.value,
        initiated_by=run.initiated_by.value,
        status=run.status.value,
        current_state=run.current_state.value,
        value_pack_id=run.value_pack_id,
        trace_id=run.trace_id,
        created_at=run.created_at,
        updated_at=run.updated_at,
    )


def _row_to_run(row: HarnessRunRow) -> HarnessRun:
    return HarnessRun(
        id=row.id,
        tenant_id=row.tenant_id,
        account_id=row.account_id,
        workflow_type=HarnessWorkflowType(row.workflow_type),
        initiated_by=InitiatedBy(row.initiated_by),
        status=HarnessRunStatus(row.status),
        current_state=HarnessState(row.current_state),
        value_pack_id=row.value_pack_id,
        trace_id=row.trace_id,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _gate_to_row(gate: HumanGate) -> HumanGateRow:
    return HumanGateRow(
        id=gate.id,
        run_id=gate.run_id,
        tenant_id=gate.tenant_id,
        gate_type=gate.gate_type.value,
        action_class=gate.action_class.value if gate.action_class else None,
        status=gate.status.value,
        decision_by=gate.decision_by,
        decision_reason=gate.decision_reason,
        created_at=gate.created_at,
        decided_at=gate.decided_at,
    )


def _row_to_gate(row: HumanGateRow) -> HumanGate:
    return HumanGate(
        id=row.id,
        run_id=row.run_id,
        tenant_id=row.tenant_id,
        gate_type=GateType(row.gate_type),
        action_class=ActionClass(row.action_class) if row.action_class else None,
        status=GateStatus(row.status),
        decision_by=row.decision_by,
        decision_reason=row.decision_reason,
        created_at=row.created_at,
        decided_at=row.decided_at,
    )


def _checkpoint_to_row(cp: HarnessCheckpoint) -> HarnessCheckpointRow:
    return HarnessCheckpointRow(
        id=cp.id,
        run_id=cp.run_id,
        tenant_id=cp.tenant_id,
        state_name=cp.state_name.value,
        state_payload=dict(cp.state_payload),
        input_hash=cp.input_hash,
        output_hash=cp.output_hash,
        tool_calls=[
            {
                "tool_contract_id": tc.tool_contract_id,
                "invocation_id": tc.invocation_id,
                "input_hash": tc.input_hash,
                "output_hash": tc.output_hash,
            }
            for tc in cp.tool_calls
        ],
        created_at=cp.created_at,
    )


def _row_to_checkpoint(row: HarnessCheckpointRow) -> HarnessCheckpoint:
    tool_calls = [
        ToolCallRef(
            tool_contract_id=tc["tool_contract_id"],
            invocation_id=tc["invocation_id"],
            input_hash=tc["input_hash"],
            output_hash=tc.get("output_hash"),
        )
        for tc in (row.tool_calls or [])
    ]
    return HarnessCheckpoint(
        id=row.id,
        run_id=row.run_id,
        tenant_id=row.tenant_id,
        state_name=HarnessState(row.state_name),
        state_payload=dict(row.state_payload or {}),
        input_hash=row.input_hash,
        output_hash=row.output_hash,
        tool_calls=tool_calls,
        created_at=row.created_at,
    )


def _tool_to_row(tool: ToolContract, tenant_id: str) -> ToolContractRow:
    return ToolContractRow(
        id=tool.id,
        tool_id=tool.tool_id,
        tenant_id=tenant_id,
        layer=tool.layer.value,
        version=tool.version,
        input_schema_ref=tool.input_schema_ref,
        output_schema_ref=tool.output_schema_ref,
        side_effect_class=tool.side_effect_class.value,
        risk_level=tool.risk_level.value,
        requires_tenant_context=tool.requires_tenant_context,
        requires_account_context=tool.requires_account_context,
        approval_policy_id=tool.approval_policy_id,
        created_at=datetime.now(UTC),
    )


def _row_to_tool(row: ToolContractRow) -> ToolContract:
    return ToolContract(
        id=row.id,
        tool_id=row.tool_id,
        layer=ToolLayer(row.layer),
        version=row.version,
        input_schema_ref=row.input_schema_ref,
        output_schema_ref=row.output_schema_ref,
        side_effect_class=ToolSideEffectClass(row.side_effect_class),
        risk_level=ToolRiskLevel(row.risk_level),
        requires_tenant_context=row.requires_tenant_context,
        requires_account_context=row.requires_account_context,
        approval_policy_id=row.approval_policy_id,
    )


def _event_to_row(event: HarnessTraceEvent) -> HarnessTraceEventRow:
    return HarnessTraceEventRow(
        id=f"evt_{event.trace_id[-8:]}_{event.run_id[-8:]}_{int(event.timestamp.timestamp() * 1000) % 10**9}",
        trace_id=event.trace_id,
        run_id=event.run_id,
        tenant_id=event.tenant_id,
        account_id=event.account_id,
        workflow_type=event.workflow_type.value,
        from_state=event.from_state.value if event.from_state else None,
        to_state=event.to_state.value if event.to_state else None,
        status=event.status.value if event.status else None,
        value_pack_id=event.value_pack_id,
        validation_state=event.validation_state.value if event.validation_state else None,
        human_gate_id=event.human_gate_id,
        tool_contract_id=event.tool_contract_id,
        event_type=event.event_type,
        metadata_=dict(event.metadata),
        timestamp=event.timestamp,
    )


def _row_to_event(row: HarnessTraceEventRow) -> HarnessTraceEvent:
    return HarnessTraceEvent(
        trace_id=row.trace_id,
        run_id=row.run_id,
        tenant_id=row.tenant_id,
        account_id=row.account_id,
        workflow_type=HarnessWorkflowType(row.workflow_type),
        from_state=HarnessState(row.from_state) if row.from_state else None,
        to_state=HarnessState(row.to_state) if row.to_state else None,
        status=HarnessRunStatus(row.status) if row.status else None,
        value_pack_id=row.value_pack_id,
        validation_state=ValidationState(row.validation_state) if row.validation_state else None,
        human_gate_id=row.human_gate_id,
        tool_contract_id=row.tool_contract_id,
        event_type=row.event_type,
        metadata=dict(row.metadata_ or {}),
        timestamp=row.timestamp,
    )


# ---------------------------------------------------------------------------
# Repositories
# ---------------------------------------------------------------------------


class HarnessRunRepository:
    """Async repository for HarnessRun persistence."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, run: HarnessRun) -> HarnessRun:
        row = _run_to_row(run)
        self._session.add(row)
        await self._session.flush()
        return run

    async def get(self, run_id: str, tenant_id: str) -> HarnessRun:
        from harness.registry import RunNotFoundError

        result = await self._session.execute(
            select(HarnessRunRow).where(
                HarnessRunRow.id == run_id,
                HarnessRunRow.tenant_id == tenant_id,
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            raise RunNotFoundError(f"Run '{run_id}' not found for tenant '{tenant_id}'")
        return _row_to_run(row)

    async def update(self, run: HarnessRun, expected_updated_at: datetime | None = None) -> HarnessRun:
        from harness.registry import HarnessRegistryError, TransitionConflictError

        stmt = (
            update(HarnessRunRow)
            .where(
                HarnessRunRow.id == run.id,
                HarnessRunRow.tenant_id == run.tenant_id,
            )
            .values(
                status=run.status.value,
                current_state=run.current_state.value,
                updated_at=run.updated_at,
            )
        )
        if expected_updated_at is not None:
            stmt = stmt.where(HarnessRunRow.updated_at == expected_updated_at)
        result = await self._session.execute(stmt)
        if result.rowcount == 0:
            if expected_updated_at is not None:
                raise TransitionConflictError(f"Stale run state for '{run.id}'")
            raise HarnessRegistryError(f"Run '{run.id}' not found for update")

        await self._session.flush()
        return run

    async def get_for_update(self, run_id: str, tenant_id: str) -> HarnessRun:
        """Fetch a run row using a row lock while preserving tenant isolation."""
        from harness.registry import RunNotFoundError

        result = await self._session.execute(
            select(HarnessRunRow)
            .where(
                HarnessRunRow.id == run_id,
                HarnessRunRow.tenant_id == tenant_id,
            )
            .with_for_update()
        )
        row = result.scalar_one_or_none()
        if row is None:
            raise RunNotFoundError(f"Run '{run_id}' not found for tenant '{tenant_id}'")
        return _row_to_run(row)

    async def list(
        self,
        tenant_id: str,
        status: HarnessRunStatus | None = None,
        workflow_type: HarnessWorkflowType | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[HarnessRun], int]:
        """Return (items, total_count) for the given filters.

        ``total_count`` reflects the full unsliced count so callers can
        compute ``has_more`` without relying on slice length.
        """
        from sqlalchemy import func
        from sqlalchemy import select as sa_select

        base = sa_select(HarnessRunRow).where(HarnessRunRow.tenant_id == tenant_id)
        if status is not None:
            base = base.where(HarnessRunRow.status == status.value)
        if workflow_type is not None:
            base = base.where(HarnessRunRow.workflow_type == workflow_type.value)

        count_stmt = sa_select(func.count()).select_from(base.subquery())
        total: int = (await self._session.execute(count_stmt)).scalar_one()

        page_stmt = base.order_by(HarnessRunRow.created_at.desc()).limit(limit).offset(offset)
        result = await self._session.execute(page_stmt)
        items = [_row_to_run(row) for row in result.scalars().all()]
        return items, total


class HumanGateRepository:
    """Async repository for HumanGate persistence."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, gate: HumanGate) -> HumanGate:
        row = _gate_to_row(gate)
        self._session.add(row)
        await self._session.flush()
        return gate

    async def get(self, gate_id: str, tenant_id: str) -> HumanGate:
        from harness.human_gates import GateNotFoundError

        result = await self._session.execute(
            select(HumanGateRow).where(
                HumanGateRow.id == gate_id,
                HumanGateRow.tenant_id == tenant_id,
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            raise GateNotFoundError(f"Gate '{gate_id}' not found for tenant '{tenant_id}'")
        return _row_to_gate(row)

    async def get_for_update(self, gate_id: str, tenant_id: str) -> HumanGate:
        """Fetch a gate row using a row lock while preserving tenant isolation."""
        from harness.human_gates import GateNotFoundError

        result = await self._session.execute(
            select(HumanGateRow)
            .where(
                HumanGateRow.id == gate_id,
                HumanGateRow.tenant_id == tenant_id,
            )
            .with_for_update()
        )
        row = result.scalar_one_or_none()
        if row is None:
            raise GateNotFoundError(f"Gate '{gate_id}' not found for tenant '{tenant_id}'")
        return _row_to_gate(row)

    async def update(self, gate: HumanGate) -> HumanGate:
        from harness.human_gates import GateNotFoundError

        result = await self._session.execute(
            select(HumanGateRow).where(
                HumanGateRow.id == gate.id,
                HumanGateRow.tenant_id == gate.tenant_id,
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            raise GateNotFoundError(f"Gate '{gate.id}' not found for update")

        row.status = gate.status.value
        row.decision_by = gate.decision_by
        row.decision_reason = gate.decision_reason
        row.decided_at = gate.decided_at
        await self._session.flush()
        return gate

    async def list_for_run(self, run_id: str, tenant_id: str) -> list[HumanGate]:
        result = await self._session.execute(
            select(HumanGateRow).where(
                HumanGateRow.run_id == run_id,
                HumanGateRow.tenant_id == tenant_id,
            )
        )
        return [_row_to_gate(row) for row in result.scalars().all()]


class CheckpointRepository:
    """Async repository for HarnessCheckpoint persistence."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, checkpoint: HarnessCheckpoint) -> HarnessCheckpoint:
        row = _checkpoint_to_row(checkpoint)
        self._session.add(row)
        await self._session.flush()
        return checkpoint

    async def get(self, checkpoint_id: str, run_id: str, tenant_id: str) -> HarnessCheckpoint:
        from harness.checkpoints import CheckpointError, CheckpointTenantError

        result = await self._session.execute(
            select(HarnessCheckpointRow).where(HarnessCheckpointRow.id == checkpoint_id)
        )
        row = result.scalar_one_or_none()
        if row is None:
            raise CheckpointError(f"Checkpoint '{checkpoint_id}' not found")
        if row.run_id != run_id:
            raise CheckpointTenantError(
                f"Checkpoint '{checkpoint_id}' run_id mismatch: expected {run_id}"
            )
        if row.tenant_id != tenant_id:
            raise CheckpointTenantError(
                f"Checkpoint '{checkpoint_id}' tenant_id mismatch: expected {tenant_id}"
            )
        return _row_to_checkpoint(row)

    async def list_for_run(self, run_id: str, tenant_id: str) -> list[HarnessCheckpoint]:
        from sqlalchemy import asc

        result = await self._session.execute(
            select(HarnessCheckpointRow)
            .where(
                HarnessCheckpointRow.run_id == run_id,
                HarnessCheckpointRow.tenant_id == tenant_id,
            )
            .order_by(asc(HarnessCheckpointRow.created_at))
        )
        return [_row_to_checkpoint(row) for row in result.scalars().all()]

    async def get_latest(self, run_id: str, tenant_id: str) -> HarnessCheckpoint | None:
        from sqlalchemy import desc

        result = await self._session.execute(
            select(HarnessCheckpointRow)
            .where(
                HarnessCheckpointRow.run_id == run_id,
                HarnessCheckpointRow.tenant_id == tenant_id,
            )
            .order_by(desc(HarnessCheckpointRow.created_at))
            .limit(1)
        )
        row = result.scalar_one_or_none()
        return _row_to_checkpoint(row) if row is not None else None


class ToolContractRepository:
    """Async repository for ToolContract persistence."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def register(self, tool: ToolContract, tenant_id: str) -> ToolContract:
        from harness.tool_contracts import ToolRegistrationError

        # Enforce: high-risk tools need approval policy
        if tool.risk_level in (ToolRiskLevel.HIGH, ToolRiskLevel.CRITICAL):
            if not tool.approval_policy_id:
                raise ToolRegistrationError(
                    f"High-risk tool '{tool.tool_id}' must have approval_policy_id"
                )
        if tool.side_effect_class == ToolSideEffectClass.CUSTOMER_FACING_OUTPUT:
            if not tool.approval_policy_id:
                raise ToolRegistrationError(
                    f"Customer-facing tool '{tool.tool_id}' must have approval_policy_id"
                )

        row = _tool_to_row(tool, tenant_id)
        self._session.add(row)
        try:
            await self._session.flush()
        except IntegrityError:
            await self._session.rollback()
            raise ToolRegistrationError(
                f"Tool '{tool.tool_id}' already registered for tenant '{tenant_id}'"
            )
        return tool

    async def get(self, tool_id: str, tenant_id: str) -> ToolContract:
        from harness.tool_contracts import ToolNotFoundError

        result = await self._session.execute(
            select(ToolContractRow).where(
                ToolContractRow.tool_id == tool_id,
                ToolContractRow.tenant_id == tenant_id,
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            raise ToolNotFoundError(f"Tool '{tool_id}' not found for tenant '{tenant_id}'")
        return _row_to_tool(row)

    async def list(
        self,
        tenant_id: str,
        layer: str | None = None,
        risk_level: ToolRiskLevel | None = None,
    ) -> list[ToolContract]:
        stmt = select(ToolContractRow).where(ToolContractRow.tenant_id == tenant_id)
        if layer is not None:
            stmt = stmt.where(ToolContractRow.layer == layer)
        if risk_level is not None:
            stmt = stmt.where(ToolContractRow.risk_level == risk_level.value)
        result = await self._session.execute(stmt)
        return [_row_to_tool(row) for row in result.scalars().all()]

    async def delete(self, tool_id: str, tenant_id: str) -> None:
        from harness.tool_contracts import ToolNotFoundError

        result = await self._session.execute(
            select(ToolContractRow).where(
                ToolContractRow.tool_id == tool_id,
                ToolContractRow.tenant_id == tenant_id,
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            raise ToolNotFoundError(f"Tool '{tool_id}' not found for tenant '{tenant_id}'")
        await self._session.delete(row)
        await self._session.flush()


class TraceEventRepository:
    """Async repository for HarnessTraceEvent persistence."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def append(self, event: HarnessTraceEvent) -> HarnessTraceEvent:
        row = _event_to_row(event)
        self._session.add(row)
        await self._session.flush()
        return event

    async def list(
        self,
        run_id: str | None = None,
        tenant_id: str | None = None,
    ) -> list[HarnessTraceEvent]:
        from sqlalchemy import asc

        stmt = select(HarnessTraceEventRow)
        if run_id is not None:
            stmt = stmt.where(HarnessTraceEventRow.run_id == run_id)
        if tenant_id is not None:
            stmt = stmt.where(HarnessTraceEventRow.tenant_id == tenant_id)
        stmt = stmt.order_by(asc(HarnessTraceEventRow.timestamp))
        result = await self._session.execute(stmt)
        return [_row_to_event(row) for row in result.scalars().all()]
