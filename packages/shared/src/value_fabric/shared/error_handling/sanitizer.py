"""Centralized error sanitization for public API responses and logs."""

from __future__ import annotations

import re
from dataclasses import dataclass

from fastapi import HTTPException

from ..security.redaction import redact_credentials
from .exceptions import ValueFabricException
from .helpers import sanitize_log_error
from .models import ErrorCode


# Patterns that may expose tenant-scoped identifiers or internal IDs in public
# error messages.  These are redacted from API responses but remain available
# in internal logs and observability.
_SENSITIVE_IDENTIFIER_KEYS = (
    "tenant_id",
    "subscription_id",
    "customer_id",
    "user_id",
    "org_id",
    "organization_id",
    "account_id",
    "workspace_id",
)

# Match key=value pairs where key is a sensitive identifier.
# Examples: tenant_id=tenant_abc123, subscription_id=sub_xxx
_IDENTIFIER_REDACTION_RE = re.compile(
    rf"\b({'|'.join(_SENSITIVE_IDENTIFIER_KEYS)})=[A-Za-z0-9_\-:]+\b"
)


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


def sanitize_error_message(message: str) -> str:
    """Redact sensitive identifier values and credentials from public-facing error messages.

    Internal IDs (tenant, subscription, customer, user, org, workspace, account)
    are replaced with ``<redacted>`` to prevent cross-tenant information leakage
    and subscription identifier exposure. Credentials (passwords, tokens, API keys)
    are also redacted to prevent secret exposure. Generic guidance text is preserved
    so the response remains actionable.
    """
    if not message:
        return message
    # First redact identifiers
    message = _IDENTIFIER_REDACTION_RE.sub(lambda m: f"{m.group(1)}=<redacted>", message)
    # Then redact credentials (passwords, tokens, API keys)
    message = redact_credentials(message)
    return message


def sanitize_error_for_log(exc: BaseException) -> str:
    """Return redacted exception text for internal logs."""
    return sanitize_log_error(exc)
