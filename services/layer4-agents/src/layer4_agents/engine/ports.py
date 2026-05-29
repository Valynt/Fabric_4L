from __future__ import annotations

"""Task execution ports for OSS-0 substitution scaffolding.

The port captures the Fabric task-execution contract while the legacy adapter delegates
to the existing TaskScheduler. This creates a stable seam for future distributed
execution pilots without changing scheduler defaults or orchestration semantics.
"""


from typing import Any, Protocol, runtime_checkable

from .scheduler import ScheduledTask, TaskScheduler


@runtime_checkable
class TaskExecutionPort(Protocol):
    """Application-owned task-execution contract."""

    async def submit(self, task: ScheduledTask) -> str:
        """Submit a task for execution and return its task ID."""

    async def cancel(self, task_id: str) -> bool:
        """Cancel a pending or running task."""

    async def get_status(self, task_id: str) -> dict[str, Any] | None:
        """Return the task status dictionary, or ``None`` if unknown."""

    async def list_pending(
        self,
        tenant_id: str | None = None,
        capability: str | None = None,
    ) -> list[dict[str, Any]]:
        """List pending tasks using the current scheduler status shape."""

    async def list_running(self) -> list[dict[str, Any]]:
        """List currently running tasks using the current scheduler status shape."""

    def get_stats(self) -> dict[str, Any]:
        """Return scheduler statistics in the current operational shape."""


class LegacyTaskExecutionAdapter:
    """TaskExecutionPort adapter around the current TaskScheduler."""

    def __init__(self, scheduler: TaskScheduler) -> None:
        self._scheduler = scheduler

    async def submit(self, task: ScheduledTask) -> str:
        return await self._scheduler.schedule_task(task)

    async def cancel(self, task_id: str) -> bool:
        return await self._scheduler.cancel_task(task_id)

    async def get_status(self, task_id: str) -> dict[str, Any] | None:
        return await self._scheduler.get_task_status(task_id)

    async def list_pending(
        self,
        tenant_id: str | None = None,
        capability: str | None = None,
    ) -> list[dict[str, Any]]:
        if tenant_id is not None:
            pending = await self._scheduler.list_pending_tasks_by_tenant(tenant_id)
        else:
            pending = await self._scheduler.list_pending_tasks()

        if capability is not None:
            pending = [task for task in pending if task.get("capability") == capability]

        return pending

    async def list_running(self) -> list[dict[str, Any]]:
        return await self._scheduler.list_running_tasks()

    def get_stats(self) -> dict[str, Any]:
        return self._scheduler.get_stats()


def as_task_execution_port(scheduler: TaskScheduler) -> TaskExecutionPort:
    """Return the legacy scheduler through the stable task-execution port."""

    return LegacyTaskExecutionAdapter(scheduler)
