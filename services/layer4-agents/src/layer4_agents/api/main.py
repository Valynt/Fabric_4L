from __future__ import annotations

"""Thin Layer 4 release entrypoint; application assembly belongs in the factory."""

from value_fabric.shared.observability.sentry_init import init_sentry
from value_fabric.shared.startup import reject_insecure_bypass_in_production

from .app_factory import create_app

init_sentry(service_name="layer4-agents", release="0.2.0")

reject_insecure_bypass_in_production(service_name="layer4-agents")
# Keep this module importable by ASGI servers without defining a second
# bootstrap path. All application assembly must remain in ``app_factory``.
app = create_app()

# Phase 1 Clerk integration: verify the Fabric4L internal AuthContext envelope.
# No-op when FABRIC_AUTH_PUBLIC_KEYS is unset.
from value_fabric.shared.identity.fabric_auth import register_fabric_auth_from_env  # noqa: E402

register_fabric_auth_from_env(app, service_name="layer4-agents")
