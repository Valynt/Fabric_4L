"""Compatibility alias for the canonical Layer 4 CRM webhook routes."""

from __future__ import annotations

import sys

from layer4_agents.api.routes import crm_webhooks as _canonical

sys.modules[__name__] = _canonical
