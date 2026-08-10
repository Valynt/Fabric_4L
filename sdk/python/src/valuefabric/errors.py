"""Custom exceptions for the Value Fabric SDK."""

from __future__ import annotations

from typing import Any


class ValueFabricError(Exception):
    """Base exception for all SDK errors with safe request context."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        endpoint: str | None = None,
        response_body: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.endpoint = endpoint
        self.response_body = response_body


class ConfigurationError(ValueFabricError):
    """SDK configuration is invalid or missing."""


class ConnectionError(ValueFabricError):
    """Failed to connect to the API."""


class AuthenticationError(ValueFabricError):
    """API key or JWT token is invalid or expired."""


class ValidationError(ValueFabricError):
    """Request validation failed (400 Bad Request)."""


class NotFoundError(ValueFabricError):
    """Requested resource was not found (404)."""


class RateLimitError(ValueFabricError):
    """Rate limit exceeded (429)."""

    def __init__(
        self,
        message: str,
        *,
        retry_after: int | None = None,
        status_code: int | None = None,
        endpoint: str | None = None,
        response_body: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            status_code=status_code,
            endpoint=endpoint,
            response_body=response_body,
        )
        self.retry_after = retry_after


class APIError(ValueFabricError):
    """Generic API error (5xx or unexpected status)."""


class ResponseError(ValueFabricError):
    """A successful HTTP response could not be decoded or validated."""
