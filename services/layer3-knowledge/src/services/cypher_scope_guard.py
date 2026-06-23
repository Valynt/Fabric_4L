from __future__ import annotations

"""Backward-compatibility shim for cypher_scope_guard (GOV-L3-006).

The canonical implementation lives in:
    services/layer3-knowledge/src/utils/cypher_security.py

This module re-exports the public API so existing callers do not need
immediate updates. Migrate callers to import directly from
``utils.cypher_security`` (within the Layer 3 service runtime) and remove
this shim once all consumers are updated.
"""


from src.utils.cypher_security import (  # noqa: F401
    ALLOWED_REL_TYPES,
    ALLOWED_TARGET_LABELS,
    TENANT_OWNED_LABELS,
    validate_cypher_identifier,
    validate_tenant_scoped_cypher,
)

__all__ = [
    "ALLOWED_REL_TYPES",
    "ALLOWED_TARGET_LABELS",
    "TENANT_OWNED_LABELS",
    "validate_cypher_identifier",
    "validate_tenant_scoped_cypher",
]
