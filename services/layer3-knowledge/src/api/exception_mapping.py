from __future__ import annotations

"""Allowed service-local exception for Layer 3 service wrapper.

Owner: layer3-knowledge
Removal/migration target: 2026-09-30
Reason: Utilities for mapping domain/infrastructure exceptions to HTTP errors.
"""


from typing import Any

from fastapi import HTTPException
from value_fabric.shared.error_handling.exceptions import NotFoundError

from ..api.exceptions import (
    ContractViolationError,
    DatabaseError,
    SearchError,
    TenantAccessError,
    ValidationError,
    VectorStoreError,
)


def map_exception_to_http_error(exc: Exception, *, context: dict[str, Any]) -> HTTPException:
    """Convert known exceptions into consistent HTTPException envelopes."""
    if isinstance(exc, HTTPException):
        return exc

    if isinstance(exc, ValidationError):
        return HTTPException(
            status_code=422,
            detail={"code": "VALIDATION_ERROR", "message": exc.message, "context": context},
        )

    if isinstance(exc, NotFoundError):
        return HTTPException(
            status_code=404,
            detail={"code": "NOT_FOUND", "message": getattr(exc, "message", str(exc)), "context": context},
        )

    if isinstance(exc, TenantAccessError):
        return HTTPException(
            status_code=403,
            detail={"code": "TENANT_ACCESS_DENIED", "message": "Tenant authorization failed", "context": context},
        )

    if isinstance(exc, ContractViolationError):
        return HTTPException(
            status_code=500,
            detail={"code": "CONTRACT_VIOLATION", "message": "Service contract violated", "context": context},
        )

    if isinstance(exc, (DatabaseError, VectorStoreError)):
        return HTTPException(
            status_code=503,
            detail={"code": "DEPENDENCY_UNAVAILABLE", "message": "Data backend unavailable", "context": context},
        )

    if isinstance(exc, SearchError):
        return HTTPException(
            status_code=502,
            detail={"code": "SEARCH_BACKEND_ERROR", "message": "Search backend request failed", "context": context},
        )

    if isinstance(exc, TimeoutError):
        return HTTPException(
            status_code=504,
            detail={"code": "UPSTREAM_TIMEOUT", "message": "Upstream dependency timed out", "context": context},
        )

    return HTTPException(
        status_code=500,
        detail={"code": "INTERNAL_ERROR", "message": "Unexpected server fault", "context": context},
    )
