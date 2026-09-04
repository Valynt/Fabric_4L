"""Phase 5 event-bus tests for the Agent Runtime observability slice.

Covers the ``RuntimeEvent`` contract, the 9 event-kind constants, the
``EventSink`` protocol, and ``RuntimeEventBus`` fan-out semantics
(registration order, idempotency, unregister, and fail-open isolation of a
misbehaving sink).
"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from layer4_agents.runtime import (
    CHECKPOINT_SAVED,
    RUN_CANCELLED,
    RUN_COMPLETED,
    RUN_FAILED,
    RUN_PAUSED,
    RUN_RESUMED,
    RUN_STARTED,
    TOOL_CALLED,
    TOOL_DENIED,
    EventSink,
    RuntimeEvent,
    RuntimeEventBus,
)

pytestmark = pytest.mark.unit

_ALL_KINDS = (
    RUN_STARTED,
    RUN_COMPLETED,
    RUN_FAILED,
    RUN_PAUSED,
    RUN_CANCELLED,
    RUN_RESUMED,
    TOOL_CALLED,
    TOOL_DENIED,
    CHECKPOINT_SAVED,
)


class _RecordingSink:
    """EventSink that records every event it receives."""

    def __init__(self) -> None:
        self.events: list[RuntimeEvent] = []

    async def publish(self, event: RuntimeEvent) -> None:
        self.events.append(event)


class _RaisingSink:
    """EventSink that always fails; used to prove fail-open bus semantics."""

    async def publish(self, event: RuntimeEvent) -> None:
        raise RuntimeError("sink exploded")


def _event(**overrides: Any) -> RuntimeEvent:
    base = {"kind": RUN_STARTED, "run_id": "run-1", "tenant_id": "tenant-a"}
    base.update(overrides)
    return RuntimeEvent(**base)


def test_event_kind_constants_are_stable_dotted_names() -> None:
    assert _ALL_KINDS == (
        "run.started",
        "run.completed",
        "run.failed",
        "run.paused",
        "run.cancelled",
        "run.resumed",
        "tool.called",
        "tool.denied",
        "checkpoint.saved",
    )


def test_runtime_event_defaults_and_occurred_at() -> None:
    event = RuntimeEvent(kind=RUN_STARTED, run_id="run-1")

    assert event.tenant_id is None
    assert event.workflow_type is None
    assert event.tool_name is None
    assert event.status is None
    assert event.payload == {}
    assert isinstance(event.occurred_at, str)
    # occurred_at defaults to an ISO-8601 timestamp with timezone.
    assert "T" in event.occurred_at
    assert event.occurred_at.endswith("+00:00") or "+00:00" in event.occurred_at


def test_runtime_event_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        RuntimeEvent(kind=RUN_STARTED, unexpected="boom")


def test_recording_sink_satisfies_event_sink_protocol() -> None:
    assert isinstance(_RecordingSink(), EventSink)


def test_runtime_event_bus_is_an_event_sink() -> None:
    # Buses can be chained because the bus itself implements EventSink.
    assert isinstance(RuntimeEventBus(), EventSink)


@pytest.mark.asyncio
async def test_bus_register_is_idempotent_and_sink_count_tracks() -> None:
    bus = RuntimeEventBus()
    sink = _RecordingSink()
    assert bus.sink_count() == 0

    bus.register(sink)
    bus.register(sink)
    assert bus.sink_count() == 1

    bus.register(_RecordingSink())
    assert bus.sink_count() == 2


@pytest.mark.asyncio
async def test_bus_unregister_removes_sink_and_absent_is_noop() -> None:
    bus = RuntimeEventBus()
    sink = _RecordingSink()
    bus.register(sink)
    assert bus.sink_count() == 1

    bus.unregister(sink)
    assert bus.sink_count() == 0

    # Unregistering an absent sink must not raise.
    bus.unregister(sink)


@pytest.mark.asyncio
async def test_bus_fans_event_out_to_all_sinks_in_registration_order() -> None:
    bus = RuntimeEventBus()
    first = _RecordingSink()
    second = _RecordingSink()
    bus.register(first)
    bus.register(second)
    event = _event()

    await bus.publish(event)

    assert first.events == [event]
    assert second.events == [event]


@pytest.mark.asyncio
async def test_bus_fails_open_when_a_sink_raises() -> None:
    bus = RuntimeEventBus()
    recorder = _RecordingSink()
    bus.register(_RaisingSink())
    bus.register(recorder)
    event = _event(kind=TOOL_CALLED)

    # publish must not raise even though the first sink blows up.
    await bus.publish(event)

    assert recorder.events == [event]
