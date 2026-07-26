"""CRM integration abstractions: connectors, state reducer, and provider implementations."""

from __future__ import annotations

from .core.connector import CRMConnector, CRMWriteConnector
from .core.errors import (
    AuthError,
    CRMError,
    MappingError,
    PermanentError,
    PermissionError_,
    TransientError,
    classify_http_status,
    classify_httpx_exception,
)
from .core.state import (
    ErrorClass,
    ObservedStatus,
    OperationalStatus,
    reduce,
)
from .core.types import (
    CanonicalRecord,
    CRMModel,
    CRMOperationResult,
    SyncCursor,
)
from .factory import get_connector, get_write_connector

__all__ = [
    "CRMConnector",
    "CRMWriteConnector",
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
    "get_connector",
    "get_write_connector",
    "CRMModel",
    "CanonicalRecord",
    "SyncCursor",
    "CRMOperationResult",
]
