"""Compatibility alias for the canonical Layer 4 checkpoints routes."""

from __future__ import annotations

import sys

from layer4_agents.api.routes import checkpoints as _canonical

sys.modules[__name__] = _canonical
