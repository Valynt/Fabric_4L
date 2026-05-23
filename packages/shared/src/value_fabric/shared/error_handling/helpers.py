"""Shared helper utilities for API error payloads."""

from __future__ import annotations

from typing import Any, Optional

from .exceptions import (
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    ServiceUnavailableError,
    ValidationError,
    ValueFabricException,
)
from .models import ErrorCode


def build_error_detail(
    *,
    message: str,
    error_code: str,
    request_id: str | None = None,
    correlation_id: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a stable error detail envelope for HTTPException payloads."""
    payload: dict[str, Any] = {
        "message": message,
        "error_code": error_code,
        "request_id": request_id,
        "correlation_id": correlation_id or request_id,
    }
    if extra:
        payload.update(extra)
    return payload


def raise_validation_error(
    field: Optional[str] = None,
    message: str = "Validation failed",
    details: Optional[dict[str, Any]] = None,
) -> None:
    """Raise a validation error with standardized error code.

    Args:
        field: Optional field name that failed validation
        message: Human-readable error message
        details: Optional additional error context

    Raises:
        ValidationError: With VALIDATION_ERROR code and 422 status
    """
    raise ValidationError(message=message, field=field, details=details)


def raise_authentication_error(
    message: str = "Authentication failed",
    details: Optional[dict[str, Any]] = None,
) -> None:
    """Raise an authentication error with standardized error code.

    Args:
        message: Human-readable error message
        details: Optional additional error context

    Raises:
        AuthenticationError: With AUTHENTICATION_ERROR code and 401 status
    """
    raise AuthenticationError(message=message, details=details)


def raise_authorization_error(
    message: str = "Access denied",
    details: Optional[dict[str, Any]] = None,
) -> None:
    """Raise an authorization error with standardized error code.

    Args:
        message: Human-readable error message
        details: Optional additional error context

    Raises:
        AuthorizationError: With AUTHORIZATION_ERROR code and 403 status
    """
    raise AuthorizationError(message=message, details=details)


def raise_not_found_error(
    resource_type: str = "Resource",
    resource_id: Optional[str] = None,
    message: Optional[str] = None,
    details: Optional[dict[str, Any]] = None,
) -> None:
    """Raise a not found error with standardized error code.

    Args:
        resource_type: Type of resource that was not found
        resource_id: Optional ID of the resource
        message: Optional custom message (auto-generated if not provided)
        details: Optional additional error context

    Raises:
        NotFoundError: With NOT_FOUND code and 404 status
    """
    raise NotFoundError(
        resource_type=resource_type,
        resource_id=resource_id,
        message=message,
        details=details,
    )


def raise_conflict_error(
    message: str = "Resource conflict",
    details: Optional[dict[str, Any]] = None,
) -> None:
    """Raise a conflict error with standardized error code.

    Args:
        message: Human-readable error message
        details: Optional additional error context

    Raises:
        ValueFabricException: With CONFLICT code and 409 status
    """
    raise ValueFabricException(
        message=message,
        error_code=ErrorCode.CONFLICT,
        status_code=409,
        details=details,
    )


def raise_service_unavailable_error(
    service: Optional[str] = None,
    message: str = "Service temporarily unavailable",
    details: Optional[dict[str, Any]] = None,
) -> None:
    """Raise a service unavailable error with standardized error code.

    Args:
        service: Optional name of the unavailable service
        message: Human-readable error message
        details: Optional additional error context

    Raises:
        ServiceUnavailableError: With SERVICE_UNAVAILABLE code and 503 status
    """
    raise ServiceUnavailableError(service=service, message=message, details=details)


def raise_tenant_context_error(
    message: str = "Tenant context error",
    details: Optional[dict[str, Any]] = None,
) -> None:
    """Raise a tenant context error with standardized error code.

    Args:
        message: Human-readable error message
        details: Optional additional error context

    Raises:
        ValueFabricException: With INTERNAL_ERROR code and 500 status
    """
    raise ValueFabricException(
        message=message,
        error_code=ErrorCode.INTERNAL_ERROR,
        status_code=500,
        details=details,
    )

