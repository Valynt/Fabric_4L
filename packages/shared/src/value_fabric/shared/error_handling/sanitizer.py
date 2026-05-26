"""Centralized error sanitization for public API responses and logs."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import HTTPException

from .exceptions import ValueFabricException
from .helpers import sanitize_log_error
from .models import ErrorCode


@dataclass(frozen=True)
class PublicError:
    code: str
    message: str


_STATUS_CODE_MAP: dict[int, str] = {
    400: ErrorCode.VALIDATION_ERROR,
    401: ErrorCode.AUTHENTICATION_ERROR,
    403: ErrorCode.AUTHORIZATION_ERROR,
    404: ErrorCode.NOT_FOUND,
    409: ErrorCode.CONFLICT,
    422: ErrorCode.VALIDATION_ERROR,
    429: ErrorCode.RATE_LIMIT_EXCEEDED,
    500: ErrorCode.INTERNAL_ERROR,
    503: ErrorCode.SERVICE_UNAVAILABLE,
}


def sanitize_public_error(exc: BaseException, *, status_code: int = 500) -> PublicError:
    """Return a contract-stable, safe public error payload."""
    if isinstance(exc, ValueFabricException):
        return PublicError(code=exc.error_code, message=exc.message)
    if isinstance(exc, HTTPException):
        return PublicError(
            code=_STATUS_CODE_MAP.get(exc.status_code, ErrorCode.INTERNAL_ERROR),
            message="Request failed" if exc.status_code >= 500 else "Request could not be completed",
        )
    return PublicError(
        code=_STATUS_CODE_MAP.get(status_code, ErrorCode.INTERNAL_ERROR),
        message="An unexpected error occurred. Please try again or contact support.",
    )


def sanitize_error_for_log(exc: BaseException) -> str:
    """Return redacted exception text for internal logs."""
    return sanitize_log_error(exc)
