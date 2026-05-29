from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from .scheduler import ScheduledTask


def build_workflow_task(*, priority: int, workflow_id: str, tenant_id: str | None, user_id: str | None, workflow_type: str, workflow: Any, initial_state: Any, checkpoint_interval: int, handler: Any) -> ScheduledTask:
    return ScheduledTask(
        priority=priority,
        scheduled_time=datetime.now(UTC),
        task_id=f"wf-{workflow_id}",
        workflow_instance_id=workflow_id,
        capability="workflow_execution",
        agent_type="OrchestrationController",
        context={"tenant_id": tenant_id, "user_id": user_id, "workflow_type": workflow_type},
        parameters={
            "workflow": workflow,
            "initial_state": initial_state,
            "workflow_id": workflow_id,
            "checkpoint_interval": checkpoint_interval,
            "handler": handler,
        },
        tenant_id=tenant_id,
        tenant_context={
            "tenant_id": tenant_id,
            "user_id": user_id,
            "workflow_type": workflow_type,
            "auth_source": "workflow_execution",
        },
    )
