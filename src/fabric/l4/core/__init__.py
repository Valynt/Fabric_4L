"""Lazy namespace redirects for the Layer 4 core engine."""

from __future__ import annotations

from importlib import import_module
from typing import Any

_EXPORTS = {
    "LegacyTaskExecutionAdapter": "layer4_agents.adapters.task_execution",
    "StateManager": "layer4_agents.engine.state_manager",
    "TaskExecutionPort": "src.fabric.l4.types",
    "TaskExecutionRequest": "src.fabric.l4.types",
    "TaskSchedulerPort": "src.fabric.l4.types",
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
