"""Compatibility alias for the canonical Layer 4 C1 route module."""

from __future__ import annotations

import sys

from layer4_agents.api.routes import c1 as _canonical

sys.modules[__name__] = _canonical
