"""Deprecated re-export shim; canonical home is layer4_agents.integration.connectors.core.errors."""

from __future__ import annotations

from layer4_agents.integration.connectors.core.errors import (
    AuthError,
    CRMError,
    IntegrityGateOpenError,
    MappingError,
    PermanentError,
    PermissionError_,
    TransientError,
    classify_http_status,
    classify_httpx_exception,
)

__all__ = [
    "CRMError",
    "TransientError",
    "AuthError",
    "PermissionError_",
    "MappingError",
    "PermanentError",
    "IntegrityGateOpenError",
    "classify_http_status",
    "classify_httpx_exception",
]