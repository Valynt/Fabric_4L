"""Compatibility shim for the canonical Layer 4 module.

The implementation lives in ``layer4_agents.api.common.audit``. Keep this file as a thin
re-export only so the packaged source of truth remains ``layer4_agents``.
"""

from layer4_agents.api.common.audit import *  # noqa: F401,F403
