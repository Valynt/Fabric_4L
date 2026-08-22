from __future__ import annotations

from datetime import UTC, datetime

import pytest

from layer4_agents.models.agent_state import WorkflowStatus, WorkflowType
from layer4_agents.policies.replay_conflict import ReplayConflictError
from layer4_agents.workflows.replay import (
    Layer4WorkflowReplayHarness,
    ReplayAuthorizationContext,
    ReplayEventEnvelopeV1,
)


class _AuditSink:
    def __init__(self) -> None:
        self.records: list[tuple[str, dict]] = []

    def record(self, action: str, details: dict) -> None:
        self.records.append((action, details))


class _InMemoryEventStream:
    def __init__(self, events: list[ReplayEventEnvelopeV1]) -> None:
        self._events = events
        self.calls: list[tuple[str, str, str]] = []

    def list_events(self, *, tenant_id: str, workflow_id: str, domain: str = "layer4.workflow_state") -> list[ReplayEventEnvelopeV1]:
        self.calls.append((tenant_id, workflow_id, domain))
        return list(self._events)


def _evt(event_id: str, event_type: str, ts: int, payload: dict | None = None) -> ReplayEventEnvelopeV1:
    return ReplayEventEnvelopeV1(
        event_id=event_id,
        tenant_id="tenant-a",
        actor="user:alice",
        timestamp=datetime(2026, 1, 1, 0, 0, ts, tzinfo=UTC),
        correlation_id="corr-1",
        schema_version="1.0",
        domain="layer4.workflow_state",
        event_type=event_type,
        payload_pointer=f"s3://replay/{event_id}.json",
        payload_checksum="sha256:abc",
        payload_redacted=payload or {},
    )


def test_replay_is_deterministic_for_historical_events() -> None:
    sink = _AuditSink()
    harness = Layer4WorkflowReplayHarness(sink)
    authz = ReplayAuthorizationContext(
        tenant_id="tenant-a", actor="replay-bot", roles=("replay:execute",), environment="test"
    )
    events = [
        _evt("e2", "workflow.started", 2),
        _evt("e1", "workflow.created", 1),
        _evt("e3", "workflow.node_transition", 3, {"current_node": "roi_compute"}),
        _evt("e4", "workflow.completed", 4, {"roi": 12.3}),
    ]

    result_a = harness.replay(workflow_id="wf-1", workflow_type=WorkflowType.ROI_CALCULATOR, events=events, authz=authz)
    result_b = harness.replay(workflow_id="wf-1", workflow_type=WorkflowType.ROI_CALCULATOR, events=list(reversed(events)), authz=authz)

    assert result_a.applied_event_ids == ["e1", "e2", "e3", "e4"]
    assert result_a.applied_event_ids == result_b.applied_event_ids
    assert result_a.state.status == WorkflowStatus.COMPLETED
    assert result_a.state.current_node == "roi_compute"
    assert result_a.state.output_data == {"roi": 12.3}
    state_a = result_a.state.model_dump(exclude={"run_id", "trace_id"})
    state_b = result_b.state.model_dump(exclude={"run_id", "trace_id"})
    assert state_a == state_b


def test_replay_rejects_cross_tenant_events() -> None:
    sink = _AuditSink()
    harness = Layer4WorkflowReplayHarness(sink)
    authz = ReplayAuthorizationContext(
        tenant_id="tenant-a", actor="replay-bot", roles=("replay:execute",), environment="test"
    )
    bad = _evt("e1", "workflow.created", 1)
    bad = bad.model_copy(update={"tenant_id": "tenant-b"})

    with pytest.raises(PermissionError, match="Cross-tenant replay"):
        harness.replay(workflow_id="wf-1", workflow_type=WorkflowType.ROI_CALCULATOR, events=[bad], authz=authz)


def test_replay_from_stream_uses_tenant_scoped_query_and_is_deterministic() -> None:
    sink = _AuditSink()
    harness = Layer4WorkflowReplayHarness(sink)
    authz = ReplayAuthorizationContext(
        tenant_id="tenant-a", actor="replay-bot", roles=("replay:execute",), environment="test"
    )
    events = [
        _evt("e2", "workflow.started", 2),
        _evt("e1", "workflow.created", 1),
        _evt("e3", "workflow.completed", 3, {"result": "ok"}),
    ]
    stream = _InMemoryEventStream(events)

    result = harness.replay_from_stream(
        workflow_id="wf-stream", workflow_type=WorkflowType.ROI_CALCULATOR, stream=stream, authz=authz
    )

    assert stream.calls == [("tenant-a", "wf-stream", "layer4.workflow_state")]
    assert result.applied_event_ids == ["e1", "e2", "e3"]
    assert result.state.status == WorkflowStatus.COMPLETED


def test_replay_policy_rejects_duplicate_run_event_ids_and_audits_decision() -> None:
    sink = _AuditSink()
    harness = Layer4WorkflowReplayHarness(sink)
    authz = ReplayAuthorizationContext(tenant_id="tenant-a", actor="bot", roles=("replay:execute",), environment="test")
    events = [_evt("dup", "workflow.created", 1), _evt("dup", "workflow.started", 2)]

    with pytest.raises(ReplayConflictError, match="duplicate run event IDs"):
        harness.replay(workflow_id="wf-dups", workflow_type=WorkflowType.ROI_CALCULATOR, events=events, authz=authz)

    assert sink.records[-1][0] == "layer4.workflow.replay.policy_decision"
    assert sink.records[-1][1]["decision"] == "reject"


def test_replay_policy_marks_stale_schema_as_force_replay_and_audits_decision() -> None:
    sink = _AuditSink()
    harness = Layer4WorkflowReplayHarness(sink)
    authz = ReplayAuthorizationContext(tenant_id="tenant-a", actor="bot", roles=("replay:execute",), environment="test")
    stale = _evt("e1", "workflow.created", 1).model_copy(update={"schema_version": "0.9"})

    result = harness.replay(workflow_id="wf-stale", workflow_type=WorkflowType.ROI_CALCULATOR, events=[stale], authz=authz)
    assert result.applied_event_ids == ["e1"]
    assert sink.records[0][1]["decision"] == "force-replay"


def test_replay_policy_rejects_concurrent_resume_replay_attempts() -> None:
    sink = _AuditSink()
    harness = Layer4WorkflowReplayHarness(sink)
    authz = ReplayAuthorizationContext(tenant_id="tenant-a", actor="bot", roles=("replay:execute",), environment="test")
    events = [_evt("e1", "workflow.created", 1)]
    fp = harness._resolver.compute_replay_fingerprint("wf-concurrent", "tenant-a", None)
    harness._active_replays.add(fp)

    with pytest.raises(ReplayConflictError, match="concurrent replay attempt"):
        harness.replay(workflow_id="wf-concurrent", workflow_type=WorkflowType.ROI_CALCULATOR, events=events, authz=authz)

    assert sink.records[-1][1]["reason"] == "concurrent_attempt"
