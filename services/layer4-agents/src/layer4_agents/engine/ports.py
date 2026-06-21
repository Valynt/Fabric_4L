from __future__ import annotations

"""Task execution ports for OSS-0 substitution scaffolding.

The port captures the Fabric task-execution contract for future distributed
execution pilots without binding application code to the legacy scheduler.
"""


from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class TaskExecutionRequest(Protocol):
    """Application-owned task shape required by task-execution ports."""

    task_id: str
    workflow_instance_id: str
    capability: str
    agent_type: str
    tenant_id: str | None
    context: dict[str, Any]
    parameters: dict[str, Any]


@runtime_checkable
class TaskExecutionPort(Protocol):
    """Application-owned task-execution contract."""

    async def submit(self, task: TaskExecutionRequest) -> str:
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
