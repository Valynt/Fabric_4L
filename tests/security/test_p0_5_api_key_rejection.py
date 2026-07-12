"""Regression tests for P0-5: API Key rejection in layers without DB access.

These tests verify that layers without database access properly reject API key
authentication with clear logging.
"""

import logging

import pytest
from value_fabric.shared.identity.api_key_stub import (
    reject_api_key_unsupported,
    reject_api_key_with_error,
)


class TestApiKeyRejection:
    """Test API key rejection in layers without database access."""

    def test_reject_api_key_unsupported_returns_none(self):
        """reject_api_key_unsupported must always return None."""
        result = reject_api_key_unsupported("some-api-key")
        assert result is None

    def test_reject_api_key_unsupported_logs_warning(self, caplog):
        """reject_api_key_unsupported must log a warning."""
        with caplog.at_level(logging.WARNING):
            reject_api_key_unsupported("test-key-123")

        assert "API key authentication rejected" in caplog.text
        assert "Use JWT Bearer tokens instead" in caplog.text

    def test_reject_api_key_with_error_returns_none(self):
        """reject_api_key_with_error must always return None."""
        result = reject_api_key_with_error("some-api-key")
        assert result is None

    def test_reject_api_key_with_error_logs_error(self, caplog):
        """reject_api_key_with_error must log an error."""
        with caplog.at_level(logging.ERROR):
            reject_api_key_with_error("test-key-123")

        assert "rejected" in caplog.text
        assert "disabled in this layer" in caplog.text

    def test_reject_api_key_does_not_leak_full_key(self, caplog):
        """Only first 8 characters of key should be logged."""
        with caplog.at_level(logging.ERROR):
            reject_api_key_with_error("super-secret-key-that-is-long")

        # Should log truncated key (8 chars)
        assert "super-se" in caplog.text
        # Should NOT log beyond 8 chars
        assert "super-secr" not in caplog.text

    def test_reject_api_key_short_key_masked(self, caplog):
        """Short keys below minimum should be masked with ***."""
        with caplog.at_level(logging.ERROR):
            reject_api_key_with_error("ab")  # 2 chars, below _KEY_PREVIEW_SHORT (4)

        assert "'ab...'" not in caplog.text
        assert "***" in caplog.text

    def test_reject_api_key_non_string_input(self, caplog):
        """Non-string input should be handled gracefully without raising."""
        with caplog.at_level(logging.ERROR):
            # Should not raise
            result = reject_api_key_with_error(None)  # type: ignore
            assert result is None

        assert "***" in caplog.text  # Should show placeholder

    def test_reject_api_key_unsupported_with_short_key(self, caplog):
        """reject_api_key_unsupported should also mask short keys."""
        with caplog.at_level(logging.WARNING):
            reject_api_key_unsupported("xy")  # 2 chars

        assert "'xy...'" not in caplog.text
        assert "***" in caplog.text

    @pytest.mark.parametrize("candidate", ["", "   ", "\n\t", "key with spaces", "🔥not-ascii🔥"])
    def test_reject_api_key_unsupported_handles_malformed_inputs(self, caplog, candidate: str):
        """Malformed API key candidates should be rejected and safely masked."""
        with caplog.at_level(logging.WARNING):
            result = reject_api_key_unsupported(candidate)
        assert result is None
        assert "API key authentication rejected" in caplog.text

    @pytest.mark.parametrize("token", ["x.y", "x.y.z.extra", "..", "header.payload.", ".payload.sig"])
    def test_reject_api_key_with_error_never_treats_jwt_like_input_as_valid(self, caplog, token: str):
        """JWT-like malformed values must still be rejected as API keys in DB-less layers."""
        with caplog.at_level(logging.ERROR):
            result = reject_api_key_with_error(token)
        assert result is None
        assert "rejected" in caplog.text
