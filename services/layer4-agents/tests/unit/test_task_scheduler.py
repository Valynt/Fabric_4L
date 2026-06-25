from __future__ import annotations

"""Unit tests for the TaskScheduler and ScheduledTask.

Tests priority-based scheduling, backpressure, retry with exponential backoff,
tenant-context propagation, and task lifecycle.
"""


from datetime import UTC, datetime

import pytest

from layer4_agents.engine.scheduler import (
    ScheduledTask,
    TaskPriority,
    TaskScheduler,
    TaskStatus,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_task(
    task_id: str = "task-1",
    capability: str = "test_cap",
    priority: int = TaskPriority.NORMAL.value,
    tenant_id: str | None = "tenant-abc",
    max_retries: int = 0,
    scheduled_at: datetime | None = None,
) -> ScheduledTask:
    return ScheduledTask(
        priority=priority,
        scheduled_time=scheduled_at or datetime.now(UTC),
        task_id=task_id,
        workflow_instance_id="wf-test",
        capability=capability,
        agent_type="TestAgent",
        context={"tenant_id": tenant_id} if tenant_id else {},
        tenant_id=tenant_id,
        max_retries=max_retries,
    )


# ============================================================================
# ScheduledTask
# ============================================================================

class TestScheduledTask:
    """Tests for ScheduledTask data class."""

    @pytest.mark.unit
    def test_creation_with_defaults(self):
        """ScheduledTask can be created with minimal required fields."""
        task = _make_task()
        assert task.task_id == "task-1"
        assert task.status == TaskStatus.PENDING
        assert task.retry_count == 0
        assert task.started_at is None
        assert task.completed_at is None

    @pytest.mark.unit
    def test_get_tenant_id_from_explicit_field(self):
        """get_tenant_id() returns tenant_id when explicitly set."""
        task = _make_task(tenant_id="t-explicit")
        assert task.get_tenant_id() == "t-explicit"

    @pytest.mark.unit
    def test_get_tenant_id_falls_back_to_context(self):
        """get_tenant_id() falls back to context dict when tenant_id is None."""
        task = ScheduledTask(
            priority=TaskPriority.NORMAL.value,
            scheduled_time=datetime.now(UTC),
            task_id="t1",
            workflow_instance_id="wf",
            capability="cap",
            agent_type="Agent",
            context={"tenant_id": "ctx-tenant"},
            tenant_id=None,
        )
        assert task.get_tenant_id() == "ctx-tenant"

    @pytest.mark.unit
    def test_get_tenant_id_returns_none_if_missing(self):
        """get_tenant_id() returns None when no tenant is specified anywhere."""
        task = ScheduledTask(
            priority=TaskPriority.NORMAL.value,
            scheduled_time=datetime.now(UTC),
            task_id="t2",
            workflow_instance_id="wf",
            capability="cap",
            agent_type="Agent",
            tenant_id=None,
        )
        assert task.get_tenant_id() is None

    @pytest.mark.unit
    def test_get_full_tenant_context_merges_all_sources(self):
        """get_full_tenant_context() merges context, tenant_context, and tenant_id."""
        task = ScheduledTask(
            priority=TaskPriority.NORMAL.value,
            scheduled_time=datetime.now(UTC),
            task_id="t3",
            workflow_instance_id="wf",
            capability="cap",
            agent_type="Agent",
            context={"user_id": "u-1"},
            tenant_context={"tier": "enterprise"},
            tenant_id="t-merged",
        )
        ctx = task.get_full_tenant_context()
        assert ctx["user_id"] == "u-1"
        assert ctx["tier"] == "enterprise"
        assert ctx["tenant_id"] == "t-merged"

    @pytest.mark.unit
    def test_priority_ordering(self):
        """Tasks compare correctly by (priority, scheduled_time) for heap ordering."""
        now = datetime.now(UTC)
        critical = _make_task("c", priority=TaskPriority.CRITICAL.value, scheduled_at=now)
        background = _make_task("b", priority=TaskPriority.BACKGROUND.value, scheduled_at=now)
        assert critical < background  # lower priority value = higher priority

    @pytest.mark.unit
    def test_scheduled_time_string_is_parsed(self):
        """ScheduledTask accepts ISO string for scheduled_time and converts it."""
        iso_str = "2025-01-01T12:00:00+00:00"
        task = ScheduledTask(
            priority=TaskPriority.NORMAL.value,
            scheduled_time=iso_str,  # type: ignore[arg-type]
            task_id="t-iso",
            workflow_instance_id="wf",
            capability="cap",
            agent_type="Agent",
        )
        assert isinstance(task.scheduled_time, datetime)


# ============================================================================
# TaskScheduler
# ============================================================================

class TestTaskSchedulerStats:
    """Tests for TaskScheduler statistics and configuration."""

    @pytest.mark.unit
    def test_initial_stats_are_zero(self):
        """Fresh scheduler reports all-zero statistics."""
        scheduler = TaskScheduler(max_concurrent_tasks=10)
        stats = scheduler.get_stats()
        assert stats["pending_tasks"] == 0
        assert stats["running_tasks"] == 0
        assert stats["completed_tasks"] == 0
        assert stats["failed_tasks"] == 0
        assert stats["max_concurrent"] == 10

    @pytest.mark.unit
    def test_utilization_is_zero_initially(self):
        """Utilization starts at 0%."""
        scheduler = TaskScheduler(max_concurrent_tasks=50)
        assert scheduler.get_stats()["utilization"] == 0.0

    @pytest.mark.unit
    def test_custom_max_concurrent_tasks(self):
        """Scheduler honours the max_concurrent_tasks parameter."""
        scheduler = TaskScheduler(max_concurrent_tasks=200)
        assert scheduler.max_concurrent_tasks == 200


class TestTaskSchedulerScheduleAndCancel:
    """Tests for task scheduling and cancellation."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_schedule_task_returns_task_id(self):
        """schedule_task() returns the task's ID."""
        scheduler = TaskScheduler()
        task = _make_task("sched-1")
        result = await scheduler.schedule_task(task)
        assert result == "sched-1"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_scheduled_task_appears_in_pending(self):
        """A freshly scheduled task appears in list_pending_tasks()."""
        scheduler = TaskScheduler()
        task = _make_task("pending-1")
        await scheduler.schedule_task(task)

        pending = await scheduler.list_pending_tasks()
        task_ids = [t["task_id"] for t in pending]
        assert "pending-1" in task_ids

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cancel_queued_task_removes_it(self):
        """cancel_task() removes a pending task from the queue."""
        scheduler = TaskScheduler()
        task = _make_task("cancel-1")
        await scheduler.schedule_task(task)

        cancelled = await scheduler.cancel_task("cancel-1")
        assert cancelled is True

        pending = await scheduler.list_pending_tasks()
        assert all(t["task_id"] != "cancel-1" for t in pending)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cancel_unknown_task_returns_false(self):
        """cancel_task() returns False for an unknown task ID."""
        scheduler = TaskScheduler()
        result = await scheduler.cancel_task("nonexistent")
        assert result is False

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cancel_tasks_by_tenant(self):
        """cancel_tasks_by_tenant() cancels all pending tasks for a tenant."""
        scheduler = TaskScheduler()
        tasks = [_make_task(f"t{i}", tenant_id="victim-tenant") for i in range(3)]
        other_task = _make_task("other", tenant_id="safe-tenant")

        for t in tasks:
            await scheduler.schedule_task(t)
        await scheduler.schedule_task(other_task)

        count = await scheduler.cancel_tasks_by_tenant("victim-tenant")
        assert count == 3

        pending = await scheduler.list_pending_tasks()
        remaining_ids = {t["task_id"] for t in pending}
        assert not remaining_ids.intersection({"t0", "t1", "t2"})
        assert "other" in remaining_ids

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_pending_tasks_filters_by_workflow(self):
        """list_pending_tasks(workflow_id=...) filters by workflow instance."""
        scheduler = TaskScheduler()
        t1 = ScheduledTask(
            priority=TaskPriority.NORMAL.value,
            scheduled_time=datetime.now(UTC),
            task_id="wf1-task",
            workflow_instance_id="wf-1",
            capability="cap",
            agent_type="Agent",
        )
        t2 = ScheduledTask(
            priority=TaskPriority.NORMAL.value,
            scheduled_time=datetime.now(UTC),
            task_id="wf2-task",
            workflow_instance_id="wf-2",
            capability="cap",
            agent_type="Agent",
        )
        await scheduler.schedule_task(t1)
        await scheduler.schedule_task(t2)

        results = await scheduler.list_pending_tasks(workflow_id="wf-1")
        assert all(t["task_id"] == "wf1-task" for t in results)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_pending_tasks_by_tenant(self):
        """list_pending_tasks_by_tenant() returns only tasks for that tenant."""
        scheduler = TaskScheduler()
        t_a = _make_task("a1", tenant_id="tenant-A")
        t_b = _make_task("b1", tenant_id="tenant-B")
        await scheduler.schedule_task(t_a)
        await scheduler.schedule_task(t_b)

        results = await scheduler.list_pending_tasks_by_tenant("tenant-A")
        assert all(t["tenant_id"] == "tenant-A" for t in results)
        assert len(results) == 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_schedule_raises_when_shutdown(self):
        """schedule_task() raises RuntimeError after stop() is called."""
        scheduler = TaskScheduler()
        scheduler._shutdown = True
        with pytest.raises(RuntimeError, match="shutting down"):
            await scheduler.schedule_task(_make_task())


class TestTaskSchedulerPriorityOrdering:
    """Tests for priority queue ordering."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_critical_task_ordered_before_background(self):
        """CRITICAL priority tasks are positioned before BACKGROUND tasks."""
        scheduler = TaskScheduler()
        now = datetime.now(UTC)

        bg_task = ScheduledTask(
            priority=TaskPriority.BACKGROUND.value,
            scheduled_time=now,
            task_id="bg",
            workflow_instance_id="wf",
            capability="cap",
            agent_type="Agent",
        )
        crit_task = ScheduledTask(
            priority=TaskPriority.CRITICAL.value,
            scheduled_time=now,
            task_id="crit",
            workflow_instance_id="wf",
            capability="cap",
            agent_type="Agent",
        )

        # Add background first, then critical
        await scheduler.schedule_task(bg_task)
        await scheduler.schedule_task(crit_task)

        # The first element in the heap should be the critical task
        top_priority, _, top_task = scheduler._task_queue[0]
        assert top_priority == TaskPriority.CRITICAL.value
        assert top_task.task_id == "crit"


class TestTaskSchedulerGetTaskStatus:
    """Tests for get_task_status()."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_task_status_for_queued_task(self):
        """get_task_status() returns a dict for a queued task."""
        scheduler = TaskScheduler()
        await scheduler.schedule_task(_make_task("status-test"))

        status = await scheduler.get_task_status("status-test")
        assert status is not None
        assert status["task_id"] == "status-test"
        assert status["status"] == TaskStatus.PENDING.value

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_task_status_unknown_returns_none(self):
        """get_task_status() returns None for an unrecognised task ID."""
        scheduler = TaskScheduler()
        result = await scheduler.get_task_status("does-not-exist")
        assert result is None


class TestTaskSchedulerStartStop:
    """Tests for scheduler lifecycle."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_start_and_stop_do_not_raise(self):
        """start() and stop() complete without errors."""
        scheduler = TaskScheduler()
        await scheduler.start()
        await scheduler.stop()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_double_start_is_safe(self):
        """Calling start() twice does not create duplicate scheduler tasks."""
        scheduler = TaskScheduler()
        await scheduler.start()
        first_task = scheduler._scheduler_task
        await scheduler.start()
        # Should not create a new task
        assert scheduler._scheduler_task is first_task
        await scheduler.stop()


class TestTaskSchedulerCallbacks:
    """Tests for task lifecycle callbacks."""

    @pytest.mark.unit
    def test_set_callbacks_registers_callables(self):
        """set_callbacks() stores the provided callables."""
        scheduler = TaskScheduler()

        def on_complete(t):
            pass

        def on_fail(t, e):
            pass

        scheduler.set_callbacks(on_complete=on_complete, on_fail=on_fail)
        assert scheduler._on_task_complete is on_complete
        assert scheduler._on_task_fail is on_fail

    @pytest.mark.unit
    def test_set_callbacks_with_none_clears_them(self):
        """set_callbacks() with None arguments clears the registered callables."""
        scheduler = TaskScheduler()

        def on_complete(t):
            pass

        scheduler.set_callbacks(on_complete=on_complete)
        scheduler.set_callbacks(on_complete=None, on_fail=None)
        assert scheduler._on_task_complete is None
        assert scheduler._on_task_fail is None


# ============================================================================
# OSS-0 Characterization
# ============================================================================

class TestOSS0SchedulerCharacterization:
    """Behavior that future TaskExecutionPort adapters must preserve."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_retry_preserves_tenant_context_and_parameters(self):
        """Retry scheduling keeps tenant metadata and handler parameters intact."""

        scheduler = TaskScheduler()
        task = ScheduledTask(
            priority=TaskPriority.HIGH.value,
            scheduled_time=datetime.now(UTC),
            task_id="retry-source",
            workflow_instance_id="wf-retry",
            capability="capability",
            agent_type="Agent",
            context={"request_id": "req-1", "tenant_id": "tenant-context"},
            parameters={"payload": "same"},
            retry_count=0,
            max_retries=2,
            tenant_id="tenant-explicit",
            tenant_context={"role": "analyst"},
        )

        await scheduler._handle_retry(task)
        pending = await scheduler.list_pending_tasks()

        assert len(pending) == 1
        retry = pending[0]
        assert retry["task_id"] == "retry-source_retry_1"
        assert retry["workflow_instance_id"] == "wf-retry"
        assert retry["tenant_id"] == "tenant-explicit"
        assert retry["retry_count"] == 1
        assert retry["max_retries"] == 2

        queued_task = scheduler._task_queue[0][2]
        assert queued_task.context == {"request_id": "req-1", "tenant_id": "tenant-context"}
        assert queued_task.parameters == {"payload": "same"}
        assert queued_task.tenant_context == {"role": "analyst"}

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_handler_result_wrapper_shape_is_stable(self):
        """Handlers return the canonical task/capability/status/result wrapper."""

        scheduler = TaskScheduler()
        task = _make_task(task_id="handler-result", capability="analysis")

        async def handler(received_task: ScheduledTask) -> dict[str, str]:
            assert received_task is task
            return {"value": "ok"}

        scheduler.register_handler("analysis", handler)

        result = await scheduler._run_task_handler(task)
        assert result.model_dump() == {
            "task_id": "handler-result",
            "capability": "analysis",
            "status": "completed",
            "result": {"value": "ok"},
        }

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_task_to_dict_preserves_operational_schema(self):
        """Task status dictionaries expose stable keys for routes and diagnostics."""

        scheduler = TaskScheduler(max_concurrent_tasks=3)
        task = _make_task(task_id="schema-task", capability="schema_cap")
        task.result = {"done": True}
        task.error = None

        serialized = scheduler._task_to_dict(task)

        assert set(serialized) == {
            "task_id",
            "workflow_instance_id",
            "capability",
            "agent_type",
            "priority",
            "status",
            "scheduled_time",
            "started_at",
            "completed_at",
            "retry_count",
            "max_retries",
            "result",
            "error",
            "tenant_id",
        }
        assert serialized["tenant_id"] == "tenant-abc"
        assert serialized["result"] == {"done": True}
