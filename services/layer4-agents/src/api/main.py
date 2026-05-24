"""Thin entrypoint for Layer 4 API."""

from __future__ import annotations

from value_fabric.shared.startup import reject_insecure_bypass_in_production

from .app_factory import create_app

reject_insecure_bypass_in_production(service_name="layer4-agents")
app = create_app()

# Phase 1 Clerk integration: verify the Fabric4L internal AuthContext envelope.
# No-op when FABRIC_AUTH_PUBLIC_KEYS is unset.
from value_fabric.shared.identity.fabric_auth import register_fabric_auth_from_env  # noqa: E402

register_fabric_auth_from_env(app, service_name="layer4-agents")
