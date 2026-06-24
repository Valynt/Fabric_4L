"""Compatibility shim for the canonical Layer 4 module.

The implementation lives in ``src.fabric.l4.core.scheduler``. Keep this file as
a thin re-export during the namespace transition.
"""

from src.fabric.l4.core.scheduler import *  # noqa: F401,F403
