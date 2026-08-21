"""Secret Redaction in Logs Tests — P0 Gap Verification

Validates that the RedactionFilter prevents secrets from leaking in logs.
Tests the existing redaction infrastructure integration with Python logging.

Production Invariant: Secrets must be redacted from all log outputs.
This test verifies the RedactionFilter integration.

Author: Autonomous Test Assurance Agent
Date: 2026-06-24
"""

from __future__ import annotations

import logging
from io import StringIO

import pytest

try:
    from value_fabric.shared.security.redaction import (
        REDACTED_VALUE,
        RedactionFilter,
        install_redaction_filter,
    )
    REDACTION_AVAILABLE = True
except ImportError:
    REDACTION_AVAILABLE = False


pytestmark = [
    pytest.mark.skipif(not REDACTION_AVAILABLE, reason="Redaction module not available"),
    pytest.mark.security,
    pytest.mark.secret_redaction,
    pytest.mark.p0,
]


class TestRedactionFilterInLogs:
    """Verify RedactionFilter prevents secrets in log messages."""

    def test_jwt_secret_redacted_in_log_message(self):
        """P0: JWT_SECRET must be redacted in log messages."""
        logger = logging.getLogger("test_jwt")
        logger.handlers.clear()
        
        # Capture log output
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(logging.Formatter("%(message)s"))
        
        # Install redaction filter
        filter_instance = RedactionFilter()
        handler.addFilter(filter_instance)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        
        # Log message with secret
        logger.info("Authentication failed with JWT_SECRET=dummy_super_secret_key_12345")
        
        # Check output
        log_output = stream.getvalue()
        assert "dummy_super_secret_key_12345" not in log_output, (
            "JWT_SECRET leaked in log message - REDACTION FILTER FAILED"
        )
        assert REDACTED_VALUE in log_output or "redacted" in log_output.lower()

    def test_password_redacted_in_log_message(self):
        """P0: Passwords must be redacted in log messages."""
        logger = logging.getLogger("test_password")
        logger.handlers.clear()
        
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(logging.Formatter("%(message)s"))
        
        filter_instance = RedactionFilter()
        handler.addFilter(filter_instance)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        
        logger.info("DB connection: password=dummy_db_password_123")
        
        log_output = stream.getvalue()
        assert "dummy_db_password_123" not in log_output, (
            "Password leaked in log message - REDACTION FILTER FAILED"
        )

    def test_api_key_redacted_in_log_message(self):
        """P0: API keys must be redacted in log messages."""
        logger = logging.getLogger("test_api_key")
        logger.handlers.clear()
        
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(logging.Formatter("%(message)s"))
        
        filter_instance = RedactionFilter()
        handler.addFilter(filter_instance)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        
        logger.info("API call with key=sk_test_dummy_abc123xyz789")
        
        log_output = stream.getvalue()
        assert "sk_test_dummy_abc123xyz789" not in log_output, (
            "API key leaked in log message - REDACTION FILTER FAILED"
        )

    def test_token_redacted_in_log_message(self):
        """P0: Tokens must be redacted in log messages."""
        logger = logging.getLogger("test_token")
        logger.handlers.clear()
        
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(logging.Formatter("%(message)s"))
        
        filter_instance = RedactionFilter()
        handler.addFilter(filter_instance)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        
        token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJkdW1teV9zdWJqZWN0XzEyMzQ1IiwidGVuYW50IjoidGVzdCJ9.dummy_test_signature_long_enough_12345"
        logger.info(f"Bearer {token}")
        
        log_output = stream.getvalue()
        assert token not in log_output, (
            "JWT token leaked in log message - REDACTION FILTER FAILED"
        )
    def test_sensitive_field_redacted_in_log_extra(self):
        """P0: Sensitive fields in log extra dict must be redacted."""
        logger = logging.getLogger("test_extra")
        logger.handlers.clear()
        
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(logging.Formatter("%(message)s %(password)s %(token)s"))
        
        filter_instance = RedactionFilter()
        handler.addFilter(filter_instance)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        
        logger.info("User login", extra={"password": "secret123", "token": "abc456"})
        
        log_output = stream.getvalue()
        assert "secret123" not in log_output
        assert "abc456" not in log_output

    def test_install_redaction_filter_function(self):
        """POSITIVE: install_redaction_filter adds filter to logger."""
        logger = logging.getLogger("test_install")
        logger.handlers.clear()
        
        # Install filter
        filter_instance = install_redaction_filter(logger)
        
        # Verify filter was added
        assert any(isinstance(f, RedactionFilter) for f in logger.filters)
        assert filter_instance is not None

    def test_safe_message_not_modified(self):
        """POSITIVE: Safe messages without secrets should not be modified."""
        logger = logging.getLogger("test_safe")
        logger.handlers.clear()
        
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(logging.Formatter("%(message)s"))
        
        filter_instance = RedactionFilter()
        handler.addFilter(filter_instance)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        
        logger.info("Request processed successfully")
        
        log_output = stream.getvalue()
        assert "Request processed successfully" in log_output


class TestRedactionFilterInStructuredLogs:
    """Verify redaction works with structured logging patterns."""

    def test_dict_with_sensitive_keys_redacted(self):
        """P0: Dicts with sensitive keys must be redacted."""
        from value_fabric.shared.security.redaction import redact_value
        
        data = {
            "user_id": "user-123",
            "password": "secret123",
            "api_key": "sk_test_dummy_abc123",
            "normal_field": "safe_value"
        }
        
        redacted = redact_value(data)
        
        assert redacted["password"] == REDACTED_VALUE
        assert redacted["api_key"] == REDACTED_VALUE
        assert redacted["user_id"] == "user-123"
        assert redacted["normal_field"] == "safe_value"

    def test_nested_dict_with_secrets_redacted(self):
        """P0: Nested dicts with secrets must be redacted."""
        from value_fabric.shared.security.redaction import redact_value
        
        data = {
            "config": {
                "database": {
                    "password": "db_secret",
                    "host": "localhost"
                }
            }
        }
        
        redacted = redact_value(data)
        
        assert redacted["config"]["database"]["password"] == REDACTED_VALUE
        assert redacted["config"]["database"]["host"] == "localhost"

    def test_list_with_secrets_redacted(self):
        """P0: Lists containing secrets must be redacted."""
        from value_fabric.shared.security.redaction import redact_value
        
        data = [
            {"api_key": "sk_test_dummy_abc123"},
            {"api_key": "sk_test_dummy_def456"}
        ]
        
        redacted = redact_value(data)
        
        assert all(item["api_key"] == REDACTED_VALUE for item in redacted)

    def test_string_with_url_with_secrets_redacted(self):
        """P0: URLs with secret query params must be redacted."""
        from value_fabric.shared.security.redaction import redact_credentials
        
        url = "https://api.example.com/endpoint?api_key=sk_test_dummy_abc123&token=xyz789"
        redacted = redact_credentials(url)
        
        assert "sk_test_dummy_abc123" not in redacted
        assert "xyz789" not in redacted
        assert REDACTED_VALUE in redacted
