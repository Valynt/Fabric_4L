"""Deprecated re-export shim for the CRM connector subsystem.

The canonical home for these modules is ``layer4_agents.integration.connectors``.
This package re-exports the canonical modules so that any external consumer
that still resolves the old ``layer4_agents.integrations.*`` path keeps
working. Do NOT add new imports here; import from the canonical location.
"""

from __future__ import annotations

from layer4_agents.integration.connectors import (
    CRMConnector,
    CRMWriteConnector,
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
    get_connector,
    get_write_connector,
)

__all__ = [
    "CRMConnector",
    "CRMWriteConnector",
    "AuthError",
    "CRMError",
    "MappingError",
    "PermanentError",
    "PermissionError_",
    "TransientError",
    "classify_http_status",
    "classify_httpx_exception",
    "ErrorClass",
    "ObservedStatus",
    "OperationalStatus",
    "reduce",
    "CanonicalRecord",
    "CRMModel",
    "CRMOperationResult",
    "SyncCursor",
    "get_connector",
    "get_write_connector",
]