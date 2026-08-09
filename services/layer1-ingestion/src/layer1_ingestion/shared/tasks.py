"""Compatibility surface for Layer 1 Celery tasks.

Implementations are grouped by responsibility in ``task_runtime``,
``pipeline_tasks``, and ``event_tasks``. Existing imports, patch points, and
Celery task names remain available from this module.
"""

import sys
from types import ModuleType

from . import event_tasks as _event_tasks
from . import pipeline_tasks as _pipeline_tasks
from . import task_runtime as _task_runtime

_IMPLEMENTATIONS = (_task_runtime, _event_tasks, _pipeline_tasks)

# Preserve the historical module namespace, including private helpers used by
# internal callers and tests. Later, more-specific modules intentionally win
# when a shared import name appears in multiple implementation modules.
for _implementation in _IMPLEMENTATIONS:
    globals().update(
        {
            _name: _value
            for _name, _value in vars(_implementation).items()
            if not _name.startswith("__")
        }
    )


class _TaskCompatibilityModule(ModuleType):
    """Forward patched compatibility attributes to implementation modules."""

    def __setattr__(self, name, value):
        for implementation in _IMPLEMENTATIONS:
            if hasattr(implementation, name):
                setattr(implementation, name, value)
        super().__setattr__(name, value)


sys.modules[__name__].__class__ = _TaskCompatibilityModule
