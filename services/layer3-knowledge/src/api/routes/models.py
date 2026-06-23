"""Allowed service-local exception for Layer 3 service wrapper.

Owner: layer3-knowledge
Removal/migration target: 2026-09-30
Reason: Compatibility shim for value_fabric.layer3.api.routes.models.
"""
from ..auth_context import _get_tenant_context  # noqa: F401
from .models_router import *  # noqa: F401,F403
