"""Dependency-free Layer 4 transport task datatypes."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class TaskPriority(Enum):
    """Task priority levels per Layer 4 transport contract."""

    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4
    BACKGROUND = 5


class TaskStatus(Enum):
    """Task execution status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


@dataclass(order=True)
class ScheduledTask:
    """Dependency-free task scheduled for Layer 4 transport execution."""

    priority: int
    scheduled_time: datetime
    task_id: str = field(compare=False)
    workflow_instance_id: str = field(compare=False)
    capability: str = field(compare=False)
    agent_type: str = field(compare=False)
    context: dict[str, Any] = field(compare=False, default_factory=dict)
    parameters: dict[str, Any] = field(compare=False, default_factory=dict)
    retry_count: int = field(compare=False, default=0)
    max_retries: int = field(compare=False, default=3)
    timeout_seconds: int = field(compare=False, default=300)
    status: TaskStatus = field(compare=False, default=TaskStatus.PENDING)
    started_at: datetime | None = field(compare=False, default=None)
    completed_at: datetime | None = field(compare=False, default=None)
    result: dict[str, Any] | None = field(compare=False, default=None)
    error: str | None = field(compare=False, default=None)
    tenant_id: str | None = field(compare=False, default=None)
    tenant_context: dict[str, Any] | None = field(compare=False, default=None)

    def __post_init__(self) -> None:
        """Normalize scheduled times supplied by compatibility callers."""
        if isinstance(self.scheduled_time, str):
            self.scheduled_time = datetime.fromisoformat(self.scheduled_time)

    def get_tenant_id(self) -> str | None:
        """Return the effective tenant identifier for this task."""
        return self.tenant_id or self.context.get("tenant_id")

    def get_full_tenant_context(self) -> dict[str, Any]:
        """Return context fields merged with explicit tenant metadata."""
        result = dict(self.context)
        if self.tenant_context:
            result.update(self.tenant_context)
        if self.tenant_id:
            result["tenant_id"] = self.tenant_id
        return result
