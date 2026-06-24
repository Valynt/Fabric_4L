"""Compatibility redirect for Layer 4 workflow state management."""

from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = ["StateManager"]  # noqa: F822 - exported lazily via __getattr__


def __getattr__(name: str) -> Any:
    if name != "StateManager":
        raise AttributeError(name)
    module = import_module("layer4_agents.engine.state_manager")
    value = getattr(module, name)
    globals()[name] = value
    return value
