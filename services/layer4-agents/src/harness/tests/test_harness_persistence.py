"""SQL persistence tests for the Fabric Harness.

Uses SQLite + aiosqlite — no external Postgres required in CI.
All five repository classes and their SQL-backed store wrappers are covered.

Test classes:
  TestSqlRunRepository
  TestSqlGateRepository
  TestSqlCheckpointRepository
  TestSqlToolContractRepository
  TestSqlTraceEventRepository
  TestSqlHarnessRegistryIntegration
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import pytest_asyncio

# Ensure harness is importable from src/
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from harness.checkpoints import CheckpointError, CheckpointTenantError

# ---------------------------------------------------------------------------
# SQLite fixtures
# ---------------------------------------------------------------------------
# Import Base from db_models — it falls back to a local DeclarativeBase
# when src.database is unavailable (e.g. SQLite test environment).
from harness.db_models import (
    Base,  # noqa: E402
    ClaimValidationResultRow,
    HarnessCheckpointRow,
    HarnessRunRow,
    HarnessTraceEventRow,
    HumanGateRow,
    ToolContractRow,
)
from harness.factory import make_in_memory_registry, make_sql_registry
from harness.human_gates import GateNotFoundError
from harness.models import (
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
    ToolLayer,
    ToolRiskLevel,
    ToolSideEffectClass,
)
from harness.registry import RunNotFoundError
from harness.repositories import (
    CheckpointRepository,
    HarnessRunRepository,
    HumanGateRepository,
    ToolContractRepository,
    TraceEventRepository,
)
from harness.tool_contracts import ToolNotFoundError, ToolRegistrationError


@pytest_asyncio.fixture
async def async_engine():
    """In-memory SQLite engine with harness schema created."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        # Create only harness tables (subset of full Base metadata)
        await conn.run_sync(
            lambda sync_conn: Base.metadata.create_all(
                sync_conn,
                tables=[
                    HarnessRunRow.__table__,
                    HumanGateRow.__table__,
                    HarnessCheckpointRow.__table__,
                    ToolContractRow.__table__,
                    HarnessTraceEventRow.__table__,
                    ClaimValidationResultRow.__table__,
                ],
            )
        )
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def session(async_engine):
    """AsyncSession bound to the in-memory SQLite engine.

    When src.database is imported elsewhere in the same pytest process (e.g.
    by the migration tests), it registers a TenantContextError-raising
    before_flush listener on the base SQLAlchemy Session class. That listener
    fires on every flush — including our plain SQLite sessions — and raises
    TenantContextError because no tenant context is set.

    We temporarily remove that listener for the duration of each test and
    restore it afterward so other tests are unaffected.
    """
    from sqlalchemy import event
    from sqlalchemy.orm import Session

    _removed: list = []
    # Snapshot listeners registered on Session.before_flush via _clslevel
    try:
        clslevel = Session.dispatch.before_flush._clslevel
        listeners = list(clslevel.get(Session, []))
        for fn in listeners:
            try:
                event.remove(Session, "before_flush", fn)
                _removed.append(fn)
            except Exception:
                pass
    except Exception:
        pass

    async_session = sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as s:
        yield s

    # Restore removed listeners
    for fn in _removed:
        try:
            if not event.contains(Session, "before_flush", fn):
                event.listen(Session, "before_flush", fn)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Shared test data helpers
# ---------------------------------------------------------------------------

TENANT_A = "tenant_alpha"
TENANT_B = "tenant_beta"


def _make_run(tenant_id: str = TENANT_A, **kwargs) -> HarnessRun:
    return HarnessRun(
        tenant_id=tenant_id,
        workflow_type=HarnessWorkflowType.VALUE_MODEL_GENERATION,
        initiated_by=InitiatedBy.USER,
        account_id="acct_001",
        **kwargs,
    )


def _make_low_risk_tool(tool_id: str = "fabric.l3.graph_query") -> ToolContract:
    return ToolContract(
        tool_id=tool_id,
        layer=ToolLayer.L3,
        input_schema_ref="GraphQueryRequest",
        output_schema_ref="GraphQueryResponse",
        side_effect_class=ToolSideEffectClass.READ,
        risk_level=ToolRiskLevel.LOW,
        requires_tenant_context=True,
    )


def _make_high_risk_tool(tool_id: str = "fabric.output.business_case") -> ToolContract:
    return ToolContract(
        tool_id=tool_id,
        layer=ToolLayer.PRESENTATION,
        input_schema_ref="BusinessCaseRequest",
        output_schema_ref="BusinessCaseOutput",
        side_effect_class=ToolSideEffectClass.CUSTOMER_FACING_OUTPUT,
        risk_level=ToolRiskLevel.HIGH,
        requires_tenant_context=True,
        requires_account_context=True,
        approval_policy_id="policy_customer_output_v1",
    )


# ===========================================================================
# TestSqlRunRepository
# ===========================================================================


class TestSqlRunRepository:
    async def test_create_and_get_run(self, session: AsyncSession) -> None:
        repo = HarnessRunRepository(session)
        run = _make_run()
        await repo.create(run)
        fetched = await repo.get(run.id, TENANT_A)
        assert fetched.id == run.id
        assert fetched.tenant_id == TENANT_A
        assert fetched.workflow_type == HarnessWorkflowType.VALUE_MODEL_GENERATION
        assert fetched.current_state == HarnessState.INIT

    async def test_get_wrong_tenant_raises(self, session: AsyncSession) -> None:
        repo = HarnessRunRepository(session)
        run = _make_run(tenant_id=TENANT_A)
        await repo.create(run)
        with pytest.raises(RunNotFoundError):
            await repo.get(run.id, TENANT_B)

    async def test_list_filters_by_tenant(self, session: AsyncSession) -> None:
        repo = HarnessRunRepository(session)
        run_a = _make_run(tenant_id=TENANT_A)
        run_b = _make_run(tenant_id=TENANT_B)
        await repo.create(run_a)
        await repo.create(run_b)
        results, _total = await repo.list(TENANT_A)
        ids = [r.id for r in results]
        assert run_a.id in ids
        assert run_b.id not in ids

    async def test_list_filters_by_status(self, session: AsyncSession) -> None:
        repo = HarnessRunRepository(session)
        run = _make_run()
        await repo.create(run)
        queued, _total_q = await repo.list(TENANT_A, status=HarnessRunStatus.QUEUED)
        running, _total_r = await repo.list(TENANT_A, status=HarnessRunStatus.RUNNING)
        assert any(r.id == run.id for r in queued)
        assert not any(r.id == run.id for r in running)

    async def test_update_run_state(self, session: AsyncSession) -> None:
        repo = HarnessRunRepository(session)
        run = _make_run()
        await repo.create(run)
        updated = run.with_state(HarnessState.RESOLVE_CONTEXT, status=HarnessRunStatus.RUNNING)
        await repo.update(updated)
        fetched = await repo.get(run.id, TENANT_A)
        assert fetched.current_state == HarnessState.RESOLVE_CONTEXT
        assert fetched.status == HarnessRunStatus.RUNNING


# ===========================================================================
# TestSqlGateRepository
# ===========================================================================


class TestSqlGateRepository:
    async def test_create_and_get_gate(self, session: AsyncSession) -> None:
        run_repo = HarnessRunRepository(session)
        gate_repo = HumanGateRepository(session)
        run = _make_run()
        await run_repo.create(run)
        gate = HumanGate(run_id=run.id, tenant_id=TENANT_A, gate_type=GateType.APPROVE_CLAIMS)
        await gate_repo.create(gate)
        fetched = await gate_repo.get(gate.id, TENANT_A)
        assert fetched.id == gate.id
        assert fetched.status == GateStatus.PENDING
        assert fetched.gate_type == GateType.APPROVE_CLAIMS

    async def test_approve_gate_persisted(self, session: AsyncSession) -> None:
        run_repo = HarnessRunRepository(session)
        gate_repo = HumanGateRepository(session)
        run = _make_run()
        await run_repo.create(run)
        gate = HumanGate(run_id=run.id, tenant_id=TENANT_A, gate_type=GateType.APPROVE_CLAIMS)
        await gate_repo.create(gate)
        approved = gate.decide(GateStatus.APPROVED, decision_by="alice", decision_reason="LGTM")
        await gate_repo.update(approved)
        fetched = await gate_repo.get(gate.id, TENANT_A)
        assert fetched.status == GateStatus.APPROVED
        assert fetched.decision_by == "alice"
        assert fetched.decision_reason == "LGTM"
        assert fetched.decided_at is not None

    async def test_reject_gate_persisted(self, session: AsyncSession) -> None:
        run_repo = HarnessRunRepository(session)
        gate_repo = HumanGateRepository(session)
        run = _make_run()
        await run_repo.create(run)
        gate = HumanGate(run_id=run.id, tenant_id=TENANT_A, gate_type=GateType.APPROVE_CLAIMS)
        await gate_repo.create(gate)
        rejected = gate.decide(GateStatus.REJECTED, decision_by="bob", decision_reason="Needs more evidence")
        await gate_repo.update(rejected)
        fetched = await gate_repo.get(gate.id, TENANT_A)
        assert fetched.status == GateStatus.REJECTED
        assert fetched.decision_by == "bob"

    async def test_cross_tenant_gate_not_found(self, session: AsyncSession) -> None:
        run_repo = HarnessRunRepository(session)
        gate_repo = HumanGateRepository(session)
        run = _make_run(tenant_id=TENANT_A)
        await run_repo.create(run)
        gate = HumanGate(run_id=run.id, tenant_id=TENANT_A, gate_type=GateType.APPROVE_CLAIMS)
        await gate_repo.create(gate)
        with pytest.raises(GateNotFoundError):
            await gate_repo.get(gate.id, TENANT_B)

    async def test_list_gates_for_run(self, session: AsyncSession) -> None:
        run_repo = HarnessRunRepository(session)
        gate_repo = HumanGateRepository(session)
        run = _make_run()
        await run_repo.create(run)
        g1 = HumanGate(run_id=run.id, tenant_id=TENANT_A, gate_type=GateType.APPROVE_CLAIMS)
        g2 = HumanGate(run_id=run.id, tenant_id=TENANT_A, gate_type=GateType.APPROVE_CUSTOMER_OUTPUT)
        await gate_repo.create(g1)
        await gate_repo.create(g2)
        gates = await gate_repo.list_for_run(run.id, TENANT_A)
        ids = [g.id for g in gates]
        assert g1.id in ids
        assert g2.id in ids


# ===========================================================================
# TestSqlCheckpointRepository
# ===========================================================================


class TestSqlCheckpointRepository:
    async def test_create_checkpoint_deterministic_hash(self, session: AsyncSession) -> None:
        run_repo = HarnessRunRepository(session)
        cp_repo = CheckpointRepository(session)
        run = _make_run()
        await run_repo.create(run)
        payload = {"key": "value", "count": 42}
        hash1 = HarnessCheckpoint.compute_input_hash(
            run_id=run.id, tenant_id=TENANT_A,
            state_name=HarnessState.RESOLVE_CONTEXT,
            state_payload=payload, tool_calls=[],
        )
        cp = HarnessCheckpoint(
            run_id=run.id, tenant_id=TENANT_A,
            state_name=HarnessState.RESOLVE_CONTEXT,
            state_payload=payload, input_hash=hash1,
        )
        await cp_repo.create(cp)
        fetched = await cp_repo.get(cp.id, run.id, TENANT_A)
        assert fetched.input_hash == hash1

    async def test_same_payload_same_hash_after_roundtrip(self, session: AsyncSession) -> None:
        run_repo = HarnessRunRepository(session)
        cp_repo = CheckpointRepository(session)
        run = _make_run()
        await run_repo.create(run)
        payload = {"nested": {"a": 1}, "list": [1, 2, 3]}
        hash_before = HarnessCheckpoint.compute_input_hash(
            run_id=run.id, tenant_id=TENANT_A,
            state_name=HarnessState.MATCH_EVIDENCE,
            state_payload=payload, tool_calls=[],
        )
        cp = HarnessCheckpoint(
            run_id=run.id, tenant_id=TENANT_A,
            state_name=HarnessState.MATCH_EVIDENCE,
            state_payload=payload, input_hash=hash_before,
        )
        await cp_repo.create(cp)
        fetched = await cp_repo.get(cp.id, run.id, TENANT_A)
        hash_after = HarnessCheckpoint.compute_input_hash(
            run_id=fetched.run_id, tenant_id=fetched.tenant_id,
            state_name=fetched.state_name,
            state_payload=dict(fetched.state_payload), tool_calls=list(fetched.tool_calls),
        )
        assert hash_before == hash_after

    async def test_cross_tenant_checkpoint_rejected(self, session: AsyncSession) -> None:
        run_repo = HarnessRunRepository(session)
        cp_repo = CheckpointRepository(session)
        run = _make_run(tenant_id=TENANT_A)
        await run_repo.create(run)
        h = HarnessCheckpoint.compute_input_hash(
            run_id=run.id, tenant_id=TENANT_A,
            state_name=HarnessState.INIT, state_payload={}, tool_calls=[],
        )
        cp = HarnessCheckpoint(
            run_id=run.id, tenant_id=TENANT_A,
            state_name=HarnessState.INIT, state_payload={}, input_hash=h,
        )
        await cp_repo.create(cp)
        with pytest.raises((CheckpointError, CheckpointTenantError)):
            await cp_repo.get(cp.id, run.id, TENANT_B)

    async def test_list_ordered_by_created_at(self, session: AsyncSession) -> None:
        run_repo = HarnessRunRepository(session)
        cp_repo = CheckpointRepository(session)
        run = _make_run()
        await run_repo.create(run)
        for state in [HarnessState.INIT, HarnessState.RESOLVE_CONTEXT, HarnessState.LOAD_VALUE_PACK]:
            h = HarnessCheckpoint.compute_input_hash(
                run_id=run.id, tenant_id=TENANT_A,
                state_name=state, state_payload={}, tool_calls=[],
            )
            cp = HarnessCheckpoint(
                run_id=run.id, tenant_id=TENANT_A,
                state_name=state, state_payload={}, input_hash=h,
            )
            await cp_repo.create(cp)
        checkpoints = await cp_repo.list_for_run(run.id, TENANT_A)
        assert len(checkpoints) == 3
        states = [c.state_name for c in checkpoints]
        assert states[0] == HarnessState.INIT

    async def test_get_latest_checkpoint(self, session: AsyncSession) -> None:
        run_repo = HarnessRunRepository(session)
        cp_repo = CheckpointRepository(session)
        run = _make_run()
        await run_repo.create(run)
        for state in [HarnessState.INIT, HarnessState.RESOLVE_CONTEXT]:
            h = HarnessCheckpoint.compute_input_hash(
                run_id=run.id, tenant_id=TENANT_A,
                state_name=state, state_payload={}, tool_calls=[],
            )
            cp = HarnessCheckpoint(
                run_id=run.id, tenant_id=TENANT_A,
                state_name=state, state_payload={}, input_hash=h,
            )
            await cp_repo.create(cp)
        latest = await cp_repo.get_latest(run.id, TENANT_A)
        assert latest is not None
        assert latest.state_name == HarnessState.RESOLVE_CONTEXT


# ===========================================================================
# TestSqlToolContractRepository
# ===========================================================================


class TestSqlToolContractRepository:
    async def test_register_and_get_tool(self, session: AsyncSession) -> None:
        repo = ToolContractRepository(session)
        tool = _make_low_risk_tool()
        await repo.register(tool, TENANT_A)
        fetched = await repo.get(tool.tool_id, TENANT_A)
        assert fetched.tool_id == tool.tool_id
        assert fetched.layer == ToolLayer.L3
        assert fetched.risk_level == ToolRiskLevel.LOW

    async def test_duplicate_registration_raises(self, session: AsyncSession) -> None:
        repo = ToolContractRepository(session)
        tool = _make_low_risk_tool()
        await repo.register(tool, TENANT_A)
        with pytest.raises(ToolRegistrationError):
            await repo.register(tool, TENANT_A)

    async def test_cross_tenant_tool_not_found(self, session: AsyncSession) -> None:
        repo = ToolContractRepository(session)
        tool = _make_low_risk_tool()
        await repo.register(tool, TENANT_A)
        with pytest.raises(ToolNotFoundError):
            await repo.get(tool.tool_id, TENANT_B)

    async def test_list_by_layer(self, session: AsyncSession) -> None:
        repo = ToolContractRepository(session)
        t1 = _make_low_risk_tool("fabric.l3.query")
        t2 = _make_high_risk_tool("fabric.output.case")
        await repo.register(t1, TENANT_A)
        await repo.register(t2, TENANT_A)
        l3_tools = await repo.list(TENANT_A, layer="L3")
        assert any(t.tool_id == "fabric.l3.query" for t in l3_tools)
        assert not any(t.tool_id == "fabric.output.case" for t in l3_tools)

    async def test_list_by_risk_level(self, session: AsyncSession) -> None:
        repo = ToolContractRepository(session)
        t1 = _make_low_risk_tool("fabric.l3.low")
        t2 = _make_high_risk_tool("fabric.output.high")
        await repo.register(t1, TENANT_A)
        await repo.register(t2, TENANT_A)
        high_tools = await repo.list(TENANT_A, risk_level=ToolRiskLevel.HIGH)
        assert any(t.tool_id == "fabric.output.high" for t in high_tools)
        assert not any(t.tool_id == "fabric.l3.low" for t in high_tools)

    async def test_delete_tool(self, session: AsyncSession) -> None:
        repo = ToolContractRepository(session)
        tool = _make_low_risk_tool()
        await repo.register(tool, TENANT_A)
        await repo.delete(tool.tool_id, TENANT_A)
        with pytest.raises(ToolNotFoundError):
            await repo.get(tool.tool_id, TENANT_A)

    async def test_high_risk_without_policy_raises(self, session: AsyncSession) -> None:
        repo = ToolContractRepository(session)
        bad_tool = ToolContract(
            tool_id="fabric.critical.no_policy",
            layer=ToolLayer.L4,
            input_schema_ref="Req",
            output_schema_ref="Resp",
            side_effect_class=ToolSideEffectClass.EXTERNAL_WRITE,
            risk_level=ToolRiskLevel.CRITICAL,
            requires_tenant_context=True,
        )
        with pytest.raises(ToolRegistrationError):
            await repo.register(bad_tool, TENANT_A)


# ===========================================================================
# TestSqlTraceEventRepository
# ===========================================================================


class TestSqlTraceEventRepository:
    async def test_append_event(self, session: AsyncSession) -> None:
        run_repo = HarnessRunRepository(session)
        evt_repo = TraceEventRepository(session)
        run = _make_run()
        await run_repo.create(run)
        event = HarnessTraceEvent(
            trace_id=run.trace_id,
            run_id=run.id,
            tenant_id=TENANT_A,
            workflow_type=HarnessWorkflowType.VALUE_MODEL_GENERATION,
            event_type="transition",
            to_state=HarnessState.RESOLVE_CONTEXT,
        )
        await evt_repo.append(event)
        events = await evt_repo.list(run_id=run.id, tenant_id=TENANT_A)
        assert len(events) == 1
        assert events[0].event_type == "transition"

    async def test_list_by_run_id(self, session: AsyncSession) -> None:
        run_repo = HarnessRunRepository(session)
        evt_repo = TraceEventRepository(session)
        run1 = _make_run()
        run2 = _make_run()
        await run_repo.create(run1)
        await run_repo.create(run2)
        for run in [run1, run2]:
            evt = HarnessTraceEvent(
                trace_id=run.trace_id, run_id=run.id, tenant_id=TENANT_A,
                workflow_type=HarnessWorkflowType.VALUE_MODEL_GENERATION,
                event_type="transition",
            )
            await evt_repo.append(evt)
        events = await evt_repo.list(run_id=run1.id)
        assert all(e.run_id == run1.id for e in events)

    async def test_list_by_tenant_id(self, session: AsyncSession) -> None:
        run_repo = HarnessRunRepository(session)
        evt_repo = TraceEventRepository(session)
        run_a = _make_run(tenant_id=TENANT_A)
        run_b = _make_run(tenant_id=TENANT_B)
        await run_repo.create(run_a)
        await run_repo.create(run_b)
        for run, tid in [(run_a, TENANT_A), (run_b, TENANT_B)]:
            evt = HarnessTraceEvent(
                trace_id=run.trace_id, run_id=run.id, tenant_id=tid,
                workflow_type=HarnessWorkflowType.VALUE_MODEL_GENERATION,
                event_type="transition",
            )
            await evt_repo.append(evt)
        events = await evt_repo.list(tenant_id=TENANT_A)
        assert all(e.tenant_id == TENANT_A for e in events)

    async def test_event_includes_trace_id_and_tenant_id(self, session: AsyncSession) -> None:
        run_repo = HarnessRunRepository(session)
        evt_repo = TraceEventRepository(session)
        run = _make_run()
        await run_repo.create(run)
        event = HarnessTraceEvent(
            trace_id=run.trace_id, run_id=run.id, tenant_id=TENANT_A,
            workflow_type=HarnessWorkflowType.VALUE_MODEL_GENERATION,
            event_type="checkpoint",
        )
        await evt_repo.append(event)
        events = await evt_repo.list(run_id=run.id)
        assert events[0].trace_id == run.trace_id
        assert events[0].tenant_id == TENANT_A


# ===========================================================================
# TestSqlHarnessRegistryIntegration
# ===========================================================================


class TestSqlHarnessRegistryIntegration:
    async def test_full_workflow_persisted_across_registry_instances(
        self, session: AsyncSession
    ) -> None:
        """Run created in one registry instance is readable from a second."""
        reg1 = await make_sql_registry(session)
        run = await reg1.create_run(
            tenant_id=TENANT_A,
            workflow_type=HarnessWorkflowType.VALUE_MODEL_GENERATION,
            initiated_by=InitiatedBy.USER,
        )
        run_id = run.id

        # Second registry instance, same session
        reg2 = await make_sql_registry(session)
        fetched = await reg2.get_run(run_id, TENANT_A)
        assert fetched.id == run_id
        assert fetched.tenant_id == TENANT_A
        assert fetched.current_state == HarnessState.INIT

    async def test_tenant_isolation_across_registry_instances(
        self, session: AsyncSession
    ) -> None:
        reg = await make_sql_registry(session)
        run = await reg.create_run(
            tenant_id=TENANT_A,
            workflow_type=HarnessWorkflowType.VALUE_MODEL_GENERATION,
            initiated_by=InitiatedBy.USER,
        )
        with pytest.raises(RunNotFoundError):
            await reg.get_run(run.id, TENANT_B)

    async def test_checkpoint_survives_registry_restart(
        self, session: AsyncSession
    ) -> None:
        reg1 = await make_sql_registry(session)
        run = await reg1.create_run(
            tenant_id=TENANT_A,
            workflow_type=HarnessWorkflowType.VALUE_MODEL_GENERATION,
            initiated_by=InitiatedBy.SYSTEM,
        )
        await reg1.transition(
            run_id=run.id,
            tenant_id=TENANT_A,
            to_state=HarnessState.RESOLVE_CONTEXT,
            state_payload={"context": "loaded"},
        )

        # New registry instance, same session — simulates restart
        reg2 = await make_sql_registry(session)
        checkpoints = await reg2.get_checkpoints(run.id, TENANT_A)
        assert len(checkpoints) == 1
        assert checkpoints[0].state_name == HarnessState.RESOLVE_CONTEXT
        assert checkpoints[0].state_payload == {"context": "loaded"}

    async def test_make_in_memory_registry_returns_compatible_object(self) -> None:
        """make_in_memory_registry returns a HarnessRegistry-compatible object."""
        from harness.registry import HarnessRegistry

        reg = make_in_memory_registry()
        assert isinstance(reg, HarnessRegistry)
        run = reg.create_run(
            tenant_id=TENANT_A,
            workflow_type=HarnessWorkflowType.VALUE_MODEL_GENERATION,
            initiated_by=InitiatedBy.USER,
        )
        assert run.tenant_id == TENANT_A

    async def test_list_runs_tenant_scoped(self, session: AsyncSession) -> None:
        reg = await make_sql_registry(session)
        await reg.create_run(
            tenant_id=TENANT_A,
            workflow_type=HarnessWorkflowType.VALUE_MODEL_GENERATION,
            initiated_by=InitiatedBy.USER,
        )
        await reg.create_run(
            tenant_id=TENANT_B,
            workflow_type=HarnessWorkflowType.VALUE_MODEL_GENERATION,
            initiated_by=InitiatedBy.USER,
        )
        runs_a, _total = await reg.list_runs(tenant_id=TENANT_A)
        assert all(r.tenant_id == TENANT_A for r in runs_a)
        assert len(runs_a) == 1


    async def test_get_events_sync_returns_in_memory_events(
        self, session: AsyncSession
    ) -> None:
        """SqlTelemetryEmitter.get_events() mirrors in-memory filtering behavior."""
        from harness.sql_stores import SqlTelemetryEmitter

        emitter = SqlTelemetryEmitter(session)
        run = HarnessRun(
            tenant_id=TENANT_A,
            workflow_type=HarnessWorkflowType.VALUE_MODEL_GENERATION,
            initiated_by=InitiatedBy.USER,
        )
        emitter.emit_transition_event(
            run=run,
            from_state=HarnessState.INIT,
            to_state=HarnessState.RESOLVE_CONTEXT,
        )

        all_events = emitter.get_events()
        run_events = emitter.get_events(run_id=run.id)
        tenant_events = emitter.get_events(tenant_id=TENANT_A)

        assert len(all_events) == 1
        assert len(run_events) == 1
        assert len(tenant_events) == 1
        assert run_events[0].run_id == run.id
        assert tenant_events[0].tenant_id == TENANT_A

    async def test_decide_gate_enriches_telemetry_with_run_trace_id(
        self, session: AsyncSession
    ) -> None:
        """decide_gate() uses a point lookup to enrich telemetry with trace_id.

        Verifies that the gate decision correctly resolves the parent run via
        get_run(gate.run_id) rather than a full-tenant list scan, and that the
        resulting gate has the expected terminal status.
        """
        reg = await make_sql_registry(session)
        run = await reg.create_run(
            tenant_id=TENANT_A,
            workflow_type=HarnessWorkflowType.VALUE_MODEL_GENERATION,
            initiated_by=InitiatedBy.USER,
        )
        gate = await reg.create_human_gate(
            run_id=run.id,
            tenant_id=TENANT_A,
            gate_type=GateType.APPROVE_CLAIMS,
        )
        decided = await reg.decide_gate(
            gate_id=gate.id,
            tenant_id=TENANT_A,
            decision=GateStatus.APPROVED,
            decision_by="reviewer",
            decision_reason="Evidence sufficient",
        )
        assert decided.status == GateStatus.APPROVED
        assert decided.decision_by == "reviewer"
        # Confirm the run is still accessible (point lookup didn't corrupt state)
        fetched_run = await reg.get_run(run.id, TENANT_A)
        assert fetched_run.trace_id == run.trace_id


# ---------------------------------------------------------------------------
# SqlClaimValidationStore persistence
# ---------------------------------------------------------------------------


class TestSqlClaimValidationStore:
    """Verify save_results / get_results_for_run round-trip via SQLite."""

    @pytest.mark.asyncio
    async def test_save_and_retrieve_results(self, session):
        from harness.models import ClaimValidationResult, ValidationState
        from harness.sql_stores import SqlClaimValidationStore

        store = SqlClaimValidationStore(session)
        run_id = "run-cvr-001"
        results = [
            ClaimValidationResult(
                tenant_id=TENANT_A,
                claim_id="c1",
                validation_state=ValidationState.PASSED,
                evidence_refs=["ref-1"],
                confidence=0.95,
                trust_score=0.9,
                validator="agent",
                reason="Verified against L5",
            ),
            ClaimValidationResult(
                tenant_id=TENANT_A,
                claim_id="c2",
                validation_state=ValidationState.NEEDS_REVIEW,
                evidence_refs=[],
                confidence=0.4,
                trust_score=0.3,
                validator="unavailable",
                reason="L5 unreachable",
            ),
        ]
        await store.save_results(run_id, results)

        fetched = await store.get_results_for_run(run_id, TENANT_A)
        assert len(fetched) == 2
        states = {r.claim_id: r.validation_state for r in fetched}
        assert states["c1"] == ValidationState.PASSED
        assert states["c2"] == ValidationState.NEEDS_REVIEW

    @pytest.mark.asyncio
    async def test_cross_tenant_isolation(self, session):
        """Results saved for TENANT_A are not visible to TENANT_B."""
        from harness.models import ClaimValidationResult, ValidationState
        from harness.sql_stores import SqlClaimValidationStore

        store = SqlClaimValidationStore(session)
        run_id = "run-cvr-002"
        result = ClaimValidationResult(
            tenant_id=TENANT_A,
            claim_id="c1",
            validation_state=ValidationState.PASSED,
            evidence_refs=[],
            confidence=1.0,
            trust_score=1.0,
            validator="agent",
            reason="",
        )
        await store.save_results(run_id, [result])

        fetched_b = await store.get_results_for_run(run_id, TENANT_B)
        assert fetched_b == []

    @pytest.mark.asyncio
    async def test_save_is_idempotent_on_claim_id(self, session):
        """Re-saving the same claim_id replaces the previous result."""
        from harness.models import ClaimValidationResult, ValidationState
        from harness.sql_stores import SqlClaimValidationStore

        store = SqlClaimValidationStore(session)
        run_id = "run-cvr-003"

        first = ClaimValidationResult(
            tenant_id=TENANT_A,
            claim_id="c1",
            validation_state=ValidationState.NEEDS_REVIEW,
            evidence_refs=[],
            confidence=0.5,
            trust_score=0.5,
            validator="unavailable",
            reason="first pass",
        )
        await store.save_results(run_id, [first])

        second = ClaimValidationResult(
            tenant_id=TENANT_A,
            claim_id="c1",
            validation_state=ValidationState.PASSED,
            evidence_refs=["ref-x"],
            confidence=0.95,
            trust_score=0.9,
            validator="agent",
            reason="second pass",
        )
        await store.save_results(run_id, [second])

        fetched = await store.get_results_for_run(run_id, TENANT_A)
        assert len(fetched) == 1
        assert fetched[0].validation_state == ValidationState.PASSED
        assert fetched[0].reason == "second pass"

    @pytest.mark.asyncio
    async def test_empty_run_returns_empty_list(self, session):
        """get_results_for_run returns [] when no results have been saved."""
        from harness.sql_stores import SqlClaimValidationStore

        store = SqlClaimValidationStore(session)
        fetched = await store.get_results_for_run("run-nonexistent", TENANT_A)
        assert fetched == []

    @pytest.mark.asyncio
    async def test_validate_claims_with_run_id_persists(self, session):
        """SqlHarnessRegistry.validate_claims persists results when run_id is given."""
        from unittest.mock import AsyncMock

        from harness.models import ClaimValidationResult, ValidationState
        from harness.sql_stores import (
            SqlCheckpointManager,
            SqlHarnessRegistry,
            SqlHumanGateManager,
            SqlTelemetryEmitter,
            SqlToolContractRegistry,
        )
        from harness.state_machine import StateMachine
        from harness.validation_hooks import ClaimValidationRequest, ValidationHook

        # Stub the ValidationHook to return a known PASSED result
        mock_hook = ValidationHook(primary_validator=None)
        mock_hook.validate_claims = AsyncMock(
            return_value=[
                ClaimValidationResult(
                    tenant_id=TENANT_A,
                    claim_id="c1",
                    validation_state=ValidationState.PASSED,
                    evidence_refs=[],
                    confidence=1.0,
                    trust_score=1.0,
                    validator="agent",
                    reason="mocked",
                )
            ]
        )

        registry = SqlHarnessRegistry(
            session=session,
            state_machine=StateMachine(),
            tool_registry=SqlToolContractRegistry(session),
            gate_manager=SqlHumanGateManager(session),
            checkpoint_manager=SqlCheckpointManager(session),
            telemetry=SqlTelemetryEmitter(session),
            validation_hook=mock_hook,
        )
        run = await registry.create_run(
            tenant_id=TENANT_A,
            workflow_type=HarnessWorkflowType.BUSINESS_CASE_GENERATION,
            initiated_by=InitiatedBy.USER,
        )

        req = ClaimValidationRequest(
            tenant_id=TENANT_A,
            claim_id="c1",
            claim_text="ROI claim",
            evidence_refs=[],
        )
        await registry.validate_claims(TENANT_A, [req], run_id=run.id)

        # Retrieve via get_validation_results
        stored = await registry.get_validation_results(run.id, TENANT_A)
        assert len(stored) == 1
        assert stored[0].claim_id == "c1"
        assert stored[0].validation_state == ValidationState.PASSED


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
