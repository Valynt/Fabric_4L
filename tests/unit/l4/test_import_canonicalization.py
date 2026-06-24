from __future__ import annotations

from datetime import UTC, datetime
from inspect import signature
import subprocess
import sys


def test_low_level_task_types_do_not_depend_on_layer4_runtime() -> None:
    from src.fabric.l4.types import ScheduledTask, TaskPriority, TaskStatus

    task = ScheduledTask(
        priority=TaskPriority.NORMAL.value,
        scheduled_time=datetime.now(UTC),
        task_id="task-1",
        workflow_instance_id="workflow-1",
        capability="workflow_execution",
        agent_type="OrchestrationController",
        context={"tenant_id": "tenant-a"},
        status=TaskStatus.PENDING,
    )

    assert task.get_tenant_id() == "tenant-a"
    assert task.get_full_tenant_context()["tenant_id"] == "tenant-a"


def test_canonical_type_and_core_package_imports_are_lazy() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys; "
                "import src.fabric.l4.types; "
                "import src.fabric.l4.core; "
                "import src.fabric.l4.core.scheduler; "
                "loaded = [m for m in sys.modules if m.startswith('layer4_agents')]; "
                "raise SystemExit(1 if loaded else 0)"
            ),
        ],
        cwd=".",
        check=False,
    )

    assert result.returncode == 0


def test_legacy_scheduler_uses_canonical_task_types() -> None:
    from layer4_agents.engine.scheduler import (
        ScheduledTask as LegacyScheduledTask,
        TaskPriority as LegacyTaskPriority,
        TaskStatus as LegacyTaskStatus,
    )
    from src.fabric.l4.types import ScheduledTask, TaskPriority, TaskStatus

    assert LegacyScheduledTask is ScheduledTask
    assert LegacyTaskPriority is TaskPriority
    assert LegacyTaskStatus is TaskStatus


def test_legacy_ports_use_canonical_task_execution_interfaces() -> None:
    from layer4_agents.engine import TaskExecutionPort as EnginePackagePort
    from layer4_agents.engine.ports import TaskExecutionPort as LegacyPort
    from src.fabric.l4.core import TaskExecutionPort as CorePort
    from src.fabric.l4.types import TaskExecutionPort, TaskSchedulerPort
    from layer4_agents.engine.scheduler import TaskScheduler

    assert LegacyPort is TaskExecutionPort
    assert EnginePackagePort is TaskExecutionPort
    assert CorePort is TaskExecutionPort
    assert isinstance(TaskScheduler(max_concurrent_tasks=1), TaskSchedulerPort)


def test_core_namespace_redirects_scheduler_without_new_runtime_copy() -> None:
    from layer4_agents.engine.scheduler import TaskScheduler
    from src.fabric.l4.core.scheduler import TaskScheduler as CoreTaskScheduler

    assert TaskScheduler is CoreTaskScheduler


def test_orchestration_controller_exposes_scheduler_dependency_injection() -> None:
    from layer4_agents.engine.executor import OrchestrationController

    assert "task_scheduler" in signature(OrchestrationController).parameters


def test_internal_transport_consumers_use_canonical_type_namespace() -> None:
    import layer4_agents.adapters.task_execution as task_execution_adapter
    import layer4_agents.engine.execution_dispatch as execution_dispatch
    import layer4_agents.engine.executor as executor
    from src.fabric.l4.types import ScheduledTask, TaskPriority

    assert task_execution_adapter.ScheduledTask is ScheduledTask
    assert execution_dispatch.ScheduledTask is ScheduledTask
    assert executor.ScheduledTask is ScheduledTask
    assert executor.TaskPriority is TaskPriority
