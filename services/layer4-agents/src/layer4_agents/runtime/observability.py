"""Runtime metrics and operational helpers.

Two layers live here:

- ``RuntimeMetrics`` — a thread-safe, in-process metrics collector that also
  implements ``EventSink``. Register it on a ``RuntimeEventBus`` (or pass it as
  the runtime's event bus) and it derives Prometheus-friendly counters purely
  from the event stream: runs started / terminal by status, tool calls allowed
  and denied, and checkpoints saved. ``snapshot()`` exposes plain dict views
  for introspection and tests.
- ``find_stale_runs`` — stuck-run detection over stored ``RunResult`` records:
  an active run (pending/running/retrying) that has not progressed past a
  threshold age is reported so an operator can cancel or requeue it.

Neither layer depends on a metrics vendor, keeping the runtime provider-agnostic
(plan: every span/counter carries run/tenant context, but never vendor wiring).
"""

from __future__ import annotations

import threading
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from typing import Any

from .events import (
    CHECKPOINT_SAVED,
    RUN_CANCELLED,
    RUN_COMPLETED,
    RUN_FAILED,
    RUN_PAUSED,
    RUN_RESUMED,
    RUN_STARTED,
    TOOL_CALLED,
    TOOL_DENIED,
    RuntimeEvent,
)
from .models import RunResult, RunStatus

#: Statuses that mean a run is still active and eligible for stale detection.
_ACTIVE_STATUSES = frozenset(
    {RunStatus.PENDING, RunStatus.RUNNING, RunStatus.RETRYING}
)

#: Event kinds that mark the end of a run lifecycle (not resumable).
_TERMINAL_KINDS = frozenset({RUN_COMPLETED, RUN_FAILED, RUN_CANCELLED})

#: Mapping from terminal event kind to the recorded status label.
_KIND_TO_STATUS = {
    RUN_COMPLETED: RunStatus.COMPLETED.value,
    RUN_FAILED: RunStatus.FAILED.value,
    RUN_CANCELLED: RunStatus.CANCELLED.value,
}

#: Default bound on distinct labels tracked per label map. Beyond the cap,
#: aggregate totals keep counting but new labels are no longer tracked
#: individually, so in-process memory grows to a fixed ceiling.
DEFAULT_MAX_LABEL_CARDINALITY = 1024


class RuntimeMetrics:
    """Thread-safe counters derived from the runtime event stream.

    Implements ``EventSink`` so it can be registered directly on a
    ``RuntimeEventBus``. Runs are broken down by tenant and workflow
    type as internal-only label maps (aggregate counts keyed by label;
    no per-tenant content values). Tool counters are not tenant-labeled
    to bound cardinality.

    Every label map is cardinality-capped at ``max_label_cardinality``
    distinct keys (default 1024). Once the cap is reached, aggregate
    totals keep counting all events while previously-tracked labels
    continue to be updated; new labels are simply not tracked. This
    bounds memory usage in production where tenant and workflow-type
    cardinality is open-ended.
    """

    def __init__(
        self, *, max_label_cardinality: int = DEFAULT_MAX_LABEL_CARDINALITY
    ) -> None:
        if max_label_cardinality < 1:
            raise ValueError(
                "max_label_cardinality must be a positive integer, got "
                f"{max_label_cardinality}"
            )
        self._max_label_cardinality = max_label_cardinality
        self._lock = threading.Lock()
        self._runs_started_total = 0
        self._runs_started_by_tenant: dict[str, int] = {}
        self._runs_started_by_workflow_type: dict[str, int] = {}
        self._runs_terminal_total = 0
        self._runs_terminal_by_status: dict[str, int] = {}
        self._runs_paused_total = 0
        self._runs_resumed_total = 0
        self._tool_calls_total = 0
        self._tool_calls_allowed_total = 0
        self._tool_calls_denied_total = 0
        self._tool_calls_by_tool: dict[str, int] = {}
        self._checkpoints_saved_total = 0

    async def publish(self, event: RuntimeEvent) -> None:
        """Update counters from a single ``RuntimeEvent``."""
        kind = event.kind
        with self._lock:
            if kind == RUN_STARTED:
                self._runs_started_total += 1
                if event.tenant_id:
                    self._bump(self._runs_started_by_tenant, event.tenant_id)
                if event.workflow_type:
                    self._bump(
                        self._runs_started_by_workflow_type, event.workflow_type
                    )
            elif kind in _TERMINAL_KINDS:
                self._runs_terminal_total += 1
                status = _KIND_TO_STATUS[kind]
                self._bump(self._runs_terminal_by_status, status)
            elif kind == RUN_PAUSED:
                # A pause is not terminal: the run is resumable, so it is
                # tracked separately from terminal transitions.
                self._runs_paused_total += 1
            elif kind == RUN_RESUMED:
                self._runs_resumed_total += 1
            elif kind in (TOOL_CALLED, TOOL_DENIED):
                self._tool_calls_total += 1
                if kind == TOOL_CALLED:
                    self._tool_calls_allowed_total += 1
                else:
                    self._tool_calls_denied_total += 1
                if event.tool_name:
                    self._bump(self._tool_calls_by_tool, event.tool_name)
            elif kind == CHECKPOINT_SAVED:
                self._checkpoints_saved_total += 1
            # Unknown kinds belong to other observers and are ignored.

    def _bump(self, counter: dict[str, int], key: str) -> None:
        """Increment a label counter under an explicit cardinality cap.

        Once ``len(counter)`` reaches ``max_label_cardinality`` and ``key``
        is not already tracked, the label is skipped: aggregate totals
        (maintained by the callers) keep counting, but the map stops
        growing so memory stays bounded.
        """
        if key not in counter and len(counter) >= self._max_label_cardinality:
            return
        counter[key] = counter.get(key, 0) + 1

    def snapshot(self) -> dict[str, Any]:
        """Return a deep-ish copy of all counters as a flat JSON-safe dict."""
        with self._lock:
            return {
                "runs_started_total": self._runs_started_total,
                "runs_started_by_tenant": dict(self._runs_started_by_tenant),
                "runs_started_by_workflow_type": dict(
                    self._runs_started_by_workflow_type
                ),
                "runs_terminal_total": self._runs_terminal_total,
                "runs_terminal_by_status": dict(self._runs_terminal_by_status),
                "runs_paused_total": self._runs_paused_total,
                "runs_resumed_total": self._runs_resumed_total,
                "tool_calls_total": self._tool_calls_total,
                "tool_calls_allowed_total": self._tool_calls_allowed_total,
                "tool_calls_denied_total": self._tool_calls_denied_total,
                "tool_calls_by_tool": dict(self._tool_calls_by_tool),
                "checkpoints_saved_total": self._checkpoints_saved_total,
            }


def find_stale_runs(
    runs: Iterable[RunResult],
    *,
    now: datetime | None = None,
    stale_after: timedelta = timedelta(minutes=5),
) -> list[str]:
    """Return ids of active runs that have not progressed past ``stale_after``.

    A run is eligible only when its status is still active (pending, running,
    or retrying). The reference timestamp is ``started_at`` when present and
    otherwise ``created_at``; an unparseable timestamp causes the run to be
    skipped (it cannot be judged stale). The result is stable: runs are
    returned in input order.
    """
    now = now or datetime.now(UTC)
    stale: list[str] = []
    for run in runs:
        if run.status not in _ACTIVE_STATUSES:
            continue
        raw = run.started_at or run.created_at
        try:
            ts = datetime.fromisoformat(raw)
        except (TypeError, ValueError):
            continue
        # Normalize naive stored timestamps to UTC so the age comparison never
        # mixes aware and naive datetimes (which would raise TypeError).
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)
        if now - ts > stale_after:
            stale.append(run.run_id)
    return stale
