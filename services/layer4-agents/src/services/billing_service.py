"""Compatibility alias for the canonical Layer 4 billing service."""

from __future__ import annotations

import sys

from layer4_agents.services import billing_service as _canonical

sys.modules[__name__] = _canonical
