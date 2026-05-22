"""Thin entrypoint for Layer 4 API."""

from __future__ import annotations

from value_fabric.shared.startup import reject_insecure_bypass_in_production

from .app_factory import create_app

reject_insecure_bypass_in_production(service_name="layer4-agents")
app = create_app()
