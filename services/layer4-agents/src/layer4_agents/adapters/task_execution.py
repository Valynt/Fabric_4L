from __future__ import annotations

"""Task execution adapter for the legacy Layer 4 scheduler."""

from typing import Any, cast

from layer4_agents.engine.ports import TaskExecutionPort, TaskExecutionRequest
from layer4_agents.engine.scheduler import ScheduledTask, TaskScheduler


class LegacyTaskExecutionAdapter:
    """TaskExecutionPort adapter around the current TaskScheduler."""

    def __init__(self, scheduler: TaskScheduler) -> None:
        self._scheduler = scheduler

    async def submit(self, task: TaskExecutionRequest) -> str:
        return cast(str, await self._scheduler.schedule_task(cast(ScheduledTask, task)))

    async def cancel(self, task_id: str) -> bool:
        return cast(bool, await self._scheduler.cancel_task(task_id))

    async def get_status(self, task_id: str) -> dict[str, Any] | None:
        return cast(dict[str, Any] | None, await self._scheduler.get_task_status(task_id))

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
        return cast(list[dict[str, Any]], await self._scheduler.list_running_tasks())

    def get_stats(self) -> dict[str, Any]:
        return cast(dict[str, Any], self._scheduler.get_stats())


def as_task_execution_port(scheduler: TaskScheduler) -> TaskExecutionPort:
    """Return the legacy scheduler through the stable task-execution port."""

    return LegacyTaskExecutionAdapter(scheduler)
