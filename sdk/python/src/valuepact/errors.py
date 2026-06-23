"""Stable ValuePact CLI error and exit-code contract."""

from __future__ import annotations

from valuefabric.errors import (
    APIError,
    AuthenticationError,
    ConfigurationError,
    ConnectionError,
    NotFoundError,
    RateLimitError,
    ValidationError,
    ValueFabricError,
)

EXIT_INVALID = 2
EXIT_AUTHENTICATION = 3
EXIT_AUTHORIZATION = 4
EXIT_DOMAIN = 5
EXIT_NOT_FOUND = 6
EXIT_RETRYABLE = 7
EXIT_INTERNAL = 8
EXIT_INTERRUPTED = 130


class CliError(Exception):
    """Command failure with a stable symbolic code."""

    def __init__(
        self,
        code: str,
        message: str,
        exit_code: int,
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.exit_code = exit_code
        self.retryable = retryable


def map_exception(exc: BaseException) -> CliError:
    """Translate application and infrastructure exceptions to CLI errors."""

    if isinstance(exc, CliError):
        return exc
    if isinstance(exc, KeyboardInterrupt):
        return CliError("INTERRUPTED", "Interrupted by user.", EXIT_INTERRUPTED)
    if isinstance(exc, (ConfigurationError, ValidationError, ValueError)):
        return CliError("INVALID_ARGUMENT", str(exc), EXIT_INVALID)
    if isinstance(exc, AuthenticationError):
        return CliError("AUTHENTICATION_REQUIRED", str(exc), EXIT_AUTHENTICATION)
    if isinstance(exc, PermissionError):
        return CliError("AUTHORIZATION_DENIED", str(exc), EXIT_AUTHORIZATION)
    if isinstance(exc, NotFoundError):
        return CliError("RESOURCE_NOT_FOUND", str(exc), EXIT_NOT_FOUND)
    if isinstance(exc, (ConnectionError, RateLimitError)):
        code = "RATE_LIMITED" if isinstance(exc, RateLimitError) else "SERVICE_UNAVAILABLE"
        return CliError(code, str(exc), EXIT_RETRYABLE, retryable=True)
    if isinstance(exc, APIError):
        if exc.status_code in {401, 403}:
            return CliError("AUTHORIZATION_DENIED", str(exc), EXIT_AUTHORIZATION)
        if exc.status_code == 404:
            return CliError("RESOURCE_NOT_FOUND", str(exc), EXIT_NOT_FOUND)
        if exc.status_code >= 500:
            return CliError("SERVICE_UNAVAILABLE", str(exc), EXIT_RETRYABLE, retryable=True)
        return CliError("DOMAIN_CONFLICT", str(exc), EXIT_DOMAIN)
    if isinstance(exc, ValueFabricError):
        return CliError("DOMAIN_CONFLICT", str(exc), EXIT_DOMAIN)
    return CliError("INTERNAL_ERROR", "Unexpected internal failure.", EXIT_INTERNAL)
