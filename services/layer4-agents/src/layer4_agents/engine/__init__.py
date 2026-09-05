from __future__ import annotations

"""Engine package for workflow execution."""

import warnings
from importlib import import_module
from typing import Any

warnings.warn(
    "layer4_agents.engine is a legacy compatibility package; use "
    "layer4_agents.runtime and its adapters for new integrations.",
    DeprecationWarning,
    stacklevel=2,
)

_EXPORTS = {
    "LegacyTaskExecutionAdapter": "layer4_agents.adapters.task_execution",
    "StateManager": "layer4_agents.engine.state_manager",
    "TaskExecutionPort": "layer4_agents.engine.ports",
    "TaskExecutionRequest": "layer4_agents.engine.ports",
    "TaskSchedulerPort": "layer4_agents.engine.ports",
    "WorkflowExecutionError": "layer4_agents.engine.executor",
    "WorkflowExecutor": "layer4_agents.engine.executor",
    "as_task_execution_port": "layer4_agents.adapters.task_execution",
}

__all__ = sorted(_EXPORTS)


def __getattr__(name: str) -> Any:
    if name not in _EXPORTS:
        raise AttributeError(name)
    module = import_module(_EXPORTS[name])
    value = getattr(module, name)
    globals()[name] = value
    return value
