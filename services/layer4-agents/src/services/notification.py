"""Compatibility alias for the canonical Layer 4 notification service."""

from __future__ import annotations

import sys

from layer4_agents.services import notification as _canonical

sys.modules[__name__] = _canonical
