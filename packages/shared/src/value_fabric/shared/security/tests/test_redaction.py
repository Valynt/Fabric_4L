"""Tests for shared credential/PII redaction helpers."""

from __future__ import annotations

import pytest

from ..redaction import redact_credentials


class TestRedactCredentials:
    """Regression tests for redact_credentials PII coverage."""

    def test_email_is_redacted(self):
        assert "alice@example.com" not in redact_credentials("Contact alice@example.com")
        assert "[REDACTED]" in redact_credentials("Contact alice@example.com")

    def test_ssn_is_redacted(self):
        assert "123-45-6789" not in redact_credentials("SSN: 123-45-6789")
        assert "[REDACTED]" in redact_credentials("SSN: 123-45-6789")

    def test_phone_is_redacted(self):
        assert "555-123-4567" not in redact_credentials("Phone: 555-123-4567")
        assert "[REDACTED]" in redact_credentials("Phone: 555-123-4567")

    def test_credit_card_is_redacted(self):
        assert "4111-1111-1111-1111" not in redact_credentials("Card: 4111-1111-1111-1111")
        assert "[REDACTED]" in redact_credentials("Card: 4111-1111-1111-1111")

    def test_uuid_is_not_redacted_as_credit_card(self):
        uuid_value = "00000000-0000-0000-0000-000000000001"
        assert uuid_value in redact_credentials(f"tenant_id={uuid_value}")

    def test_multiple_pii_types_in_one_message(self):
        message = "Email alice@example.com, phone 555-123-4567, SSN 123-45-6789"
        redacted = redact_credentials(message)
        assert "alice@example.com" not in redacted
        assert "555-123-4567" not in redacted
        assert "123-45-6789" not in redacted
        assert redacted.count("[REDACTED]") == 3

    def test_non_sensitive_text_is_preserved(self):
        message = "Account acme status active region us-east-1"
        assert redact_credentials(message) == message
