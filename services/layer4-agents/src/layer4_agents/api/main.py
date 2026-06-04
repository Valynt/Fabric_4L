from __future__ import annotations

"""Thin entrypoint for Layer 4 API."""

import os

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from value_fabric.shared.startup import reject_insecure_bypass_in_production

from .app_factory import create_app

# Initialize Sentry error tracking (no-op when SENTRY_DSN is unset)
sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    integrations=[FastApiIntegration()],
    traces_sample_rate=0.1,
    profiles_sample_rate=0.1,
)

reject_insecure_bypass_in_production(service_name="layer4-agents")
app = create_app()

# Phase 1 Clerk integration: verify the Fabric4L internal AuthContext envelope.
# No-op when FABRIC_AUTH_PUBLIC_KEYS is unset.
from value_fabric.shared.identity.fabric_auth import register_fabric_auth_from_env  # noqa: E402

register_fabric_auth_from_env(app, service_name="layer4-agents")
