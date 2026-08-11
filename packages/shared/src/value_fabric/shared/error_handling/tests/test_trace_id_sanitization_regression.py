"""Regression tests for trace ID sanitization fixes (2026-05-28).

These tests prevent regression of the P0 bugs fixed in the code review:
1. Removed sanitize_trace_id() call in RequestIDMiddleware
2. Generator parameter inconsistency in resolve_trace_context
"""

import pytest
from unittest.mock import MagicMock, patch
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from value_fabric.shared.error_handling.middleware import RequestIDMiddleware
from value_fabric.shared.observability.trace_context import (
    resolve_trace_context,
    sanitize_trace_id,
    _new_trace_id,
)


class TestTraceIdSanitizationRegression:
    """Regression tests for trace ID sanitization bug fixes."""

    def test_middleware_always_sanitizes_trace_id(self):
        """Regression test: middleware must call sanitize_trace_id even after refactors.
        
        This test verifies that the middleware code path includes sanitization.
        If sanitization is removed again, this test will fail.
        """
        # Create a custom generator to track if it was called
        generator_calls = []
        
        def custom_generator():
            generator_calls.append("called")
            return "custom-gen-id"
        
        # Create app with middleware
        app = FastAPI()
        app.add_middleware(RequestIDMiddleware, generator=custom_generator)
        
        @app.get("/test")
        async def test_endpoint(request: Request):
            return {"trace_id": getattr(request.state, "trace_id", None)}
        
        client = TestClient(app)
        
        # Test with malicious trace ID
        resp = client.get("/test", headers={"X-Request-ID": "<script>alert(1)</script>"})
        assert resp.status_code == 200
        trace_id = resp.json()["trace_id"]
        
        # Verify trace ID was sanitized (no script tags)
        assert "<script>" not in trace_id
        assert ">" not in trace_id
        
        # Verify it starts with req_ (from sanitization, not custom generator)
        assert trace_id.startswith("req_")

    def test_trace_id_with_null_bytes_rejected(self):
        """Adversarial test: null bytes in trace ID should be rejected."""
        app = FastAPI()
        app.add_middleware(RequestIDMiddleware)
        
        @app.get("/test")
        async def test_endpoint(request: Request):
            return {"trace_id": getattr(request.state, "trace_id", None)}
        
        client = TestClient(app)
        
        # Test with null bytes
        malicious_id = "req_\x00abc\x00def"
        resp = client.get("/test", headers={"X-Request-ID": malicious_id})
        assert resp.status_code == 200
        trace_id = resp.json()["trace_id"]
        
        # Verify null bytes were removed and new ID generated
        assert "\x00" not in trace_id
        # Should be regenerated since null bytes make it invalid
        assert trace_id != malicious_id

    def test_trace_id_with_sql_injection_rejected(self):
        """Adversarial test: SQL injection patterns in trace ID should be rejected."""
        app = FastAPI()
        app.add_middleware(RequestIDMiddleware)
        
        @app.get("/test")
        async def test_endpoint(request: Request):
            return {"trace_id": getattr(request.state, "trace_id", None)}
        
        client = TestClient(app)
        
        # Test with SQL injection pattern
        malicious_id = "req_' OR 1=1 --"
        resp = client.get("/test", headers={"X-Request-ID": malicious_id})
        assert resp.status_code == 200
        trace_id = resp.json()["trace_id"]
        
        # Verify SQL injection pattern was sanitized
        assert "'" not in trace_id
        assert "OR" not in trace_id.upper() or trace_id.startswith("req_")
        assert "--" not in trace_id

    def test_trace_id_with_xss_rejected(self):
        """Adversarial test: XSS patterns in trace ID should be rejected."""
        app = FastAPI()
        app.add_middleware(RequestIDMiddleware)
        
        @app.get("/test")
        async def test_endpoint(request: Request):
            return {"trace_id": getattr(request.state, "trace_id", None)}
        
        client = TestClient(app)
        
        # Test with XSS pattern
        malicious_id = "req_<img src=x onerror=alert(1)>"
        resp = client.get("/test", headers={"X-Request-ID": malicious_id})
        assert resp.status_code == 200
        trace_id = resp.json()["trace_id"]
        
        # Verify XSS pattern was sanitized
        assert "<img" not in trace_id
        assert "onerror" not in trace_id
        assert "alert" not in trace_id

    def test_generator_parameter_passed_on_invalid_id(self):
        """Verify generator parameter is used when invalid ID triggers regeneration.
        
        This test verifies the fix for the generator parameter inconsistency bug
        where resolve_trace_context was not passing the generator to sanitize_trace_id.
        """
        # Create a custom generator
        def custom_generator():
            return "custom-gen-123"
        
        # Test with invalid trace ID that will trigger regeneration
        invalid_id = "<script>invalid</script>"
        headers = {"X-Request-ID": invalid_id}
        
        # Call resolve_trace_context with custom generator
        result = resolve_trace_context(headers, generator=custom_generator)
        
        # Verify the regenerated ID uses the custom generator
        # (not the default UUID generator)
        assert result.trace_id == "req_custom-gen-123"
        assert result.source_header == "X-Request-ID"

    def test_generator_parameter_used_on_empty_id(self):
        """Verify generator parameter is used when empty ID triggers regeneration."""
        def custom_generator():
            return "empty-gen-456"
        
        # Test with empty trace ID
        headers = {"X-Request-ID": ""}
        result = resolve_trace_context(headers, generator=custom_generator)
        
        # Verify the regenerated ID uses the custom generator
        assert result.trace_id == "req_empty-gen-456"

    def test_too_long_valid_id_is_truncated_not_regenerated(self):
        """Too-long but pattern-valid IDs are truncated, not regenerated.

        The generator is only used when regeneration actually triggers
        (empty or invalid characters); length alone is handled by
        truncation to MAX_TRACE_ID_LENGTH. Governs the same path as
        test_trace_id_truncation_respects_max_length.
        """
        def custom_generator():
            return "long-gen-789"

        long_id = "a" * 200
        headers = {"X-Request-ID": long_id}
        result = resolve_trace_context(headers, generator=custom_generator)

        from value_fabric.shared.observability.trace_context import MAX_TRACE_ID_LENGTH
        assert result.trace_id == "a" * MAX_TRACE_ID_LENGTH

    def test_sanitize_trace_id_receives_generator(self):
        """Verify sanitize_trace_id receives generator parameter when needed.
        
        This is a unit test for the internal function to ensure the
        generator parameter is passed through correctly.
        """
        def custom_generator():
            return "unit-test-gen"
        
        # Test with invalid ID that will trigger regeneration
        invalid_id = "<invalid>"
        result = sanitize_trace_id(invalid_id, generator=custom_generator)
        
        # Verify custom generator was used
        assert result == "req_unit-test-gen"

    def test_valid_trace_id_uses_generator_only_when_needed(self):
        """Verify generator is NOT used when trace ID is already valid."""
        def custom_generator():
            return "should-not-be-used"
        
        # Test with valid trace ID
        valid_id = "req_abc123def456"
        result = sanitize_trace_id(valid_id, generator=custom_generator)
        
        # Verify the valid ID is returned unchanged (generator not used)
        assert result == valid_id
        assert result != "should-not-be-used"

    def test_double_prefix_prevention(self):
        """Verify _new_trace_id prevents double req_ prefix.
        
        This tests the fix where a generated ID starting with req_ would
        get another req_ prefix added.
        """
        def custom_generator():
            return "req_already_prefixed"
        
        result = _new_trace_id(generator=custom_generator)
        
        # Should not have double prefix
        assert result == "req_already_prefixed"
        assert not result.startswith("req_req_")

    def test_trace_id_truncation_respects_max_length(self):
        """Verify trace ID truncation respects MAX_TRACE_ID_LENGTH."""
        # Create a very long trace ID
        long_id = "a" * 200
        result = sanitize_trace_id(long_id)
        
        # Verify it's truncated to max length
        from value_fabric.shared.observability.trace_context import MAX_TRACE_ID_LENGTH
        assert len(result) <= MAX_TRACE_ID_LENGTH
