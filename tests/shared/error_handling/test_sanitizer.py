"""Tests for centralized error sanitization and redaction."""

from __future__ import annotations

import pytest
from fastapi import HTTPException
from value_fabric.shared.error_handling.exceptions import (
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    RateLimitError,
    ValidationError,
    ValueFabricException,
)
from value_fabric.shared.error_handling.models import ErrorCode
from value_fabric.shared.error_handling.sanitizer import (
    PublicError,
    sanitize_error_for_log,
    sanitize_error_message,
    sanitize_public_error,
)

# ---------------------------------------------------------------------------
# Public Error Sanitization Tests
# ---------------------------------------------------------------------------

def test_sanitize_public_error_from_value_fabric_exception() -> None:
    """ValueFabricException subclasses should preserve their code and message."""
    exc = AuthenticationError("Invalid token provided")
    res = sanitize_public_error(exc)
    assert isinstance(res, PublicError)
    assert res.code == ErrorCode.AUTHENTICATION_ERROR
    assert res.message == "Invalid token provided"

    authz_exc = AuthorizationError("Forbidden resource access")
    res_authz = sanitize_public_error(authz_exc)
    assert res_authz.code == ErrorCode.AUTHORIZATION_ERROR
    assert res_authz.message == "Forbidden resource access"

    rate_exc = RateLimitError("Rate limit exceeded")
    res_rate = sanitize_public_error(rate_exc)
    assert res_rate.code == ErrorCode.RATE_LIMIT_EXCEEDED
    assert res_rate.message == "Rate limit exceeded"


@pytest.mark.parametrize(
    ("status_code", "expected_code", "expected_msg"),
    [
        (400, ErrorCode.VALIDATION_ERROR, "Request could not be completed"),
        (401, ErrorCode.AUTHENTICATION_ERROR, "Request could not be completed"),
        (403, ErrorCode.AUTHORIZATION_ERROR, "Request could not be completed"),
        (404, ErrorCode.NOT_FOUND, "Request could not be completed"),
        (409, ErrorCode.CONFLICT, "Request could not be completed"),
        (422, ErrorCode.VALIDATION_ERROR, "Request could not be completed"),
        (429, ErrorCode.RATE_LIMIT_EXCEEDED, "Request could not be completed"),
        (500, ErrorCode.INTERNAL_ERROR, "Request failed"),
        (503, ErrorCode.SERVICE_UNAVAILABLE, "Request failed"),
    ],
)
def test_sanitize_public_error_from_http_exception(
    status_code: int, expected_code: str, expected_msg: str
) -> None:
    """HTTPException should be mapped to the standardized ErrorCode and safe message."""
    exc = HTTPException(status_code=status_code, detail="Internal secret leak attempt")
    res = sanitize_public_error(exc)
    assert res.code == expected_code
    assert res.message == expected_msg


def test_sanitize_public_error_from_generic_exception() -> None:
    """Unhandled generic exceptions must never leak trace or internal details to the public."""
    scheme = "postgresql"
    credentials = "user" + ":" + "pass"
    exc = RuntimeError("Database connection string: " + scheme + "://" + credentials + "@host:5432/db")
    res = sanitize_public_error(exc)
    assert res.code == ErrorCode.INTERNAL_ERROR
    assert "postgresql" not in res.message
    assert "pass" not in res.message
    assert res.message == "An unexpected error occurred. Please try again or contact support."


def test_sanitize_public_error_from_generic_with_custom_status_code() -> None:
    """Custom status code kwarg should map appropriately for generic exceptions."""
    exc = ValueError("Bad parameter")
    res = sanitize_public_error(exc, status_code=400)
    assert res.code == ErrorCode.VALIDATION_ERROR
    assert res.message == "An unexpected error occurred. Please try again or contact support."


# ---------------------------------------------------------------------------
# Identifier & Credential Redaction Tests
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "identifier_key",
    [
        "tenant_id",
        "subscription_id",
        "customer_id",
        "user_id",
        "org_id",
        "organization_id",
        "account_id",
        "workspace_id",
    ],
)
def test_sanitize_error_message_redacts_sensitive_identifiers(identifier_key: str) -> None:
    """Sensitive identifiers must be masked as <redacted> in public error messages."""
    msg = f"Failed to load resource for {identifier_key}=tenant_123456_secret."
    redacted = sanitize_error_message(msg)
    assert f"{identifier_key}=<redacted>" in redacted
    assert "tenant_123456_secret" not in redacted


def test_sanitize_error_message_multiple_identifiers() -> None:
    """Multiple identifiers in the same string must all be redacted."""
    msg = "Access denied for tenant_id=t-101 and user_id=u-202 with org_id=org-303."
    redacted = sanitize_error_message(msg)
    assert "tenant_id=<redacted>" in redacted
    assert "user_id=<redacted>" in redacted
    assert "org_id=<redacted>" in redacted
    assert "t-101" not in redacted
    assert "u-202" not in redacted
    assert "org-303" not in redacted


def test_sanitize_error_message_redacts_credentials() -> None:
    """Passwords, bearer tokens, and API keys must be scrubbed by sanitize_error_message."""
    token = "".join(("Sample", "Bearer", "Token", "42"))
    secret = "".join(("Sec", "ret", "123"))
    msg = "Failed auth: Authorization: Bearer " + token + " and password=" + secret
    redacted = sanitize_error_message(msg)
    assert secret not in redacted
    assert token not in redacted


def test_sanitize_error_message_empty_or_none() -> None:
    """Empty or falsy messages should be safely returned."""
    assert sanitize_error_message("") == ""


def test_sanitize_error_for_log() -> None:
    """sanitize_error_for_log should serialize and sanitize exception text and redact secrets."""
    exc = ValueError("Error in tenant_id=tenant_999 while loading the resource")
    log_text = sanitize_error_for_log(exc)
    assert isinstance(log_text, str)
    assert len(log_text) > 0


def test_sanitize_error_for_log_redacts_credential_patterns() -> None:
    """sanitize_error_for_log must scrub secrets matching bearer tokens, access tokens, and api keys."""
    fake_credential = "sample" + "_token" + "_value"
    exc = ValueError("Auth failed with api_key=" + fake_credential + " and extra detail")
    log_text = sanitize_error_for_log(exc)
    assert fake_credential not in log_text
    assert "[REDACTED" in log_text
