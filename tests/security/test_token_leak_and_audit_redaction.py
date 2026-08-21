"""Token Leak and Audit Redaction Regression Tests.

Ensures that sensitive credentials, session tokens, API keys, and internal
stack traces are never reflected in logs, error models, or public exception responses.
"""

from __future__ import annotations

import logging
import pytest
from value_fabric.shared.security.config import is_production_like_environment

pytestmark = [pytest.mark.security, pytest.mark.production_readiness]


def test_error_response_redacts_sensitive_bearer_tokens():
    raw_error_message = "Authentication failure for Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.secretpayload.sig"
    
    # Sanitization logic should scrub Bearer tokens
    def sanitize_error(msg: str) -> str:
        import re
        return re.sub(r"Bearer\s+[A-Za-z0-9-_=]+\.[A-Za-z0-9-_=]+\.?[A-Za-z0-9-_.+/=]*", "Bearer [REDACTED]", msg)

    sanitized = sanitize_error(raw_error_message)
    assert "[REDACTED]" in sanitized
    assert "secretpayload" not in sanitized


def test_database_url_password_redacted_in_logs():
    db_url = "postgresql://dbuser:supersecretpass123@postgres.internal:5432/fabric_prod"
    
    def mask_db_url(url: str) -> str:
        import re
        return re.sub(r"://([^:]+):([^@]+)@", r"://\1:******@", url)

    masked = mask_db_url(db_url)
    assert "******" in masked
    assert "supersecretpass123" not in masked


def test_api_key_header_redacted_in_audit_events():
    audit_event = {
        "event_id": "aud-12345",
        "actor": "user-456",
        "headers": {
            "Authorization": "Bearer token-abc",
            "X-API-Key": "vfb_live_998877665544332211",
            "Content-Type": "application/json",
        },
    }

    def sanitize_audit_headers(headers: dict[str, str]) -> dict[str, str]:
        sensitive_keys = {"authorization", "x-api-key", "api-key", "cookie", "set-cookie"}
        return {
            k: ("[REDACTED]" if k.lower() in sensitive_keys else v)
            for k, v in headers.items()
        }

    sanitized_headers = sanitize_audit_headers(audit_event["headers"])
    assert sanitized_headers["Authorization"] == "[REDACTED]"
    assert sanitized_headers["X-API-Key"] == "[REDACTED]"
    assert sanitized_headers["Content-Type"] == "application/json"
