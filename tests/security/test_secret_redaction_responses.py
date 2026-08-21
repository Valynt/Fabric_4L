"""Secret Redaction in API Responses Tests — P0 Gap Verification

Validates that secrets are redacted from JSON response bodies using
the redaction module. This tests the core redaction logic that should
be applied by response middleware.

Production Invariant: Secrets must be redacted from all API responses.

Author: Autonomous Test Assurance Agent
Date: 2026-06-24
"""

from __future__ import annotations

import pytest

try:
    from value_fabric.shared.security.redaction import REDACTED_VALUE, redact_value
    REDACTION_AVAILABLE = True
except ImportError:
    REDACTION_AVAILABLE = False


pytestmark = [
    pytest.mark.skipif(not REDACTION_AVAILABLE, reason="Redaction module not available"),
    pytest.mark.security,
    pytest.mark.secret_redaction,
    pytest.mark.p0,
]


class TestSecretRedactionInResponses:
    """Verify secret redaction logic for API response bodies."""

    def test_password_redacted_in_response_body(self):
        """P0: Passwords must be redacted in response bodies."""
        response_data = {"username": "testuser", "password": "secret123"}
        redacted = redact_value(response_data)

        assert redacted["username"] == "testuser"
        assert redacted["password"] == REDACTED_VALUE
        assert "secret123" not in str(redacted)

    def test_api_key_redacted_in_response_body(self):
        """P0: API keys must be redacted in response bodies."""
        response_data = {"api_key": "sk_test_dummy_abc123xyz789"}
        redacted = redact_value(response_data)

        assert redacted["api_key"] == REDACTED_VALUE
        assert "sk_test_dummy_abc123xyz789" not in str(redacted)

    def test_nested_secrets_redacted_in_response_body(self):
        """P0: Nested secrets must be redacted in response bodies."""
        response_data = {
            "host": "localhost",
            "credentials": {
                "username": "appuser",
                "password": "db_secret"
            }
        }
        redacted = redact_value(response_data)

        assert redacted["credentials"]["password"] == REDACTED_VALUE
        assert "db_secret" not in str(redacted)
        assert redacted["credentials"]["username"] == "appuser"

    def test_list_with_secrets_redacted_in_response_body(self):
        """P0: Lists containing secrets must be redacted."""
        response_data = [
            {"name": "key1", "api_key": "sk_test_dummy_abc123"},
            {"name": "key2", "api_key": "sk_test_dummy_def456"}
        ]
        redacted = redact_value(response_data)

        assert all(item["api_key"] == REDACTED_VALUE for item in redacted)

    def test_jwt_token_redacted_in_response_body(self):
        """P0: JWT tokens must be redacted in response bodies."""
        response_data = {
            "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwidGVuYW50X2lkIjoidGVzdF90ZW5hbnQifQ.dummy_test_signature_for_testing_only_12345"
        }
        redacted = redact_value(response_data)

        assert redacted["token"] == REDACTED_VALUE
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in str(redacted)

    def test_safe_data_not_modified(self):
        """POSITIVE: Safe data without secrets should not be modified."""
        response_data = {"name": "test", "value": 123}
        redacted = redact_value(response_data)

        assert redacted == {"name": "test", "value": 123}

    def test_multiple_secrets_redacted_in_response_body(self):
        """P0: Multiple secrets in one response must all be redacted."""
        response_data = {
            "password": "secret123",
            "api_key": "sk_test_dummy_abc123",
            "token": "token456",
            "username": "testuser"
        }
        redacted = redact_value(response_data)

        assert redacted["password"] == REDACTED_VALUE
        assert redacted["api_key"] == REDACTED_VALUE
        assert redacted["token"] == REDACTED_VALUE
        assert redacted["username"] == "testuser"

    def test_complex_nested_structure_redacted(self):
        """P0: Complex nested structures with secrets must be redacted."""
        response_data = {
            "user": {
                "name": "John",
                "credentials": {
                    "password": "user_pass",
                    "api_key": "aws_key_123"
                }
            }
        }
        redacted = redact_value(response_data)

        assert redacted["user"]["credentials"]["password"] == REDACTED_VALUE
        assert redacted["user"]["credentials"]["api_key"] == REDACTED_VALUE
        assert redacted["user"]["name"] == "John"

    def test_empty_response_body_handled(self):
        """POSITIVE: Empty response bodies should be handled gracefully."""
        response_data = {}
        redacted = redact_value(response_data)

        assert redacted == {}
