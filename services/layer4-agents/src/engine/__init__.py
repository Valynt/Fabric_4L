"""Compatibility shim for the canonical Layer 4 module.

The implementation lives in ``layer4_agents.engine``. Keep this file as a thin
re-export only so the packaged source of truth remains ``layer4_agents``.
"""

import warnings

warnings.warn(
    "engine is deprecated; import runtime APIs from layer4_agents.runtime.",
    DeprecationWarning,
    stacklevel=2,
)

from layer4_agents.engine import *  # noqa: F401,F403
