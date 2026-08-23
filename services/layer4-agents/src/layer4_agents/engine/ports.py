from __future__ import annotations

"""Task execution ports for OSS-0 substitution scaffolding.

The port captures the Fabric task-execution contract for future distributed
execution pilots without binding application code to the legacy scheduler.
"""

from collections.abc import Callable
from typing import Any, Protocol, runtime_checkable

from .types import ScheduledTask


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


@runtime_checkable
class TaskSchedulerPort(Protocol):
    """Core scheduler dependency required by the workflow executor."""

    async def start(self) -> None:
        """Start scheduler background processing."""

    async def stop(self) -> None:
        """Stop scheduler background processing."""

    async def schedule_task(self, task: ScheduledTask) -> str:
        """Schedule a task for execution."""

    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a scheduled or running task."""

    async def get_task_status(self, task_id: str) -> dict[str, Any] | None:
        """Return task status, or ``None`` when unknown."""

    async def list_pending_tasks(
        self,
        workflow_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """List queued tasks."""

    async def list_running_tasks(self) -> list[dict[str, Any]]:
        """List running tasks."""

    async def list_pending_tasks_by_tenant(
        self, tenant_id: str
    ) -> list[dict[str, Any]]:
        """List queued tasks for a tenant."""

    async def cancel_tasks_by_tenant(self, tenant_id: str) -> int:
        """Cancel queued tasks for a tenant."""

    def set_callbacks(
        self,
        on_complete: Callable[[ScheduledTask], Any] | None = None,
        on_fail: Callable[[ScheduledTask, Exception], Any] | None = None,
    ) -> None:
        """Set scheduler lifecycle callbacks."""

    def register_handler(
        self, capability: str, handler: Callable[[ScheduledTask], Any]
    ) -> None:
        """Register a handler for a task capability."""

    def get_stats(self) -> dict[str, Any]:
        """Return scheduler statistics."""


@runtime_checkable
class CheckpointPolicyPort(Protocol):
    """Contract for checkpoint conflict detection and replay policy validation."""

    def compute_state_hash(self, state: Any) -> str:
        """Compute deterministic state hash."""

    async def resolve_resume_policy(
        self,
        *,
        workflow_id: str,
        state: Any,
        target_checkpoint_id: str | None = None,
    ) -> None:
        """Validate resume request against replay policy."""

    async def get_latest_persisted_checkpoint_hash(
        self,
        *,
        tenant_id: str,
        workflow_id: str,
        run_id: str,
        checkpoint_id: str,
    ) -> str:
        """Retrieve persisted checkpoint hash."""


@runtime_checkable
class WorkflowLifecyclePersistencePort(Protocol):
    """Contract for persisting workflow state transitions and interruptions."""

    async def mark_workflow_running(self, workflow_id: str, initial_state: Any) -> None:
        """Mark workflow as RUNNING."""

    async def persist_workflow_failure(
        self, workflow_id: str, initial_state: Any, exc: Exception
    ) -> None:
        """Persist workflow failure state."""

    async def persist_interruption_if_needed(self, workflow_id: str) -> None:
        """Persist workflow interruption on cancellation if needed."""

    async def archive_workflow(
        self, workflow_id: str, tenant_id: str | None = None
    ) -> dict[str, Any] | None:
        """Archive workflow state scoped by tenant."""


@runtime_checkable
class WorkflowRecoveryPort(Protocol):
    """Contract for recovering orphaned workflow executions on startup."""

    async def recover_workflows(
        self, active_workflow_ids: set[str]
    ) -> list[dict[str, Any]]:
        """Recover orphaned active workflows."""
