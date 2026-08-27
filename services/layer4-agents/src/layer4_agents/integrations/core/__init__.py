"""Deprecated re-export shim; canonical home is layer4_agents.integration.connectors.core."""

from __future__ import annotations

from layer4_agents.integration.connectors.core import (
    AuthError,
    CRMError,
    MappingError,
    PermanentError,
    PermissionError_,
    TransientError,
    classify_http_status,
    classify_httpx_exception,
    ErrorClass,
    ObservedStatus,
    OperationalStatus,
    reduce,
    CanonicalRecord,
    CRMModel,
    CRMOperationResult,
    SyncCursor,
)

__all__ = [
    "CRMError",
    "TransientError",
    "AuthError",
    "PermissionError_",
    "MappingError",
    "PermanentError",
    "classify_http_status",
    "classify_httpx_exception",
    "OperationalStatus",
    "ObservedStatus",
    "ErrorClass",
    "reduce",
    "CRMModel",
    "SyncCursor",
    "CanonicalRecord",
    "CRMOperationResult",
]