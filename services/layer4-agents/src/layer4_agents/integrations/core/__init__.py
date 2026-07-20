"""Core CRM integration primitives: errors and value types."""

from __future__ import annotations

from .errors import (
    AuthError,
    CRMError,
    MappingError,
    PermissionError_,
    PermanentError,
    TransientError,
    classify_http_status,
    classify_httpx_exception,
)
from .state import (
    ErrorClass,
    ObservedStatus,
    OperationalStatus,
    reduce,
)
from .types import (
    CRMModel,
    CRMOperationResult,
    CanonicalRecord,
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
