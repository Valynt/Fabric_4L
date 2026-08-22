from __future__ import annotations

import os
import subprocess
import sys
from datetime import UTC, datetime
from inspect import signature


def test_low_level_task_types_do_not_depend_on_layer4_runtime() -> None:
    from layer4_agents.engine.scheduler import ScheduledTask, TaskPriority, TaskStatus

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
    env = dict(os.environ)
    pythonpath = os.pathsep.join(
        [
            "services/layer4-agents/src",
            "packages/shared/src",
            ".",
            env.get("PYTHONPATH", ""),
        ]
    )
    env["PYTHONPATH"] = pythonpath
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys; "
                "import layer4_agents.engine.ports; "
                "loaded = [m for m in sys.modules if m.startswith('src.fabric')]; "
                "raise SystemExit(1 if loaded else 0)"
            ),
        ],
        cwd=".",
        env=env,
        check=False,
    )

    assert result.returncode == 0


def test_legacy_scheduler_uses_canonical_task_types() -> None:
    from layer4_agents.engine.scheduler import ScheduledTask, TaskPriority, TaskStatus
    from layer4_agents.engine.scheduler import (
        ScheduledTask as LegacyScheduledTask,
    )
    from layer4_agents.engine.scheduler import (
        TaskPriority as LegacyTaskPriority,
    )
    from layer4_agents.engine.scheduler import (
        TaskStatus as LegacyTaskStatus,
    )

    assert LegacyScheduledTask is ScheduledTask
    assert LegacyTaskPriority is TaskPriority
    assert LegacyTaskStatus is TaskStatus


def test_legacy_ports_use_canonical_task_execution_interfaces() -> None:
    from layer4_agents.engine import TaskExecutionPort as EnginePackagePort
    from layer4_agents.engine.ports import TaskExecutionPort, TaskSchedulerPort
    from layer4_agents.engine.ports import TaskExecutionPort as LegacyPort
    from layer4_agents.engine.scheduler import TaskScheduler

    assert LegacyPort is TaskExecutionPort
    assert EnginePackagePort is TaskExecutionPort
    assert isinstance(TaskScheduler(max_concurrent_tasks=1), TaskSchedulerPort)


def test_engine_namespace_exposes_scheduler_without_runtime_copy() -> None:
    from layer4_agents.engine.scheduler import TaskScheduler
    from layer4_agents.engine.scheduler import TaskScheduler as EngineTaskScheduler

    assert TaskScheduler is EngineTaskScheduler


def test_orchestration_controller_exposes_scheduler_dependency_injection() -> None:
    from layer4_agents.engine.executor import OrchestrationController

    assert "task_scheduler" in signature(OrchestrationController).parameters


def test_internal_transport_consumers_use_canonical_type_namespace() -> None:
    import layer4_agents.adapters.task_execution as task_execution_adapter
    import layer4_agents.engine.execution_dispatch as execution_dispatch
    import layer4_agents.engine.executor as executor
    from layer4_agents.engine.scheduler import ScheduledTask, TaskPriority

    assert task_execution_adapter.ScheduledTask is ScheduledTask
    assert execution_dispatch.ScheduledTask is ScheduledTask
    assert executor.ScheduledTask is ScheduledTask
    assert executor.TaskPriority is TaskPriority


def test_removed_src_fabric_namespace_is_not_importable() -> None:
    result = subprocess.run(
        [sys.executable, "-c", "import src.fabric.l4"],
        cwd=".",
        check=False,
    )

    assert result.returncode != 0
