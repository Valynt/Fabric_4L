from __future__ import annotations

"""Task scheduler with priority and backpressure handling.

Implements the task scheduling requirements from the specification:
- Priority-based scheduling (CRITICAL, HIGH, NORMAL, LOW, BACKGROUND)
- Exponential backoff for retries
- Backpressure with max_concurrent_tasks limit
"""


import asyncio
import heapq
import logging
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from value_fabric.shared.models.typed_dict import TypedDictModel

from .types import ScheduledTask, TaskStatus


class TaskScheduler__run_task_handlerResult(TypedDictModel):
    capability: Any
    result: dict[str, Any]
    status: str
    task_id: Any


class TaskScheduler__task_to_dictResult(TypedDictModel):
    agent_type: Any
    capability: Any
    completed_at: Any
    error: Any
    max_retries: Any
    priority: Any
    result: Any
    retry_count: Any
    scheduled_time: Any
    started_at: Any
    status: Any
    task_id: Any
    tenant_id: Any
    workflow_instance_id: Any


class TaskScheduler_get_statsResult(TypedDictModel):
    completed_tasks: Any
    failed_tasks: Any
    max_concurrent: Any
    pending_tasks: Any
    running_tasks: Any
    utilization: Any


logger = logging.getLogger(__name__)


class TaskScheduler:
    """Priority-based task scheduler with backpressure.

    Implements:
    - Priority queue with heapq
    - Max concurrent task limiting
    - Retry with exponential backoff
    - Task lifecycle management

    Example:
        scheduler = TaskScheduler(max_concurrent_tasks=100)

        task = ScheduledTask(
            priority=2,  # TaskPriority.HIGH.value
            scheduled_time=datetime.now(timezone.utc),
            task_id="task-1",
            workflow_instance_id="wf-1",
            capability="document_parsing",
            agent_type="ContextExtractionAgent",
            context={"tenant_id": "tenant-1"},
        )

        await scheduler.schedule_task(task)
    """

    def __init__(self, max_concurrent_tasks: int = 100):
        """Initialize task scheduler.

        Args:
            max_concurrent_tasks: Maximum tasks running simultaneously
        """
        self.max_concurrent_tasks = max_concurrent_tasks

        # Priority queue: (priority, scheduled_time, task)
        self._task_queue: list[tuple] = []

        # Running tasks
        self._running_tasks: dict[str, asyncio.Task] = {}

        # Task history
        self._task_history: list[dict[str, Any]] = []
        self._max_history = 1000

        # Synchronization
        self._lock = asyncio.Lock()
        self._semaphore = asyncio.Semaphore(max_concurrent_tasks)
        self._shutdown = False
        self._scheduler_task: asyncio.Task | None = None

        # Callbacks
        self._on_task_complete: Callable[[ScheduledTask], Any] | None = None
        self._on_task_fail: Callable[[ScheduledTask, Exception], Any] | None = None
        self._handlers: dict[str, Callable[[ScheduledTask], Any]] = {}

    async def start(self) -> None:
        """Start the scheduler background task."""
        if self._scheduler_task is None:
            self._scheduler_task = asyncio.create_task(self._scheduler_loop())
            logger.info("Task scheduler started")

    async def stop(self) -> None:
        """Stop the scheduler and cancel pending tasks."""
        self._shutdown = True

        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass

        # Cancel running tasks
        async with self._lock:
            for task_id, task in list(self._running_tasks.items()):
                task.cancel()

        logger.info("Task scheduler stopped")

    async def schedule_task(self, task: ScheduledTask) -> str:
        """Schedule a task for execution.

        Args:
            task: Task to schedule

        Returns:
            task_id: ID of scheduled task
        """
        async with self._lock:
            if self._shutdown:
                raise RuntimeError("Scheduler is shutting down")

            heapq.heappush(self._task_queue, (task.priority, task.scheduled_time, task))

        logger.debug(
            f"Scheduled task {task.task_id} ({task.capability}) with priority {task.priority}"
        )
        return task.task_id

    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a scheduled or running task.

        Args:
            task_id: Task to cancel

        Returns:
            True if task was cancelled
        """
        async with self._lock:
            # Check if running
            if task_id in self._running_tasks:
                self._running_tasks[task_id].cancel()
                return True

            # Check if queued
            for i, (priority, scheduled_time, task) in enumerate(self._task_queue):
                if task.task_id == task_id:
                    task.status = TaskStatus.CANCELLED
                    self._task_queue.pop(i)
                    heapq.heapify(self._task_queue)
                    return True

        return False

    async def get_task_status(self, task_id: str) -> dict[str, Any] | None:
        """Get status of a task.

        Args:
            task_id: Task to query

        Returns:
            Task status dict or None if not found
        """
        async with self._lock:
            # Check running tasks
            if task_id in self._running_tasks:
                for _, _, task in self._task_queue:
                    if task.task_id == task_id:
                        return self._task_to_dict(task)

            # Check queue
            for _, _, task in self._task_queue:
                if task.task_id == task_id:
                    return self._task_to_dict(task)

            # Check history
            for history_task in reversed(self._task_history):
                if history_task["task_id"] == task_id:
                    return history_task

        return None

    async def list_pending_tasks(
        self,
        workflow_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """List pending tasks.

        Args:
            workflow_id: Filter by workflow instance

        Returns:
            List of pending task dicts
        """
        async with self._lock:
            pending = []
            for _, _, task in sorted(self._task_queue):
                if workflow_id and task.workflow_instance_id != workflow_id:
                    continue
                pending.append(self._task_to_dict(task))
            return pending

    async def list_running_tasks(self) -> list[dict[str, Any]]:
        """List currently running tasks.

        Returns:
            List of running task dicts
        """
        async with self._lock:
            running = []
            for _, _, task in self._task_queue:
                if task.status == TaskStatus.RUNNING:
                    running.append(self._task_to_dict(task))
            return running

    async def list_pending_tasks_by_tenant(
        self,
        tenant_id: str,
    ) -> list[dict[str, Any]]:
        """List pending tasks filtered by tenant (Task 2.1).

        Args:
            tenant_id: Tenant ID to filter by

        Returns:
            List of pending task dicts for the tenant
        """
        async with self._lock:
            pending = []
            for _, _, task in sorted(self._task_queue):
                if task.get_tenant_id() == tenant_id:
                    pending.append(self._task_to_dict(task))
            return pending

    async def cancel_tasks_by_tenant(self, tenant_id: str) -> int:
        """Cancel all pending tasks for a tenant (Task 2.1).

        Args:
            tenant_id: Tenant ID to cancel tasks for

        Returns:
            Number of tasks cancelled
        """
        cancelled = 0
        async with self._lock:
            tasks_to_cancel = []
            for i, (priority, scheduled_time, task) in enumerate(self._task_queue):
                if (
                    task.get_tenant_id() == tenant_id
                    and task.status == TaskStatus.PENDING
                ):
                    task.status = TaskStatus.CANCELLED
                    tasks_to_cancel.append(i)

            # Remove from queue (in reverse order to maintain indices)
            for i in reversed(tasks_to_cancel):
                self._task_queue.pop(i)
                cancelled += 1

            if tasks_to_cancel:
                heapq.heapify(self._task_queue)

        logger.info(f"Cancelled {cancelled} tasks for tenant {tenant_id}")
        return cancelled

    def set_callbacks(
        self,
        on_complete: Callable[[ScheduledTask], Any] | None = None,
        on_fail: Callable[[ScheduledTask, Exception], Any] | None = None,
    ) -> None:
        """Set callbacks for task lifecycle events.

        Args:
            on_complete: Called when task completes successfully
            on_fail: Called when task fails
        """
        self._on_task_complete = on_complete
        self._on_task_fail = on_fail

    def register_handler(
        self, capability: str, handler: Callable[[ScheduledTask], Any]
    ) -> None:
        """Register an execution handler for a task capability."""
        self._handlers[capability] = handler

    async def _scheduler_loop(self) -> None:
        """Main scheduler loop."""
        while not self._shutdown:
            try:
                await self._process_queue()
                await asyncio.sleep(0.1)  # Small delay to prevent CPU spinning
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error(f"Scheduler loop error: {e}")
                await asyncio.sleep(1)

    async def _process_queue(self) -> None:
        """Process the task queue."""
        async with self._lock:
            if not self._task_queue:
                return

            now = datetime.now(UTC)
            ready_tasks = []

            # Find tasks ready to execute
            while self._task_queue:
                priority, scheduled_time, task = self._task_queue[0]

                if scheduled_time <= now and task.status == TaskStatus.PENDING:
                    heapq.heappop(self._task_queue)
                    ready_tasks.append(task)
                else:
                    break

        # Execute ready tasks (outside lock)
        for task in ready_tasks:
            if not self._shutdown:
                asyncio.create_task(self._execute_task(task))

    async def _execute_task(self, task: ScheduledTask) -> None:
        """Execute a single task.

        Args:
            task: Task to execute
        """
        async with self._semaphore:
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now(UTC)

            task_id = task.task_id

            async with self._lock:
                self._running_tasks[task_id] = asyncio.current_task()

            try:
                # Execute with timeout
                result = await asyncio.wait_for(
                    self._run_task_handler(task),
                    timeout=task.timeout_seconds,
                )

                task.result = result
                task.status = TaskStatus.COMPLETED
                task.completed_at = datetime.now(UTC)

                logger.info(f"Task {task_id} completed successfully")

                if self._on_task_complete:
                    await self._call_callback(self._on_task_complete, task)

            except TimeoutError:
                task.status = TaskStatus.FAILED
                task.error = f"Task timed out after {task.timeout_seconds}s"
                task.completed_at = datetime.now(UTC)

                logger.error(f"Task {task_id} timed out")

                if self._on_task_fail:
                    await self._call_callback(self._on_task_fail, task, TimeoutError())

                # Schedule retry if needed
                await self._handle_retry(task)

            except asyncio.CancelledError:
                raise
            except Exception as e:
                task.status = TaskStatus.FAILED
                task.error = f"{type(e).__name__}: task_failed"
                task.completed_at = datetime.now(UTC)

                logger.exception("Task %s failed", task_id)

                if self._on_task_fail:
                    await self._call_callback(self._on_task_fail, task, e)

                # Schedule retry if needed
                await self._handle_retry(task)

            finally:
                async with self._lock:
                    if task_id in self._running_tasks:
                        del self._running_tasks[task_id]

                    # Add to history
                    self._task_history.append(self._task_to_dict(task))
                    if len(self._task_history) > self._max_history:
                        self._task_history.pop(0)

    async def _run_task_handler(self, task: ScheduledTask) -> dict[str, Any]:
        """Run the actual task handler.

        Args:
            task: Task to run

        Returns:
            Task result
        """
        handler = task.parameters.get("handler")
        if handler is None:
            handler = self._handlers.get(task.capability)

        if handler is None and task.capability == "workflow_execution":
            workflow = task.parameters.get("workflow")
            initial_state = task.parameters.get("initial_state")
            workflow_id = (
                task.parameters.get("workflow_id") or task.workflow_instance_id
            )
            if workflow is None or initial_state is None:
                raise RuntimeError(
                    f"Task {task.task_id} cannot execute workflow_execution without workflow and initial_state"
                )

            result = await workflow.run(initial_state, thread_id=workflow_id)
            return TaskScheduler__run_task_handlerResult.model_validate(
                {
                    "task_id": task.task_id,
                    "capability": task.capability,
                    "status": "completed",
                    "result": (
                        result.model_dump() if hasattr(result, "model_dump") else result
                    ),
                }
            )

        if handler is None:
            raise RuntimeError(
                f"No task handler registered for capability: {task.capability}"
            )

        result = handler(task)
        if asyncio.iscoroutine(result):
            result = await result

        return TaskScheduler__run_task_handlerResult.model_validate(
            {
                "task_id": task.task_id,
                "capability": task.capability,
                "status": "completed",
                "result": (
                    result.model_dump() if hasattr(result, "model_dump") else result
                ),
            }
        )

    async def _handle_retry(self, task: ScheduledTask) -> None:
        """Handle task retry with exponential backoff.

        Args:
            task: Failed task to potentially retry
        """
        if task.retry_count >= task.max_retries:
            logger.warning(
                f"Task {task.task_id} exceeded max retries ({task.max_retries})"
            )
            return

        # Calculate exponential backoff
        base_delay = 2
        max_delay = 300
        delay = min(base_delay**task.retry_count, max_delay)

        task.retry_count += 1
        task.status = TaskStatus.RETRYING

        next_scheduled = datetime.now(UTC) + timedelta(seconds=delay)

        logger.info(
            f"Scheduling retry {task.retry_count}/{task.max_retries} for task {task.task_id} in {delay}s"
        )

        # Task 2.1: Preserve tenant context in retry
        await self.schedule_task(
            ScheduledTask(
                priority=task.priority,
                scheduled_time=next_scheduled,
                task_id=f"{task.task_id}_retry_{task.retry_count}",
                workflow_instance_id=task.workflow_instance_id,
                capability=task.capability,
                agent_type=task.agent_type,
                context=task.context,
                parameters=task.parameters,
                retry_count=task.retry_count,
                max_retries=task.max_retries,
                timeout_seconds=task.timeout_seconds,
                tenant_id=task.tenant_id,
                tenant_context=task.tenant_context,
            )
        )

    async def _call_callback(
        self,
        callback: Callable,
        task: ScheduledTask,
        exception: Exception | None = None,
    ) -> None:
        """Safely call a callback function.

        Args:
            callback: Callback to call
            task: Task context
            exception: Optional exception for fail callback
        """
        try:
            if exception:
                result = callback(task, exception)
            else:
                result = callback(task)

            if asyncio.iscoroutine(result):
                await result
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"Callback error: {e}")

    def _task_to_dict(self, task: ScheduledTask) -> dict[str, Any]:
        """Convert task to dictionary representation.

        Args:
            task: Task to convert

        Returns:
            Dict representation
        """
        return TaskScheduler__task_to_dictResult.model_validate(
            {
                "task_id": task.task_id,
                "workflow_instance_id": task.workflow_instance_id,
                "capability": task.capability,
                "agent_type": task.agent_type,
                "priority": task.priority,
                "status": task.status.value,
                "scheduled_time": task.scheduled_time.isoformat(),
                "started_at": task.started_at.isoformat() if task.started_at else None,
                "completed_at": (
                    task.completed_at.isoformat() if task.completed_at else None
                ),
                "retry_count": task.retry_count,
                "max_retries": task.max_retries,
                "result": task.result,
                "error": task.error,
                "tenant_id": task.get_tenant_id(),  # Task 2.1
            }
        )

    def get_stats(self) -> dict[str, Any]:
        """Get scheduler statistics.

        Returns:
            Statistics dict
        """
        pending_count = len(self._task_queue)
        running_count = len(self._running_tasks)

        # Calculate history stats
        completed_count = sum(
            1 for t in self._task_history if t["status"] == TaskStatus.COMPLETED.value
        )
        failed_count = sum(
            1 for t in self._task_history if t["status"] == TaskStatus.FAILED.value
        )

        return TaskScheduler_get_statsResult.model_validate(
            {
                "pending_tasks": pending_count,
                "running_tasks": running_count,
                "completed_tasks": completed_count,
                "failed_tasks": failed_count,
                "max_concurrent": self.max_concurrent_tasks,
                "utilization": round(
                    running_count / self.max_concurrent_tasks * 100, 2
                ),
            }
        )
