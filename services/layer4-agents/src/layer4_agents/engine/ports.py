from __future__ import annotations

"""Compatibility redirects for Layer 4 task execution ports.

The dependency-free definitions live in ``src.fabric.l4.types``.
"""

from src.fabric.l4.types import TaskExecutionPort, TaskExecutionRequest, TaskSchedulerPort

__all__ = ["TaskExecutionPort", "TaskExecutionRequest", "TaskSchedulerPort"]
