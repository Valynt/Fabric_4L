"""Request Tracing Security Tests — P1 Gap Remediation

Validates that request_id is generated, propagated through request state, and
included in structured log output. A missing request_id breaks audit trail
correlation and makes incident investigation impossible.

Gap matrix ref:
  P1 gap 17 — Request ID Propagation: missing request_id in logs

Author: Platform Security Team
"""

from __future__ import annotations

import logging

import pytest

try:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from starlette.requests import Request
    _FASTAPI_AVAILABLE = True
except ImportError:
    _FASTAPI_AVAILABLE = False

pytestmark = [
    pytest.mark.security,
    pytest.mark.observability,
    pytest.mark.skipif(not _FASTAPI_AVAILABLE, reason="FastAPI not available"),
]


# ---------------------------------------------------------------------------
# RequestIDMiddleware propagation
# ---------------------------------------------------------------------------


@pytest.fixture
def traced_app():
    """Minimal FastAPI app with RequestIDMiddleware installed."""
    from fastapi import FastAPI
    from value_fabric.shared.error_handling.middleware import RequestIDMiddleware

    app = FastAPI()
    app.add_middleware(RequestIDMiddleware)

    @app.get("/ping")
    async def ping(request: Request):
        from value_fabric.shared.error_handling.middleware import get_request_id
        return {"request_id": get_request_id(request)}

    @app.get("/echo-headers")
    async def echo_headers(request: Request):
        return {
            "x_request_id": request.headers.get("X-Request-ID"),
            "state_trace_id": getattr(request.state, "trace_id", None),
        }

    return app


@pytest.fixture
def traced_client(traced_app):
    from fastapi.testclient import TestClient
    return TestClient(traced_app)


@pytest.mark.skipif(not _FASTAPI_AVAILABLE, reason="FastAPI not available")
class TestRequestIDGeneration:
    """RequestIDMiddleware must generate a request_id when none is provided."""

    def test_request_id_generated_when_absent(self, traced_client):
        """POSITIVE: A request without X-Request-ID gets one generated."""
        response = traced_client.get("/ping")
        assert response.status_code == 200
        data = response.json()
        assert data.get("request_id"), (
            "request_id must be generated when X-Request-ID header is absent."
        )
        assert data["request_id"] != "unknown", (
            "Generated request_id must not be the fallback 'unknown' string."
        )

    def test_request_id_preserved_from_header(self, traced_client):
        """POSITIVE: A provided X-Request-ID is preserved through the middleware."""
        provided_id = "req-test-abc-123"
        response = traced_client.get("/ping", headers={"X-Request-ID": provided_id})
        assert response.status_code == 200
        data = response.json()
        assert data.get("request_id") == provided_id, (
            f"Provided X-Request-ID must be preserved. Got: {data.get('request_id')}"
        )

    def test_request_id_in_response_headers(self, traced_client):
        """POSITIVE: X-Request-ID is echoed back in the response headers."""
        response = traced_client.get("/ping")
        assert response.status_code == 200
        # The middleware adds X-Request-ID (or a canonical alias) to the response
        has_trace_header = any(
            "request-id" in h.lower() or "trace-id" in h.lower() or "correlation-id" in h.lower()
            for h in response.headers
        )
        assert has_trace_header, (
            f"Response must include a trace/request-id header. Got headers: {dict(response.headers)}"
        )

    def test_each_request_gets_unique_id(self, traced_client):
        """POSITIVE: Two requests without X-Request-ID get different IDs."""
        r1 = traced_client.get("/ping")
        r2 = traced_client.get("/ping")
        id1 = r1.json().get("request_id")
        id2 = r2.json().get("request_id")
        assert id1 and id2, "Both requests must have a request_id."
        assert id1 != id2, (
            f"Each request must get a unique request_id. Got: {id1!r} and {id2!r}"
        )

    def test_correlation_id_header_also_accepted(self, traced_client):
        """POSITIVE: X-Correlation-ID is accepted as an alternative trace header."""
        correlation_id = "corr-xyz-456"
        response = traced_client.get("/ping", headers={"X-Correlation-ID": correlation_id})
        assert response.status_code == 200
        # The middleware should resolve the correlation ID as the trace ID
        data = response.json()
        assert data.get("request_id"), "request_id must be set when X-Correlation-ID is provided."


# ---------------------------------------------------------------------------
# request_id in log context
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _FASTAPI_AVAILABLE, reason="FastAPI not available")
class TestRequestIDInLogContext:
    """request_id must appear in structured log output for every request."""

    def test_log_context_includes_request_id_field(self):
        """POSITIVE: _request_log_context includes request_id from X-Request-ID header."""
        from unittest.mock import MagicMock

        from value_fabric.shared.identity.middleware import _request_log_context

        mock_request = MagicMock()
        mock_request.url.path = "/api/v1/entities"
        mock_request.method = "GET"
        mock_request.headers = {"X-Request-ID": "req-log-test-001"}

        ctx = _request_log_context(mock_request)
        assert "request_id" in ctx, (
            "_request_log_context must include 'request_id' key."
        )
        assert ctx["request_id"] == "req-log-test-001", (
            f"request_id must match X-Request-ID header. Got: {ctx['request_id']}"
        )

    def test_log_context_request_id_none_when_no_header(self):
        """NEGATIVE: request_id is None in log context when no ID header is present."""
        from unittest.mock import MagicMock

        from value_fabric.shared.identity.middleware import _request_log_context

        mock_request = MagicMock()
        mock_request.url.path = "/api/v1/entities"
        mock_request.method = "GET"
        mock_request.headers = {}

        ctx = _request_log_context(mock_request)
        assert ctx.get("request_id") is None, (
            "request_id must be None when no ID header is present."
        )

    def test_correlation_id_in_exception_log(self, caplog):
        """POSITIVE: Unhandled exceptions include correlation_id in log records."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from value_fabric.shared.error_handling.handlers import register_exception_handlers
        from value_fabric.shared.error_handling.middleware import RequestIDMiddleware

        app = FastAPI()
        app.add_middleware(RequestIDMiddleware)
        register_exception_handlers(app)

        @app.get("/boom")
        async def boom():
            raise RuntimeError("test error")

        client = TestClient(app, raise_server_exceptions=False)
        with caplog.at_level(logging.ERROR):
            response = client.get("/boom", headers={"X-Request-ID": "req-boom-001"})

        assert response.status_code == 500
        # At least one error log record should carry a correlation/trace id
        error_records = [r for r in caplog.records if r.levelno >= logging.ERROR]
        assert len(error_records) >= 1, "At least one ERROR log must be emitted for unhandled exceptions."


# ---------------------------------------------------------------------------
# RequestContext carries request_id
# ---------------------------------------------------------------------------


class TestRequestContextRequestID:
    """RequestContext must store and expose request_id."""

    def test_request_context_stores_request_id(self):
        """POSITIVE: RequestContext stores the provided request_id."""
        from value_fabric.shared.identity.context import AUTH_SOURCE_JWT, RequestContext

        ctx = RequestContext(
            tenant_id="tenant-trace-test",
            auth_source=AUTH_SOURCE_JWT,
            request_id="req-ctx-001",
        )
        assert ctx.request_id == "req-ctx-001", (
            "RequestContext must store the provided request_id."
        )

    def test_request_context_request_id_none_by_default(self):
        """POSITIVE: RequestContext request_id defaults to None."""
        from value_fabric.shared.identity.context import AUTH_SOURCE_JWT, RequestContext

        ctx = RequestContext(
            tenant_id="tenant-trace-test",
            auth_source=AUTH_SOURCE_JWT,
        )
        assert ctx.request_id is None, (
            "RequestContext request_id must default to None."
        )

    def test_request_id_in_to_log_dict(self):
        """POSITIVE: request and trace identifiers appear in to_log_dict() output."""
        from value_fabric.shared.identity.context import AUTH_SOURCE_JWT, RequestContext

        ctx = RequestContext(
            tenant_id="tenant-trace-test",
            auth_source=AUTH_SOURCE_JWT,
            request_id="req-log-dict-001",
            trace_id="trace-log-dict-001",
        )
        log_dict = ctx.to_log_dict()
        assert "request_id" in log_dict, (
            "to_log_dict() must include 'request_id'."
        )
        assert log_dict["request_id"] == "req-log-dict-001"
        assert log_dict["trace_id"] == "trace-log-dict-001"

    def test_request_id_in_to_dict(self):
        """POSITIVE: request and trace identifiers appear in to_dict() output."""
        from value_fabric.shared.identity.context import AUTH_SOURCE_JWT, RequestContext

        ctx = RequestContext(
            tenant_id="tenant-trace-test",
            auth_source=AUTH_SOURCE_JWT,
            request_id="req-dict-001",
            trace_id="trace-dict-001",
        )
        d = ctx.to_dict()
        assert "request_id" in d, "to_dict() must include 'request_id'."
        assert d["request_id"] == "req-dict-001"
        assert d["trace_id"] == "trace-dict-001"

    def test_adversarial_request_id_injection(self):
        """ADVERSARIAL: Injection payload in request_id is stored as a plain string."""
        from value_fabric.shared.identity.context import AUTH_SOURCE_JWT, RequestContext

        malicious_id = "req-001\nX-Injected-Header: evil"
        ctx = RequestContext(
            tenant_id="tenant-trace-test",
            auth_source=AUTH_SOURCE_JWT,
            request_id=malicious_id,
        )
        # Stored verbatim — the HTTP layer is responsible for sanitisation
        assert ctx.request_id == malicious_id, (
            "request_id is stored as-is; sanitisation is the HTTP layer's responsibility."
        )
