"""Allowed service-local exception for Layer 3 service wrapper.

Owner: layer3-knowledge
Removal/migration target: 2026-09-30
Reason: Custom exception classes for Value Fabric Layer 3 API.
"""

from typing import Any

from fastapi import HTTPException


class ValueFabricException(Exception):
    """Base exception class for Value Fabric Layer 3."""

    def __init__(
        self,
        message: str,
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ):
        """Initialize Value Fabric exception.

        Args:
            message: Human-readable error message
            error_code: Machine-readable error code
            details: Additional error context
            cause: Original exception that caused this error
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        self.cause = cause

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary for API responses."""
        result = {
            "error": self.error_code,
            "message": self.message,
            "type": self.__class__.__name__,
        }

        if self.details:
            result["details"] = self.details

        if self.cause:
            result["cause"] = str(self.cause)

        return result


class ValidationError(ValueFabricException):
    """Raised when input validation fails."""

    def __init__(
        self,
        message: str,
        field: str | None = None,
        value: Any | None = None,
        validation_rule: str | None = None,
        **kwargs,
    ):
        """Initialize validation error.

        Args:
            message: Error message
            field: Field that failed validation
            value: The invalid value
            validation_rule: Rule that was violated
        """
        details = kwargs.pop("details", {})

        if field:
            details["field"] = field

        if value is not None:
            details["invalid_value"] = str(value)

        if validation_rule:
            details["validation_rule"] = validation_rule

        super().__init__(
            message, error_code="VALIDATION_ERROR", details=details, **kwargs
        )


class DatabaseError(ValueFabricException):
    """Raised when database operations fail."""

    def __init__(
        self,
        message: str,
        operation: str | None = None,
        query: str | None = None,
        database: str | None = None,
        error_code: str = "DATABASE_ERROR",
        **kwargs,
    ):
        """Initialize database error.

        Args:
            message: Error message
            operation: Database operation that failed
            query: Query that failed (sanitized)
            database: Database name
            error_code: Error code for this exception type
        """
        details = kwargs.pop("details", {})

        if operation:
            details["operation"] = operation

        if query:
            # Sanitize query to prevent exposing sensitive data
            details["query"] = query[:100] + "..." if len(query) > 100 else query

        if database:
            details["database"] = database

        super().__init__(message, error_code=error_code, details=details, **kwargs)


class Neo4jError(DatabaseError):
    """Raised when Neo4j operations fail."""

    def __init__(
        self,
        message: str,
        constraint: str | None = None,
        index: str | None = None,
        **kwargs,
    ):
        """Initialize Neo4j error.

        Args:
            message: Error message
            constraint: Constraint that caused the error
            index: Index that caused the error
        """
        details = kwargs.pop("details", {})

        if constraint:
            details["constraint"] = constraint

        if index:
            details["index"] = index

        super().__init__(message, error_code="NEO4J_ERROR", details=details, **kwargs)


class VectorStoreError(ValueFabricException):
    """Raised when vector store operations fail."""

    def __init__(
        self,
        message: str,
        index: str | None = None,
        namespace: str | None = None,
        operation: str | None = None,
        **kwargs,
    ):
        """Initialize vector store error.

        Args:
            message: Error message
            index: Vector index name
            namespace: Vector namespace
            operation: Operation that failed
        """
        details = kwargs.pop("details", {})

        if index:
            details["index"] = index

        if namespace:
            details["namespace"] = namespace

        if operation:
            details["operation"] = operation

        super().__init__(
            message, error_code="VECTOR_STORE_ERROR", details=details, **kwargs
        )


class IngestionError(ValueFabricException):
    """Raised when data ingestion fails."""

    def __init__(
        self,
        message: str,
        source_id: str | None = None,
        job_id: str | None = None,
        stage: str | None = None,
        **kwargs,
    ):
        """Initialize ingestion error.

        Args:
            message: Error message
            source_id: Source document ID
            job_id: Ingestion job ID
            stage: Ingestion stage that failed
        """
        details = kwargs.pop("details", {})

        if source_id:
            details["source_id"] = source_id

        if job_id:
            details["job_id"] = job_id

        if stage:
            details["stage"] = stage

        super().__init__(
            message, error_code="INGESTION_ERROR", details=details, **kwargs
        )


class SearchError(ValueFabricException):
    """Raised when search operations fail."""

    def __init__(
        self,
        message: str,
        query: str | None = None,
        search_type: str | None = None,
        index: str | None = None,
        **kwargs,
    ):
        """Initialize search error.

        Args:
            message: Error message
            query: Search query
            search_type: Type of search (vector, hybrid, etc.)
            index: Search index used
        """
        details = kwargs.pop("details", {})

        if query:
            details["query"] = query[:100] + "..." if len(query) > 100 else query

        if search_type:
            details["search_type"] = search_type

        if index:
            details["index"] = index

        super().__init__(message, error_code="SEARCH_ERROR", details=details, **kwargs)


class AnalyticsError(ValueFabricException):
    """Raised when analytics operations fail."""

    def __init__(
        self,
        message: str,
        algorithm: str | None = None,
        parameters: dict[str, Any] | None = None,
        **kwargs,
    ):
        """Initialize analytics error.

        Args:
            message: Error message
            algorithm: Analytics algorithm that failed
            parameters: Algorithm parameters
        """
        details = kwargs.pop("details", {})

        if algorithm:
            details["algorithm"] = algorithm

        if parameters:
            # Sanitize parameters to prevent exposing sensitive data
            sanitized_params = {k: str(v)[:100] for k, v in parameters.items()}
            details["parameters"] = sanitized_params

        super().__init__(
            message, error_code="ANALYTICS_ERROR", details=details, **kwargs
        )


class TenantAccessError(ValueFabricException):
    """Raised when tenant context is missing or invalid for an operation."""

    def __init__(self, message: str = "Tenant context required", **kwargs):
        super().__init__(message, error_code="TENANT_ACCESS_DENIED", **kwargs)


class ContractViolationError(ValueFabricException):
    """Raised when data violates expected service/API contract shape."""

    def __init__(self, message: str = "Contract violation", **kwargs):
        super().__init__(message, error_code="CONTRACT_VIOLATION", **kwargs)


class ConfigurationError(ValueFabricException):
    """Raised when configuration is invalid."""

    def __init__(
        self,
        message: str,
        setting: str | None = None,
        expected_type: str | None = None,
        current_value: Any | None = None,
        **kwargs,
    ):
        """Initialize configuration error.

        Args:
            message: Error message
            setting: Configuration setting name
            expected_type: Expected type/value
            current_value: Current invalid value
        """
        details = kwargs.pop("details", {})

        if setting:
            details["setting"] = setting

        if expected_type:
            details["expected_type"] = expected_type

        if current_value is not None:
            details["current_value"] = str(current_value)

        super().__init__(
            message, error_code="CONFIGURATION_ERROR", details=details, **kwargs
        )


class AuthenticationError(ValueFabricException):
    """Raised when authentication fails."""

    def __init__(
        self,
        message: str = "Authentication failed",
        method: str | None = None,
        reason: str | None = None,
        **kwargs,
    ):
        """Initialize authentication error.

        Args:
            message: Error message
            method: Authentication method used
            reason: Reason for failure
        """
        details = kwargs.pop("details", {})

        if method:
            details["method"] = method

        if reason:
            details["reason"] = reason

        super().__init__(
            message, error_code="AUTHENTICATION_ERROR", details=details, **kwargs
        )


class AuthorizationError(ValueFabricException):
    """Raised when authorization fails."""

    def __init__(
        self,
        message: str = "Access denied",
        resource: str | None = None,
        action: str | None = None,
        required_permission: str | None = None,
        **kwargs,
    ):
        """Initialize authorization error.

        Args:
            message: Error message
            resource: Resource being accessed
            action: Action being attempted
            required_permission: Permission required
        """
        details = kwargs.pop("details", {})

        if resource:
            details["resource"] = resource

        if action:
            details["action"] = action

        if required_permission:
            details["required_permission"] = required_permission

        super().__init__(
            message, error_code="AUTHORIZATION_ERROR", details=details, **kwargs
        )


class RateLimitError(ValueFabricException):
    """Raised when rate limits are exceeded."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        limit: int | None = None,
        window_seconds: int | None = None,
        retry_after: int | None = None,
        **kwargs,
    ):
        """Initialize rate limit error.

        Args:
            message: Error message
            limit: Rate limit that was exceeded
            window_seconds: Time window in seconds
            retry_after: Seconds to wait before retry
        """
        details = kwargs.pop("details", {})

        if limit:
            details["limit"] = limit

        if window_seconds:
            details["window_seconds"] = window_seconds

        if retry_after:
            details["retry_after"] = retry_after

        super().__init__(
            message, error_code="RATE_LIMIT_ERROR", details=details, **kwargs
        )


class ServiceUnavailableError(ValueFabricException):
    """Raised when a service is unavailable."""

    def __init__(
        self,
        message: str,
        service: str | None = None,
        retry_after: int | None = None,
        **kwargs,
    ):
        """Initialize service unavailable error.

        Args:
            message: Error message
            service: Service name
            retry_after: Seconds to wait before retry
        """
        details = kwargs.pop("details", {})

        if service:
            details["service"] = service

        if retry_after:
            details["retry_after"] = retry_after

        super().__init__(
            message, error_code="SERVICE_UNAVAILABLE", details=details, **kwargs
        )


# HTTP Exception helpers
def create_http_exception(
    status_code: int,
    exception: ValueFabricException,
    headers: dict[str, str] | None = None,
) -> HTTPException:
    """Create HTTPException from ValueFabric exception.

    Args:
        status_code: HTTP status code
        exception: ValueFabric exception
        headers: Additional headers

    Returns:
        HTTPException with structured error response
    """
    return HTTPException(
        status_code=status_code, detail=exception.to_dict(), headers=headers
    )


def create_validation_http_exception(
    message: str, field: str | None = None, value: Any | None = None, **kwargs
) -> HTTPException:
    """Create HTTP 400 validation exception.

    Args:
        message: Validation error message
        field: Field that failed validation
        value: Invalid value

    Returns:
        HTTPException with validation error
    """
    validation_error = ValidationError(
        message=message, field=field, value=value, **kwargs
    )

    return create_http_exception(400, validation_error)


def create_not_found_http_exception(
    message: str,
    resource_type: str | None = None,
    resource_id: str | None = None,
    **kwargs,
) -> HTTPException:
    """Create HTTP 404 not found exception.

    Args:
        message: Error message
        resource_type: Type of resource not found
        resource_id: ID of resource not found

    Returns:
        HTTPException with not found error
    """
    details = kwargs.pop("details", {})

    if resource_type:
        details["resource_type"] = resource_type

    if resource_id:
        details["resource_id"] = resource_id

    not_found_error = ValueFabricException(
        message=message, error_code="NOT_FOUND", details=details, **kwargs
    )

    return create_http_exception(404, not_found_error)


def create_conflict_http_exception(
    message: str,
    conflict_type: str | None = None,
    existing_resource: str | None = None,
    **kwargs,
) -> HTTPException:
    """Create HTTP 409 conflict exception.

    Args:
        message: Error message
        conflict_type: Type of conflict
        existing_resource: Existing resource causing conflict

    Returns:
        HTTPException with conflict error
    """
    details = kwargs.pop("details", {})

    if conflict_type:
        details["conflict_type"] = conflict_type

    if existing_resource:
        details["existing_resource"] = existing_resource

    conflict_error = ValueFabricException(
        message=message, error_code="CONFLICT", details=details, **kwargs
    )

    return create_http_exception(409, conflict_error)


def create_rate_limit_http_exception(
    limit: int, window_seconds: int, retry_after: int, **kwargs
) -> HTTPException:
    """Create HTTP 429 rate limit exception.

    Args:
        limit: Rate limit that was exceeded
        window_seconds: Time window in seconds
        retry_after: Seconds to wait before retry

    Returns:
        HTTPException with rate limit error
    """
    rate_limit_error = RateLimitError(
        limit=limit, window_seconds=window_seconds, retry_after=retry_after, **kwargs
    )

    headers = {"Retry-After": str(retry_after)}
    return create_http_exception(429, rate_limit_error, headers)


def create_service_unavailable_http_exception(
    message: str, service: str | None = None, retry_after: int | None = None, **kwargs
) -> HTTPException:
    """Create HTTP 503 service unavailable exception.

    Args:
        message: Error message
        service: Service name
        retry_after: Seconds to wait before retry

    Returns:
        HTTPException with service unavailable error
    """
    service_error = ServiceUnavailableError(
        message=message, service=service, retry_after=retry_after, **kwargs
    )

    headers = {}
    if retry_after:
        headers["Retry-After"] = str(retry_after)

    return create_http_exception(503, service_error, headers)
