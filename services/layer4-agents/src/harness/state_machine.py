"""Compatibility shim for the canonical Layer 4 module.

The implementation lives in ``layer4_agents.harness.state_machine``. Keep this file as a thin
re-export only so the packaged source of truth remains ``layer4_agents``.
"""

from layer4_agents.harness.state_machine import *  # noqa: F401,F403
