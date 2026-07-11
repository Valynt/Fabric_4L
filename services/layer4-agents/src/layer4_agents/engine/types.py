from __future__ import annotations

"""Shared execution engine types.

Types in this module are imported by both port definitions and concrete
scheduler implementations so that port modules can stay abstract and avoid
depending on adapter/scheduler internals.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class TaskPriority(Enum):
    """Task priority levels per spec."""

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
    """Task scheduled for execution.

    From spec:
    - priority: Task priority (1=CRITICAL, 5=BACKGROUND)
    - scheduled_time: When task should execute
    - task_id: Unique identifier
    - workflow_instance_id: Parent workflow
    - state_name: Workflow state being executed
    - agent_type: Type of agent to handle task
    - context: Execution context (tenant_id, etc.)
    - retry_count: Current retry count
    - max_retries: Maximum retry attempts
    - timeout_seconds: Task timeout

    Multi-tenancy (Task 2.1):
    - tenant_id: Primary tenant identifier for RLS enforcement
    - tenant_context: Full RequestContext dict for async propagation
    """

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

    # Multi-tenancy context (Task 2.1)
    tenant_id: str | None = field(compare=False, default=None)
    tenant_context: dict[str, Any] | None = field(compare=False, default=None)

    def __post_init__(self):
        """Ensure scheduled_time is datetime object."""
        if isinstance(self.scheduled_time, str):
            self.scheduled_time = datetime.fromisoformat(self.scheduled_time)

    def get_tenant_id(self) -> str | None:
        """Get tenant ID from task context (Task 2.1).

        Returns:
            Tenant ID if set, None otherwise
        """
        return self.tenant_id or self.context.get("tenant_id")

    def get_full_tenant_context(self) -> dict[str, Any]:
        """Get complete tenant context dict (Task 2.1).

        Returns:
            Tenant context dict combining tenant_context and context fields
        """
        result = dict(self.context)
        if self.tenant_context:
            result.update(self.tenant_context)
        if self.tenant_id:
            result["tenant_id"] = self.tenant_id
        return result
