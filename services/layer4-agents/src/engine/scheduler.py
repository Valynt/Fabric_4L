"""Compatibility shim for the canonical Layer 4 module.

The implementation lives in ``layer4_agents.engine.scheduler``. Keep this file as
a thin re-export during the namespace transition.
"""

from layer4_agents.engine.scheduler import *  # noqa: F401,F403
