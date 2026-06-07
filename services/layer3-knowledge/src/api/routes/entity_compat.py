"""Allowed service-local exception for Layer 3 service wrapper.

Owner: layer3-knowledge
Removal/migration target: 2026-09-30
Reason: Compatibility shim for legacy Layer 3 entity route imports.

Canonical implementation lives in ``api.routes.entities`` within
``services/layer3-knowledge/src``.
"""

from src.api.routes.entities import router

__all__ = ["router"]
