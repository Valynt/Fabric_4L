"""Deprecated compatibility shim for Layer 3 tenant Neo4j dependencies.

Owner: layer3-knowledge
Deprecated since: 2026-05-19
Hard removal date: 2026-09-30
Reason: tenant-aware Neo4j dependencies moved to ``dependencies_tenant_secured``.

This module intentionally contains no tenant/session implementation. It exists
only to keep legacy imports working during the deprecation window while route
code migrates to the secured dependency wrapper.

Deprecation warning is emitted at import time. Direct re-exports preserve
FastAPI Depends() compatibility (function signatures are not wrapped).
"""

from __future__ import annotations

import logging
import warnings

logger = logging.getLogger(__name__)

_REMOVAL_DATE = "2026-09-30"
_CANONICAL_MODULE = "src.api.dependencies_tenant_secured"
_WARNING = (
    "src.api.dependencies_tenant is deprecated and will be removed on "
    f"{_REMOVAL_DATE}; use {_CANONICAL_MODULE} instead."
)

logger.warning("DEPRECATION: %s", _WARNING)
warnings.warn(_WARNING, DeprecationWarning, stacklevel=2)

# Direct re-exports — do NOT wrap; FastAPI Depends() inspects function signatures.
from .dependencies_tenant_secured import (  # noqa: E402,F401
    Neo4jTenantSession,
    Neo4jTenantSessionSecured,
    Neo4jTenantValidatedSession,
    create_neo4j_tenant_session,
    get_neo4j_secured,
    get_neo4j_with_optional_tenant,
    get_neo4j_with_tenant,
    get_neo4j_with_validation,
    get_query_validator,
    require_tenant_header_for_internal,
)

__all__ = [
    "Neo4jTenantSession",
    "Neo4jTenantSessionSecured",
    "Neo4jTenantValidatedSession",
    "create_neo4j_tenant_session",
    "get_neo4j_secured",
    "get_neo4j_with_optional_tenant",
    "get_neo4j_with_tenant",
    "get_neo4j_with_validation",
    "get_query_validator",
    "require_tenant_header_for_internal",
]
