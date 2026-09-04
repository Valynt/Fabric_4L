"""Custom exception classes for Value Fabric services."""

from typing import Any, Optional

from .models import ErrorCode


class ValueFabricException(Exception):
    """Base exception for all Value Fabric services.

    Provides standardized error handling with codes, trace IDs, and
    sanitized details suitable for API responses.
    """

    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.INTERNAL_ERROR,
        status_code: int = 500,
        details: Optional[dict[str, Any]] = None,
    ):
        """Initialize the exception.

        Args:
            message: Human-readable error message
            error_code: Machine-readable error code
            status_code: HTTP status code for API responses
            details: Optional additional context (sanitized in production)
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}

    def to_dict(self, include_details: bool = True) -> dict[str, Any]:
        """Convert exception to dictionary for API responses.

        Args:
            include_details: Whether to include details (False in production)

        Returns:
            Dictionary representation of the error
        """
        result = {
            "code": self.error_code,
            "message": self.message,
        }
        if include_details and self.details:
            result["details"] = self.details
        return result


class AuthenticationError(ValueFabricException):
    """Raised when authentication fails."""

    def __init__(
        self,
        message: str = "Authentication failed",
        error_code: ErrorCode = ErrorCode.AUTHENTICATION_ERROR,
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=401,
            details=details,
        )


class AuthorizationError(ValueFabricException):
    """Raised when user lacks required permissions."""

    def __init__(
        self,
        message: str = "Access denied",
        error_code: ErrorCode = ErrorCode.AUTHORIZATION_ERROR,
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=403,
            details=details,
        )


class TenantIsolationError(ValueFabricException):
    """Raised when tenant scoping or cross-tenant access checks fail."""

    def __init__(
        self,
        message: str = "Tenant access denied",
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            error_code=ErrorCode.TENANT_ISOLATION_ERROR,
            status_code=403,
            details=details,
        )


class NotFoundError(ValueFabricException):
    """Raised when a requested resource is not found."""

    def __init__(
        self,
        resource_type: str = "Resource",
        resource_id: Optional[str] = None,
        message: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
        error_code: ErrorCode = ErrorCode.NOT_FOUND,
    ):
        error_msg = message or (
            f"{resource_type} not found"
            + (f" with id '{resource_id}'" if resource_id else "")
        )
        error_details = details or {}
        if resource_id:
            error_details["resource_id"] = resource_id
        error_details["resource_type"] = resource_type

        super().__init__(
            message=error_msg,
            error_code=error_code,
            status_code=404,
            details=error_details,
        )


class ValidationError(ValueFabricException):
    """Raised when input validation fails."""

    def __init__(
        self,
        message: str = "Validation failed",
        field: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        error_details = details or {}
        if field:
            error_details["field"] = field

        super().__init__(
            message=message,
            error_code=ErrorCode.VALIDATION_ERROR,
            status_code=422,
            details=error_details,
        )


class RateLimitError(ValueFabricException):
    """Raised when rate limit is exceeded."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[int] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        error_details = details or {}
        if retry_after:
            error_details["retry_after_seconds"] = retry_after

        super().__init__(
            message=message,
            error_code=ErrorCode.RATE_LIMIT_EXCEEDED,
            status_code=429,
            details=error_details,
        )


class ServiceUnavailableError(ValueFabricException):
    """Raised when a dependent service is unavailable."""

    def __init__(
        self,
        message: str = "Service temporarily unavailable",
        service: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        error_details = details or {}
        if service:
            error_details["service"] = service

        super().__init__(
            message=message,
            error_code=ErrorCode.SERVICE_UNAVAILABLE,
            status_code=503,
            details=error_details,
        )


class ConflictError(ValueFabricException):
    """Raised when a request conflicts with current state."""

    def __init__(
        self,
        message: str = "Conflict",
        error_code: ErrorCode = ErrorCode.CONFLICT,
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=409,
            details=details,
        )


class BadRequestError(ValueFabricException):
    """Raised when request input is malformed."""

    def __init__(
        self,
        message: str = "Bad request",
        error_code: ErrorCode = ErrorCode.INVALID_PARAMETER,
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=400,
            details=details,
        )
