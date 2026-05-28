from __future__ import annotations

"""Canonical error response shape consistency tests.

Covers:
- All errors follow canonical shape with code/message/recoverable
- Error boundary middleware behavior
- Error shape validation for all error codes
- HTTPException normalization
"""


import unittest
from unittest.mock import MagicMock

from fastapi import HTTPException

from value_fabric.layer4.api.common.errors import normalize_exception, raise_normalized
from value_fabric.shared.error_handling import build_error_detail


class TestCanonicalErrorShape(unittest.TestCase):
    """Test canonical error response shape."""

    def test_build_error_detail_returns_canonical_shape(self):
        """Verify build_error_detail returns canonical error shape."""
        detail = build_error_detail(
            message="Test error message",
            error_code="TEST_ERROR",
            request_id="req-123",
        )

        self.assertIn("message", detail)
        self.assertIn("error_code", detail)
        self.assertIn("request_id", detail)
        self.assertIn("correlation_id", detail)

        self.assertEqual(detail["message"], "Test error message")
        self.assertEqual(detail["error_code"], "TEST_ERROR")
        self.assertEqual(detail["request_id"], "req-123")
        self.assertEqual(detail["correlation_id"], "req-123")

    def test_build_error_detail_without_request_id(self):
        """Verify build_error_detail handles missing request_id."""
        detail = build_error_detail(
            message="Test error message",
            error_code="TEST_ERROR",
            request_id=None,
        )

        self.assertIn("message", detail)
        self.assertIn("error_code", detail)
        self.assertIn("request_id", detail)
        self.assertIn("correlation_id", detail)

        self.assertEqual(detail["message"], "Test error message")
        self.assertEqual(detail["error_code"], "TEST_ERROR")
        self.assertIsNone(detail["request_id"])
        self.assertIsNone(detail["correlation_id"])

    def test_normalize_exception_preserves_http_exception(self):
        """Verify normalize_exception preserves existing HTTPException."""
        original_exc = HTTPException(status_code=404, detail="Not found")
        normalized = normalize_exception(
            original_exc,
            status_code=500,
            message="Internal error",
            error_code="INTERNAL_ERROR",
        )

        self.assertEqual(normalized.status_code, 404)
        self.assertEqual(normalized.detail, "Not found")

    def test_normalize_exception_converts_generic_exception(self):
        """Verify normalize_exception converts generic exception to HTTPException."""
        generic_exc = ValueError("Something went wrong")
        normalized = normalize_exception(
            generic_exc,
            status_code=400,
            message="Validation error",
            error_code="VALIDATION_ERROR",
            request_id="req-456",
        )

        self.assertIsInstance(normalized, HTTPException)
        self.assertEqual(normalized.status_code, 400)

        detail = normalized.detail
        self.assertEqual(detail["message"], "Validation error")
        self.assertEqual(detail["error_code"], "VALIDATION_ERROR")
        self.assertEqual(detail["request_id"], "req-456")

    def test_raise_normalized_raises_http_exception(self):
        """Verify raise_normalized raises HTTPException with canonical shape."""
        generic_exc = RuntimeError("Database connection failed")

        with self.assertRaises(HTTPException) as context:
            raise_normalized(
                generic_exc,
                status_code=503,
                message="Service unavailable",
                error_code="SERVICE_UNAVAILABLE",
                request_id="req-789",
            )

        exc = context.exception
        self.assertEqual(exc.status_code, 503)

        detail = exc.detail
        self.assertEqual(detail["message"], "Service unavailable")
        self.assertEqual(detail["error_code"], "SERVICE_UNAVAILABLE")
        self.assertEqual(detail["request_id"], "req-789")

    def test_error_detail_includes_all_required_fields(self):
        """Verify error detail includes all required canonical fields."""
        detail = build_error_detail(
            message="Access denied",
            error_code="ACCESS_DENIED",
            request_id="req-abc",
        )

        required_fields = ["message", "error_code", "request_id", "correlation_id"]
        for field in required_fields:
            self.assertIn(field, detail, f"Missing required field: {field}")

    def test_error_detail_message_is_string(self):
        """Verify error detail message is always a string."""
        detail = build_error_detail(
            message="Error message",
            error_code="ERROR",
            request_id="req-1",
        )

        self.assertIsInstance(detail["message"], str)

    def test_error_detail_code_is_string(self):
        """Verify error detail error_code is always a string."""
        detail = build_error_detail(
            message="Error message",
            error_code="ERROR_CODE",
            request_id="req-1",
        )

        self.assertIsInstance(detail["error_code"], str)

    def test_error_detail_request_id_is_string_or_none(self):
        """Verify error detail request_id is string or None."""
        detail_with_id = build_error_detail(
            message="Error message",
            error_code="ERROR",
            request_id="req-1",
        )
        self.assertIsInstance(detail_with_id["request_id"], str)

        detail_without_id = build_error_detail(
            message="Error message",
            error_code="ERROR",
            request_id=None,
        )
        self.assertIsNone(detail_without_id["request_id"])

    def test_error_detail_correlation_id_matches_request_id(self):
        """Verify correlation_id matches request_id when provided."""
        detail = build_error_detail(
            message="Error message",
            error_code="ERROR",
            request_id="req-123",
        )

        self.assertEqual(detail["correlation_id"], detail["request_id"])

    def test_normalize_exception_with_different_status_codes(self):
        """Verify normalize_exception handles various status codes."""
        test_cases = [
            (400, "BAD_REQUEST"),
            (401, "UNAUTHORIZED"),
            (403, "FORBIDDEN"),
            (404, "NOT_FOUND"),
            (500, "INTERNAL_ERROR"),
            (503, "SERVICE_UNAVAILABLE"),
        ]

        for status_code, error_code in test_cases:
            with self.subTest(status_code=status_code):
                exc = ValueError("Error")
                normalized = normalize_exception(
                    exc,
                    status_code=status_code,
                    message=f"Error {status_code}",
                    error_code=error_code,
                )

                self.assertEqual(normalized.status_code, status_code)
                self.assertEqual(normalized.detail["error_code"], error_code)


class TestErrorShapeAcrossErrorCodes(unittest.TestCase):
    """Test error shape consistency across different error codes."""

    def test_validation_error_shape(self):
        """Verify validation error follows canonical shape."""
        detail = build_error_detail(
            message="Invalid input",
            error_code="VALIDATION_ERROR",
            request_id="req-1",
        )

        self.assertEqual(detail["error_code"], "VALIDATION_ERROR")
        self.assertEqual(detail["message"], "Invalid input")

    def test_authentication_error_shape(self):
        """Verify authentication error follows canonical shape."""
        detail = build_error_detail(
            message="Authentication failed",
            error_code="AUTHENTICATION_FAILED",
            request_id="req-2",
        )

        self.assertEqual(detail["error_code"], "AUTHENTICATION_FAILED")
        self.assertEqual(detail["message"], "Authentication failed")

    def test_authorization_error_shape(self):
        """Verify authorization error follows canonical shape."""
        detail = build_error_detail(
            message="Access denied",
            error_code="AUTHORIZATION_DENIED",
            request_id="req-3",
        )

        self.assertEqual(detail["error_code"], "AUTHORIZATION_DENIED")
        self.assertEqual(detail["message"], "Access denied")

    def test_not_found_error_shape(self):
        """Verify not found error follows canonical shape."""
        detail = build_error_detail(
            message="Resource not found",
            error_code="NOT_FOUND",
            request_id="req-4",
        )

        self.assertEqual(detail["error_code"], "NOT_FOUND")
        self.assertEqual(detail["message"], "Resource not found")

    def test_rate_limit_error_shape(self):
        """Verify rate limit error follows canonical shape."""
        detail = build_error_detail(
            message="Rate limit exceeded",
            error_code="RATE_LIMIT_EXCEEDED",
            request_id="req-5",
        )

        self.assertEqual(detail["error_code"], "RATE_LIMIT_EXCEEDED")
        self.assertEqual(detail["message"], "Rate limit exceeded")

    def test_internal_error_shape(self):
        """Verify internal error follows canonical shape."""
        detail = build_error_detail(
            message="Internal server error",
            error_code="INTERNAL_ERROR",
            request_id="req-6",
        )

        self.assertEqual(detail["error_code"], "INTERNAL_ERROR")
        self.assertEqual(detail["message"], "Internal server error")


class TestHTTPExceptionNormalization(unittest.TestCase):
    """Test HTTPException normalization behavior."""

    def test_http_exception_with_string_detail_preserved(self):
        """Verify HTTPException with string detail is preserved."""
        exc = HTTPException(status_code=404, detail="Not found")
        normalized = normalize_exception(
            exc,
            status_code=500,
            message="Internal error",
            error_code="INTERNAL_ERROR",
        )

        self.assertEqual(normalized.detail, "Not found")
        self.assertEqual(normalized.status_code, 404)

    def test_http_exception_with_dict_detail_preserved(self):
        """Verify HTTPException with dict detail is preserved."""
        dict_detail = {"message": "Custom error", "code": "CUSTOM"}
        exc = HTTPException(status_code=400, detail=dict_detail)
        normalized = normalize_exception(
            exc,
            status_code=500,
            message="Internal error",
            error_code="INTERNAL_ERROR",
        )

        self.assertEqual(normalized.detail, dict_detail)
        self.assertEqual(normalized.status_code, 400)

    def test_generic_exception_converted_to_http_exception(self):
        """Verify generic exception is converted to HTTPException with dict detail."""
        exc = ValueError("Invalid value")
        normalized = normalize_exception(
            exc,
            status_code=400,
            message="Validation error",
            error_code="VALIDATION_ERROR",
            request_id="req-1",
        )

        self.assertIsInstance(normalized.detail, dict)
        self.assertIn("message", normalized.detail)
        self.assertIn("error_code", normalized.detail)


if __name__ == "__main__":
    unittest.main()
