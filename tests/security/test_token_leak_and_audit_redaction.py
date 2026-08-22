"""Token Leak and Audit Redaction Regression Tests.

Ensures that sensitive credentials, session tokens, API keys, and internal
stack traces are never reflected in logs, error models, or public exception responses.
Uses production-grade redaction and error sanitization implementations from shared library.
"""

from __future__ import annotations

import logging
import pytest
from value_fabric.shared.security.redaction import (
    REDACTED_VALUE,
    RedactionFilter,
    is_sensitive_key,
    redact_credentials,
    redact_value,
)
from value_fabric.shared.error_handling.sanitizer import (
    sanitize_error_message,
)

pytestmark = [pytest.mark.security, pytest.mark.production_readiness]


def test_error_response_redacts_sensitive_bearer_tokens():
    raw_error_message = "Authentication failure for Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
    sanitized = sanitize_error_message(raw_error_message)
    assert REDACTED_VALUE in sanitized
    assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in sanitized


def test_database_url_password_redacted_in_logs():
    db_url = "https://admin:supersecretpass123@postgres.internal:5432/fabric_prod?password=supersecretpass123"
    masked = redact_credentials(db_url)
    assert REDACTED_VALUE in masked
    assert "supersecretpass123" not in masked


def test_api_key_header_redacted_in_audit_events():
    audit_event = {
        "event_id": "aud-12345",
        "actor": "user-456",
        "headers": {
            "Authorization": "Bearer vf_live_secrettoken123456789",
            "X-API-Key": "vfb_live_998877665544332211",
            "Content-Type": "application/json",
        },
    }

    sanitized_headers = redact_value(audit_event["headers"])
    assert sanitized_headers["Authorization"] == REDACTED_VALUE
    assert sanitized_headers["X-API-Key"] == REDACTED_VALUE
    assert sanitized_headers["Content-Type"] == "application/json"


def test_logging_redaction_filter():
    logger = logging.getLogger("test_redaction_logger")
    log_filter = RedactionFilter()
    record = logger.makeRecord(
        name="test_redaction_logger",
        level=logging.INFO,
        fn="test_file.py",
        lno=42,
        msg="User authenticated with api_key=sk-1234567890abcdef and password=secret",
        args=(),
        exc_info=None,
        extra={"api_key": "sk-1234567890abcdef", "safe_field": "public_data"},
    )
    assert log_filter.filter(record) is True
    assert "sk-1234567890abcdef" not in record.msg
    assert REDACTED_VALUE in record.msg
    assert record.api_key == REDACTED_VALUE
    assert record.safe_field == "public_data"
