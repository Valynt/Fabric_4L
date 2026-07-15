from __future__ import annotations

"""Regression tests for real scheduler task dispatch."""


from datetime import UTC, datetime

import pytest

from layer4_agents.engine.scheduler import TaskScheduler
from layer4_agents.engine.types import ScheduledTask


def _task(capability: str, parameters: dict | None = None) -> ScheduledTask:
    return ScheduledTask(
        priority=1,
        scheduled_time=datetime.now(UTC),
        task_id=f"task-{capability}",
        workflow_instance_id="wf-test",
        capability=capability,
        agent_type="test",
        parameters=parameters or {},
    )


@pytest.mark.asyncio
async def test_run_task_handler_executes_callable_parameter_handler() -> None:
    scheduler = TaskScheduler()

    async def handler(task: ScheduledTask) -> dict:
        return {"handled": task.task_id}

    result = await scheduler._run_task_handler(
        _task("custom", {"handler": handler})
    )

    assert result["status"] == "completed"
    assert result["result"] == {"handled": "task-custom"}


@pytest.mark.asyncio
async def test_run_task_handler_fails_unknown_capability() -> None:
    scheduler = TaskScheduler()

    with pytest.raises(RuntimeError, match="No task handler registered"):
        await scheduler._run_task_handler(_task("missing"))


@pytest.mark.asyncio
async def test_workflow_execution_invokes_workflow_run() -> None:
    class InitialState:
        pass

    class Workflow:
        def __init__(self) -> None:
            self.calls = []

        async def run(self, initial_state, thread_id=None):
            self.calls.append((initial_state, thread_id))
            return {"workflow_id": thread_id, "status": "completed"}

    workflow = Workflow()
    initial_state = InitialState()
    task = _task(
        "workflow_execution",
        {
            "workflow": workflow,
            "initial_state": initial_state,
            "workflow_id": "wf-real",
        },
    )

    result = await TaskScheduler()._run_task_handler(task)

    assert workflow.calls == [(initial_state, "wf-real")]
    assert result["result"] == {"workflow_id": "wf-real", "status": "completed"}
