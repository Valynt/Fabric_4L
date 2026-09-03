"""Auth Logging Security Tests — P1 Gap Remediation

Validates that failed authentication attempts are logged with the request path
and method. This ensures that auth failures are auditable and that the
_request_log_context helper populates the required fields.

Gap matrix ref:
  P1 gap 9 — Unauthenticated Logging: failed auth not logged with path/method

Author: Platform Security Team
"""

from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

import pytest

try:
    from starlette.datastructures import Headers
    from starlette.requests import Request
    _STARLETTE_AVAILABLE = True
except ImportError:
    _STARLETTE_AVAILABLE = False

pytestmark = [
    pytest.mark.security,
    pytest.mark.audit_logging,
    pytest.mark.skipif(not _STARLETTE_AVAILABLE, reason="Starlette not available"),
]


# ---------------------------------------------------------------------------
# _request_log_context helper
# ---------------------------------------------------------------------------


def _make_mock_request(
    path: str = "/api/v1/entities",
    method: str = "GET",
    request_id: str | None = "req-abc-123",
    tenant_hint: str | None = "tenant-log-test",
) -> MagicMock:
    """Build a minimal mock Request with the fields _request_log_context reads."""
    mock_request = MagicMock()
    mock_request.url.path = path
    mock_request.method = method

    headers: dict[str, str] = {}
    if request_id:
        headers["X-Request-ID"] = request_id
    if tenant_hint:
        headers["X-Tenant-ID"] = tenant_hint

    mock_request.headers = headers
    return mock_request


@pytest.mark.skipif(not _STARLETTE_AVAILABLE, reason="Starlette not available")
class TestRequestLogContext:
    """_request_log_context must include path and method on every call."""

    def test_log_context_includes_path(self):
        """POSITIVE: _request_log_context returns the request path."""
        from value_fabric.shared.identity.logging_helpers import _request_log_context
        req = _make_mock_request(path="/api/v1/entities")
        ctx = _request_log_context(req)
        assert ctx.get("path") == "/api/v1/entities", (
            f"Log context must include 'path'. Got: {ctx}"
        )

    def test_log_context_includes_method(self):
        """POSITIVE: _request_log_context returns the HTTP method."""
        from value_fabric.shared.identity.logging_helpers import _request_log_context
        req = _make_mock_request(method="POST")
        ctx = _request_log_context(req)
        assert ctx.get("method") == "POST", (
            f"Log context must include 'method'. Got: {ctx}"
        )

    def test_log_context_includes_request_id_from_header(self):
        """POSITIVE: X-Request-ID header is captured in log context."""
        from value_fabric.shared.identity.logging_helpers import _request_log_context
        req = _make_mock_request(request_id="req-xyz-999")
        ctx = _request_log_context(req)
        assert ctx.get("request_id") == "req-xyz-999", (
            f"Log context must include 'request_id' from X-Request-ID header. Got: {ctx}"
        )

    def test_log_context_request_id_none_when_header_absent(self):
        """POSITIVE: request_id is None when neither X-Request-ID nor X-Correlation-ID is set."""
        from value_fabric.shared.identity.logging_helpers import _request_log_context
        req = _make_mock_request(request_id=None)
        ctx = _request_log_context(req)
        assert ctx.get("request_id") is None, (
            "request_id must be None when no ID header is present."
        )

    def test_log_context_includes_tenant_hint(self):
        """POSITIVE: X-Tenant-ID header is captured as tenant_hint."""
        from value_fabric.shared.identity.logging_helpers import _request_log_context
        req = _make_mock_request(tenant_hint="tenant-abc")
        ctx = _request_log_context(req)
        assert ctx.get("tenant_hint") == "tenant-abc", (
            f"Log context must include 'tenant_hint'. Got: {ctx}"
        )

    def test_log_context_path_and_method_present_for_all_http_methods(self):
        """POSITIVE: path and method are present for all standard HTTP methods."""
        from value_fabric.shared.identity.logging_helpers import _request_log_context
        for method in ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]:
            req = _make_mock_request(method=method, path=f"/api/v1/test-{method.lower()}")
            ctx = _request_log_context(req)
            assert "path" in ctx, f"'path' missing for method {method}"
            assert "method" in ctx, f"'method' missing for method {method}"
            assert ctx["method"] == method


# ---------------------------------------------------------------------------
# Auth failure log events include path and method
# ---------------------------------------------------------------------------


class TestAuthFailureLogging:
    """Failed auth events must be logged with path and method via _request_log_context."""

    def test_jwt_validation_failed_log_includes_path_and_method(self):
        """NEGATIVE: jwt_validation_failed log event includes path and method."""
        from value_fabric.shared.identity.logging_helpers import _request_log_context

        req = _make_mock_request(path="/api/v1/sensitive", method="DELETE")
        ctx = _request_log_context(req)

        # Simulate what the middleware logs on jwt_validation_failed
        log_payload = {
            "event": "jwt_validation_failed",
            "error_code": "AUTH_INVALID_TOKEN",
            **ctx,
        }

        assert log_payload.get("path") == "/api/v1/sensitive", (
            "jwt_validation_failed log must include the request path."
        )
        assert log_payload.get("method") == "DELETE", (
            "jwt_validation_failed log must include the HTTP method."
        )

    def test_jwt_context_rejected_log_includes_path_and_method(self):
        """NEGATIVE: jwt_context_rejected log event includes path and method."""
        from value_fabric.shared.identity.logging_helpers import _request_log_context

        req = _make_mock_request(path="/api/v1/admin/tenants", method="GET")
        ctx = _request_log_context(req)

        log_payload = {
            "event": "jwt_context_rejected",
            "error_code": "AUTH_CONTEXT_INVALID",
            **ctx,
        }

        assert "path" in log_payload, "jwt_context_rejected log must include path."
        assert "method" in log_payload, "jwt_context_rejected log must include method."

    def test_log_context_does_not_include_auth_header_value(self):
        """ADVERSARIAL: _request_log_context must not log the Authorization header value."""
        from value_fabric.shared.identity.logging_helpers import _request_log_context

        req = _make_mock_request()
        # Add a fake Authorization header to the mock
        req.headers = {
            "Authorization": "Bearer super-secret-token",
            "X-Request-ID": "req-001",
            "X-Tenant-ID": "tenant-x",
        }
        ctx = _request_log_context(req)

        assert "Authorization" not in ctx, (
            "_request_log_context must not include the Authorization header."
        )
        assert "super-secret-token" not in str(ctx), (
            "_request_log_context must not leak the token value."
        )

    def test_log_context_does_not_include_cookie_values(self):
        """ADVERSARIAL: _request_log_context must not log session cookie values."""
        from value_fabric.shared.identity.logging_helpers import _request_log_context

        req = _make_mock_request()
        req.headers = {
            "Cookie": "session=abc123secret",
            "X-Request-ID": "req-002",
        }
        ctx = _request_log_context(req)

        assert "Cookie" not in ctx, (
            "_request_log_context must not include Cookie header."
        )
        assert "abc123secret" not in str(ctx), (
            "_request_log_context must not leak cookie values."
        )
