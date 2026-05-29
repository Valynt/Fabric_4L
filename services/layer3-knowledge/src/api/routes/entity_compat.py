"""Allowed service-local exception for Layer 3 service wrapper.

Owner: layer3-knowledge
Removal/migration target: 2026-09-30
Reason: Compatibility shim for legacy Layer 3 entity route imports.

Canonical implementation lives in ``value_fabric.layer3.api.routes.entities``.
"""

from api.routes.entities import router

__all__ = ["router"]
