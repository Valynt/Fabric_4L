"""Compatibility redirect for Layer 4 workflow executor classes."""

from __future__ import annotations

from importlib import import_module
from typing import Any

_EXPORTS = {
    "CheckpointConflictError",
    "OrchestrationController",
    "WorkflowExecutionError",
    "WorkflowExecutor",
}

__all__ = sorted(_EXPORTS)


def __getattr__(name: str) -> Any:
    if name not in _EXPORTS:
        raise AttributeError(name)
    module = import_module("layer4_agents.engine.executor")
    value = getattr(module, name)
    globals()[name] = value
    return value
