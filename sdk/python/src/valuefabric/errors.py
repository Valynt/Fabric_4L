"""Custom exceptions for the Value Fabric SDK."""

from __future__ import annotations

from typing import Any


class ValueFabricError(Exception):
    """Base exception for all SDK errors."""

    def __init__(self, message: str, *, response_body: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.response_body = response_body


class ConfigurationError(ValueFabricError):
    """SDK configuration is invalid or missing."""

    pass


class ConnectionError(ValueFabricError):
    """Failed to connect to the API."""

    pass


class AuthenticationError(ValueFabricError):
    """API key or JWT token is invalid or expired."""

    pass


class ValidationError(ValueFabricError):
    """Request validation failed (400 Bad Request)."""

    pass


class NotFoundError(ValueFabricError):
    """Requested resource was not found (404)."""

    pass


class RateLimitError(ValueFabricError):
    """Rate limit exceeded (429)."""

    def __init__(
        self,
        message: str,
        *,
        retry_after: int | None = None,
        response_body: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, response_body=response_body)
        self.retry_after = retry_after


class APIError(ValueFabricError):
    """Generic API error (5xx or unexpected status)."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int,
        response_body: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, response_body=response_body)
        self.status_code = status_code
