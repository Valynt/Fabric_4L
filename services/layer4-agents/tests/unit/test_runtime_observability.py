"""Phase 5 observability tests: RuntimeMetrics counters and stale-run detection.

Covers the ``RuntimeMetrics`` event-sink collector (runs started/terminal by
status, pause/resume, tool calls allowed/denied by tool, checkpoints saved) and
``find_stale_runs`` stuck-run detection over stored ``RunResult`` records
(active-status eligibility, started_at vs created_at fallback, UTC
normalization of naive timestamps, unparseable-timestamp skips).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

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
    RunResult,
    RunStatus,
    RuntimeEvent,
    RuntimeMetrics,
    find_stale_runs,
)

pytestmark = pytest.mark.unit


def _event(**overrides: Any) -> RuntimeEvent:
    base = {
        "kind": RUN_STARTED,
        "run_id": "run-1",
        "tenant_id": "tenant-a",
        "workflow_type": "demo",
    }
    base.update(overrides)
    return RuntimeEvent(**base)


def _result(
    run_id: str,
    status: RunStatus,
    *,
    started_at: str | None = None,
    created_at: str | None = None,
) -> RunResult:
    return RunResult(
        run_id=run_id,
        workflow_id=run_id,
        trace_id="trace-1",
        tenant_id="tenant-a",
        workflow_type="demo",
        status=status,
        created_at=created_at or datetime.now(UTC).isoformat(),
        started_at=started_at,
    )


def test_runtime_metrics_satisfies_event_sink_protocol() -> None:
    assert isinstance(RuntimeMetrics(), EventSink)


async def test_runtime_metrics_empty_snapshot_is_zeroed() -> None:
    snapshot = RuntimeMetrics().snapshot()

    assert snapshot["runs_started_total"] == 0
    assert snapshot["runs_terminal_total"] == 0
    assert snapshot["runs_paused_total"] == 0
    assert snapshot["runs_resumed_total"] == 0
    assert snapshot["tool_calls_total"] == 0
    assert snapshot["tool_calls_allowed_total"] == 0
    assert snapshot["tool_calls_denied_total"] == 0
    assert snapshot["checkpoints_saved_total"] == 0
    assert snapshot["runs_started_by_tenant"] == {}
    assert snapshot["runs_terminal_by_status"] == {}
    assert snapshot["tool_calls_by_tool"] == {}


async def test_runtime_metrics_counts_started_runs_with_tenant_and_workflow_labels() -> None:
    metrics = RuntimeMetrics()
    await metrics.publish(
        _event(kind=RUN_STARTED, tenant_id="tenant-a", workflow_type="roi")
    )
    await metrics.publish(
        _event(kind=RUN_STARTED, tenant_id="tenant-b", workflow_type="audit")
    )
    await metrics.publish(
        _event(kind=RUN_STARTED, tenant_id="tenant-a", workflow_type="audit")
    )

    snapshot = metrics.snapshot()
    assert snapshot["runs_started_total"] == 3
    assert snapshot["runs_started_by_tenant"] == {"tenant-a": 2, "tenant-b": 1}
    assert snapshot["runs_started_by_workflow_type"] == {"roi": 1, "audit": 2}


async def test_runtime_metrics_counts_terminal_runs_by_status() -> None:
    metrics = RuntimeMetrics()
    for kind, status in (
        (RUN_COMPLETED, RunStatus.COMPLETED.value),
        (RUN_FAILED, RunStatus.FAILED.value),
        (RUN_CANCELLED, RunStatus.CANCELLED.value),
    ):
        await metrics.publish(_event(kind=kind, status=status))

    snapshot = metrics.snapshot()
    assert snapshot["runs_terminal_total"] == 3
    assert snapshot["runs_terminal_by_status"] == {
        "completed": 1,
        "failed": 1,
        "cancelled": 1,
    }


async def test_runtime_metrics_pause_is_not_a_terminal_transition() -> None:
    metrics = RuntimeMetrics()
    await metrics.publish(_event(kind=RUN_PAUSED, status=RunStatus.PAUSED.value))

    snapshot = metrics.snapshot()
    assert snapshot["runs_paused_total"] == 1
    # A pause is resumable: it must NOT appear as a terminal run.
    assert snapshot["runs_terminal_total"] == 0
    assert snapshot["runs_terminal_by_status"] == {}


async def test_runtime_metrics_resume_is_counted_separately() -> None:
    metrics = RuntimeMetrics()
    await metrics.publish(_event(kind=RUN_PAUSED, status=RunStatus.PAUSED.value))
    await metrics.publish(
        _event(kind=RUN_RESUMED, status=RunStatus.COMPLETED.value)
    )

    snapshot = metrics.snapshot()
    assert snapshot["runs_paused_total"] == 1
    assert snapshot["runs_resumed_total"] == 1
    assert snapshot["runs_terminal_total"] == 0


async def test_runtime_metrics_counts_tool_calls_allowed_and_denied_by_tool() -> None:
    metrics = RuntimeMetrics()
    await metrics.publish(_event(kind=TOOL_CALLED, tool_name="search"))
    await metrics.publish(_event(kind=TOOL_CALLED, tool_name="search"))
    await metrics.publish(_event(kind=TOOL_DENIED, tool_name="admin_delete"))
    await metrics.publish(_event(kind=TOOL_CALLED, tool_name="summarize"))

    snapshot = metrics.snapshot()
    assert snapshot["tool_calls_total"] == 4
    assert snapshot["tool_calls_allowed_total"] == 3
    assert snapshot["tool_calls_denied_total"] == 1
    assert snapshot["tool_calls_by_tool"] == {
        "search": 2,
        "admin_delete": 1,
        "summarize": 1,
    }


async def test_runtime_metrics_counts_checkpoints_saved() -> None:
    metrics = RuntimeMetrics()
    await metrics.publish(_event(kind=CHECKPOINT_SAVED))

    snapshot = metrics.snapshot()
    assert snapshot["checkpoints_saved_total"] == 1


async def test_runtime_metrics_ignores_unknown_event_kinds() -> None:
    metrics = RuntimeMetrics()
    # Unknown kinds belong to other observers and must not corrupt counters.
    await metrics.publish(_event(kind="run.unknown_signal"))

    snapshot = metrics.snapshot()
    assert snapshot["runs_started_total"] == 0
    assert snapshot["runs_terminal_total"] == 0
    assert snapshot["tool_calls_total"] == 0


async def test_runtime_metrics_snapshot_returns_a_copy_not_live_state() -> None:
    metrics = RuntimeMetrics()
    await metrics.publish(_event(kind=RUN_STARTED, tenant_id="tenant-a"))

    snapshot = metrics.snapshot()
    snapshot["runs_started_total"] = 999
    snapshot["runs_started_by_tenant"]["tenant-a"] = 999

    fresh = metrics.snapshot()
    assert fresh["runs_started_total"] == 1
    assert fresh["runs_started_by_tenant"] == {"tenant-a": 1}


# ---------------------------------------------------------------------------
# Label-map cardinality cap
# ---------------------------------------------------------------------------


async def test_runtime_metrics_caps_tenant_label_cardinality() -> None:
    metrics = RuntimeMetrics(max_label_cardinality=2)
    for tenant in ("tenant-a", "tenant-b", "tenant-c"):
        await metrics.publish(_event(kind=RUN_STARTED, tenant_id=tenant))

    snapshot = metrics.snapshot()
    # Totals count every run; the label map stops growing past the cap.
    assert snapshot["runs_started_total"] == 3
    assert snapshot["runs_started_by_tenant"] == {"tenant-a": 1, "tenant-b": 1}


async def test_runtime_metrics_capped_labels_keep_counting_tracked_tenants() -> None:
    metrics = RuntimeMetrics(max_label_cardinality=2)
    await metrics.publish(_event(kind=RUN_STARTED, tenant_id="tenant-a"))
    await metrics.publish(_event(kind=RUN_STARTED, tenant_id="tenant-b"))
    # tenant-c exceeds the cap and is not tracked individually...
    await metrics.publish(_event(kind=RUN_STARTED, tenant_id="tenant-c"))
    # ...while already-tracked labels continue to be updated.
    await metrics.publish(_event(kind=RUN_STARTED, tenant_id="tenant-a"))

    snapshot = metrics.snapshot()
    assert snapshot["runs_started_total"] == 4
    assert snapshot["runs_started_by_tenant"] == {"tenant-a": 2, "tenant-b": 1}


async def test_runtime_metrics_caps_workflow_type_label_cardinality() -> None:
    metrics = RuntimeMetrics(max_label_cardinality=2)
    for workflow_type in ("roi", "audit", "business_case"):
        await metrics.publish(
            _event(kind=RUN_STARTED, workflow_type=workflow_type)
        )

    snapshot = metrics.snapshot()
    assert snapshot["runs_started_total"] == 3
    assert snapshot["runs_started_by_workflow_type"] == {"roi": 1, "audit": 1}


async def test_runtime_metrics_caps_tool_label_cardinality() -> None:
    metrics = RuntimeMetrics(max_label_cardinality=2)
    for tool_name in ("search", "summarize", "export"):
        await metrics.publish(_event(kind=TOOL_CALLED, tool_name=tool_name))

    snapshot = metrics.snapshot()
    # Aggregate tool totals are uncapped; the per-tool map stops at the cap.
    assert snapshot["tool_calls_total"] == 3
    assert snapshot["tool_calls_by_tool"] == {"search": 1, "summarize": 1}


def test_runtime_metrics_rejects_non_positive_cardinality_cap() -> None:
    with pytest.raises(ValueError):
        RuntimeMetrics(max_label_cardinality=0)
    with pytest.raises(ValueError):
        RuntimeMetrics(max_label_cardinality=-1)


# ---------------------------------------------------------------------------
# find_stale_runs
# ---------------------------------------------------------------------------


def test_find_stale_runs_reports_old_active_runs_in_input_order() -> None:
    now = datetime.now(UTC)
    stale_run = _result(
        "run-stale",
        RunStatus.RUNNING,
        started_at=(now - timedelta(minutes=10)).isoformat(),
    )
    stale_pending = _result(
        "run-stale-pending",
        RunStatus.PENDING,
        created_at=(now - timedelta(hours=1)).isoformat(),
    )
    fresh_run = _result(
        "run-fresh",
        RunStatus.RUNNING,
        started_at=(now - timedelta(seconds=30)).isoformat(),
    )

    stale = find_stale_runs([stale_run, stale_pending, fresh_run], now=now)

    assert stale == ["run-stale", "run-stale-pending"]


def test_find_stale_runs_ignores_terminal_and_paused_runs() -> None:
    now = datetime.now(UTC)
    old = (now - timedelta(hours=2)).isoformat()
    terminal_runs = [
        _result("run-completed", RunStatus.COMPLETED, started_at=old),
        _result("run-failed", RunStatus.FAILED, started_at=old),
        _result("run-cancelled", RunStatus.CANCELLED, started_at=old),
        # Paused is resumable, not stuck/active.
        _result("run-paused", RunStatus.PAUSED, started_at=old),
    ]

    assert find_stale_runs(terminal_runs, now=now) == []


def test_find_stale_runs_uses_created_at_when_started_at_absent() -> None:
    now = datetime.now(UTC)
    no_start = _result(
        "run-no-start",
        RunStatus.RUNNING,
        created_at=(now - timedelta(minutes=30)).isoformat(),
    )

    assert find_stale_runs([no_start], now=now) == ["run-no-start"]


def test_find_stale_runs_prefers_started_at_over_created_at() -> None:
    now = datetime.now(UTC)
    run = _result(
        "run-dual",
        RunStatus.RUNNING,
        started_at=(now - timedelta(minutes=10)).isoformat(),
        created_at=(now - timedelta(hours=5)).isoformat(),
    )

    # Even a 5h-old created_at would be stale; started_at governs the check.
    assert find_stale_runs([run], now=now) == ["run-dual"]


def test_find_stale_runs_honors_custom_threshold_and_now() -> None:
    now = datetime.now(UTC)
    borderline = _result(
        "run-border",
        RunStatus.RUNNING,
        started_at=(now - timedelta(minutes=5)).isoformat(),
    )

    assert find_stale_runs([borderline], now=now) == []
    assert (
        find_stale_runs(
            [borderline], now=now, stale_after=timedelta(minutes=3)
        )
        == ["run-border"]
    )


def test_find_stale_runs_normalizes_naive_timestamps_to_utc() -> None:
    now = datetime.now(UTC)
    # A naive timestamp (no tzinfo) from an older writer must not raise
    # TypeError. Naive stored timestamps are interpreted as UTC wall time, so
    # fixtures must be derived from the UTC clock (not local datetime.now()).
    utc_naive_now = now.replace(tzinfo=None)
    naive_old = _result(
        "run-naive",
        RunStatus.RUNNING,
        started_at=(utc_naive_now - timedelta(minutes=15)).isoformat(),
    )
    naive_fresh = _result(
        "run-naive-fresh",
        RunStatus.RUNNING,
        started_at=(utc_naive_now - timedelta(seconds=10)).isoformat(),
    )

    stale = find_stale_runs([naive_old, naive_fresh], now=now)

    assert stale == ["run-naive"]


def test_find_stale_runs_skips_unparseable_timestamps() -> None:
    now = datetime.now(UTC)
    garbage = _result("run-garbage", RunStatus.RUNNING, started_at="not-a-date")
    also_garbage = _result(
        "run-garbage-created", RunStatus.PENDING, created_at="never"
    )

    # Unparseable runs cannot be judged stale and are skipped, not raised on.
    assert find_stale_runs([garbage, also_garbage], now=now) == []


def test_find_stale_runs_empty_iterable_returns_empty() -> None:
    assert find_stale_runs([], now=datetime.now(UTC)) == []
