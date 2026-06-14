"""Compatibility alias for canonical Layer 4 generation tools."""

from __future__ import annotations

import sys

from layer4_agents.tools import generation_tools as _canonical

sys.modules[__name__] = _canonical
