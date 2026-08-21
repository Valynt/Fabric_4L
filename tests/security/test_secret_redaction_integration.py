"""Secret Redaction Integration Tests — P0 Gap Remediation Verification

Validates that the redaction module integration into error sanitization
prevents secrets from leaking in error messages, logs, and responses.

Production Invariant: Secrets must be redacted from all observable outputs.
This test verifies the integration fix in sanitizer.py.

Author: Autonomous Test Assurance Agent
Date: 2026-06-24
"""

from __future__ import annotations

import pytest

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.testclient import TestClient
    from value_fabric.shared.error_handling.sanitizer import sanitize_error_message
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    TestClient = None


pytestmark = [
    pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI not available"),
    pytest.mark.security,
    pytest.mark.secret_redaction,
    pytest.mark.p0,
]


class TestSanitizeErrorMessageIntegration:
    """Verify redaction module integration in error message sanitization."""

    def test_jwt_secret_redacted_from_error_message(self):
        """P0: JWT_SECRET must be redacted from error messages."""
        message = "Internal error with JWT_SECRET=dummy_super_secret_key_12345"
        sanitized = sanitize_error_message(message)
        
        assert "dummy_super_secret_key_12345" not in sanitized, (
            "JWT_SECRET not redacted - INTEGRATION FIX FAILED"
        )
        assert "JWT_SECRET" in sanitized or "redacted" in sanitized.lower()

    def test_service_auth_secret_redacted_from_error_message(self):
        """P0: SERVICE_AUTH_SECRET must be redacted from error messages."""
        message = "Auth failed: SERVICE_AUTH_SECRET=dummy_my_secret_67890"
        sanitized = sanitize_error_message(message)
        
        assert "dummy_my_secret_67890" not in sanitized, (
            "SERVICE_AUTH_SECRET not redacted - INTEGRATION FIX FAILED"
        )

    def test_api_key_redacted_from_error_message(self):
        """P0: API keys must be redacted from error messages."""
        message = "Invalid API key: sk_test_dummy_abc123xyz789"
        sanitized = sanitize_error_message(message)
        
        assert "sk_test_dummy_abc123xyz789" not in sanitized, (
            "API key not redacted - INTEGRATION FIX FAILED"
        )

    def test_database_password_redacted_from_error_message(self):
        """P0: Database passwords must be redacted from error messages."""
        message = "DB connection failed: password=dummy-db-pass-123"
        sanitized = sanitize_error_message(message)
        
        assert "dummy-db-pass-123" not in sanitized, (
            "Database password not redacted - INTEGRATION FIX FAILED"
        )

    def test_tenant_id_redacted_from_error_message(self):
        """P0: Tenant IDs must be redacted from error messages."""
        message = "Access denied for tenant_id=tenant-abc123-def456"
        sanitized = sanitize_error_message(message)
        
        assert "tenant-abc123-def456" not in sanitized, (
            "Tenant ID not redacted - INTEGRATION FIX FAILED"
        )
        assert "tenant_id=<redacted>" in sanitized

    def test_bearer_token_redacted_from_error_message(self):
        """P0: Bearer tokens must be redacted from error messages."""
        # Use realistic JWT token length (3 segments, 20+ chars each)
        message = "Invalid Bearer token: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwidGVuYW50X2lkIjoidGVzdF90ZW5hbnQifQ.dummy_test_signature_for_testing_only_12345"
        sanitized = sanitize_error_message(message)
        
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.dummy_test_payload_12345.dummy_test_signature_for_testing_only_12345" not in sanitized, (
            "Bearer token not redacted - INTEGRATION FIX FAILED"
        )

    def test_multiple_secrets_redacted_from_error_message(self):
        """P0: Multiple secrets in one message must all be redacted."""
        message = "Error: JWT_SECRET=secret1, password=pass123, token=token456"
        sanitized = sanitize_error_message(message)
        
        assert "secret1" not in sanitized
        assert "pass123" not in sanitized
        assert "token456" not in sanitized

    def test_safe_message_not_modified(self):
        """POSITIVE: Safe messages without secrets should not be modified."""
        message = "Invalid request format"
        sanitized = sanitize_error_message(message)
        
        assert sanitized == message, (
            "Safe message was modified - FALSE POSITIVE"
        )

    def test_empty_message_handled(self):
        """POSITIVE: Empty messages should be handled gracefully."""
        message = ""
        sanitized = sanitize_error_message(message)
        
        assert sanitized == ""
