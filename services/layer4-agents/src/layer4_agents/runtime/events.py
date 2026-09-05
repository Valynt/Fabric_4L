"""Runtime event bus types and emit helpers.

The event bus is the observability channel of the Agent Runtime: lifecycle
transitions (run started/completed/failed/paused/cancelled/resumed), tool-call
attempts (allowed/denied), and persistence events (checkpoint saved) are
published as structured, JSON-safe ``RuntimeEvent`` messages to registered
``EventSink`` observers.

Observability is deliberately **fail-open**: a misbehaving sink must never
break runtime execution, so ``RuntimeEventBus.publish`` isolates sink failures.
The event vocabulary is the stable seam a metrics sink, an audit log, a
webhook notifier, or the Phase-5 introspection surface can attach to without
touching runtime internals.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)

# Event kinds (dotted namespace so sinks can group by prefix).
RUN_STARTED = "run.started"
RUN_COMPLETED = "run.completed"
RUN_FAILED = "run.failed"
RUN_PAUSED = "run.paused"
RUN_CANCELLED = "run.cancelled"
RUN_RESUMED = "run.resumed"
TOOL_CALLED = "tool.called"
TOOL_DENIED = "tool.denied"
CHECKPOINT_SAVED = "checkpoint.saved"


class RuntimeEvent(BaseModel):
    """A structured, JSON-safe observability event.

    Fields are intentionally sparse and never carry raw provider responses or
    secrets; ``payload`` is reserved for small operational details such as an
    error code or an authorization denial reason.
    """

    model_config = ConfigDict(extra="forbid")

    kind: str
    run_id: str | None = None
    tenant_id: str | None = None
    workflow_type: str | None = None
    tool_name: str | None = None
    status: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    occurred_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


@runtime_checkable
class EventSink(Protocol):
    """An observer that consumes runtime events."""

    async def publish(self, event: RuntimeEvent) -> None: ...


class RuntimeEventBus:
    """In-process fan-out bus implementing ``EventSink``.

    Sinks receive events in registration order. A sink that raises is logged
    and skipped so remaining sinks still receive the event (fail-open for
    observability). The bus itself is an ``EventSink``, so buses can be
    chained.
    """

    def __init__(self) -> None:
        self._sinks: list[EventSink] = []

    def register(self, sink: EventSink) -> None:
        """Register an event sink (idempotent)."""
        if sink not in self._sinks:
            self._sinks.append(sink)

    def unregister(self, sink: EventSink) -> None:
        """Remove a previously registered sink (no-op if absent)."""
        if sink in self._sinks:
            self._sinks.remove(sink)

    def sink_count(self) -> int:
        """Number of currently registered sinks."""
        return len(self._sinks)

    async def publish(self, event: RuntimeEvent) -> None:
        """Fan the event out to every registered sink, isolating failures."""
        for sink in list(self._sinks):
            try:
                await sink.publish(event)
            except Exception:
                logger.warning(
                    "runtime event sink failed while publishing kind=%s",
                    event.kind,
                    exc_info=True,
                )
