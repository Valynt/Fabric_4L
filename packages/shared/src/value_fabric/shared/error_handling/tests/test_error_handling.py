"""Tests for error handling exceptions, models, handlers and middleware."""

import os
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI, HTTPException, Request
from fastapi.testclient import TestClient

from ..exceptions import (
    AuthenticationError,
    AuthorizationError,
    BadRequestError,
    ConflictError,
    NotFoundError,
    RateLimitError,
    ServiceUnavailableError,
    TenantIsolationError,
    ValidationError,
    ValueFabricException,
)
from ..handlers import (
    _sanitize_trace_id,
    canonical_error_response_schema,
    is_production,
    register_exception_handlers,
    sanitize_error_details,
)
from ..sanitizer import sanitize_error_message
from ..middleware import RequestIDMiddleware, get_request_id
from ..models import ErrorCode, ErrorResponse, ErrorEnvelope, ErrorDetail
from starlette.middleware.base import BaseHTTPMiddleware
from value_fabric.shared.models.typed_dict import TypedDictModel
from value_fabric.shared.observability.request_context import logging_context_dict


class _FakeTrustedAuthMiddleware(BaseHTTPMiddleware):
    """Test double for the production auth layer.

    RequestIDMiddleware reads tenant context from ``request.state.tenant_id``
    — populated by trusted authentication middleware — and deliberately never
    from client-controlled headers. Added after RequestIDMiddleware so it
    runs first (Starlette applies later-added middleware outermost).
    """

    def __init__(self, app, tenant_id: str):
        super().__init__(app)
        self._tenant_id = tenant_id

    async def dispatch(self, request, call_next):
        request.state.tenant_id = self._tenant_id
        return await call_next(request)


class TestRequestIDMiddleware_test_endpointResult(TypedDictModel):
    trace_id: Any


# ═══════════════════════════════════════════════════════════════════════════
# Exception classes
# ═══════════════════════════════════════════════════════════════════════════


class TestValueFabricException:
    def test_default_attributes(self):
        exc = ValueFabricException("something broke")
        assert exc.message == "something broke"
        assert exc.error_code == ErrorCode.INTERNAL_ERROR
        assert exc.status_code == 500
        assert exc.details == {}

    def test_custom_attributes(self):
        exc = ValueFabricException(
            "bad input",
            error_code=ErrorCode.VALIDATION_ERROR,
            status_code=422,
            details={"field": "name"},
        )
        assert exc.error_code == ErrorCode.VALIDATION_ERROR
        assert exc.status_code == 422
        assert exc.details == {"field": "name"}

    def test_to_dict_with_details(self):
        exc = ValueFabricException("err", details={"key": "val"})
        d = exc.to_dict(include_details=True)
        assert d["message"] == "err"
        assert d["details"] == {"key": "val"}

    def test_to_dict_without_details(self):
        exc = ValueFabricException("err", details={"key": "val"})
        d = exc.to_dict(include_details=False)
        assert "details" not in d


class TestExceptionSubclasses:
    def test_authentication_error(self):
        exc = AuthenticationError()
        assert exc.status_code == 401
        assert exc.error_code == ErrorCode.AUTHENTICATION_ERROR

    def test_authorization_error(self):
        exc = AuthorizationError()
        assert exc.status_code == 403
        assert exc.error_code == ErrorCode.AUTHORIZATION_ERROR

    def test_tenant_isolation_error(self):
        exc = TenantIsolationError()
        assert exc.status_code == 403
        assert exc.error_code == ErrorCode.TENANT_ISOLATION_ERROR

    def test_not_found_error_default(self):
        exc = NotFoundError()
        assert exc.status_code == 404
        assert exc.message == "Resource not found"

    def test_not_found_error_with_id(self):
        exc = NotFoundError(resource_type="User", resource_id="42")
        assert "42" in exc.message
        assert exc.details["resource_id"] == "42"
        assert exc.details["resource_type"] == "User"

    def test_not_found_error_custom_message(self):
        exc = NotFoundError(message="custom not found")
        assert exc.message == "custom not found"

    def test_validation_error(self):
        exc = ValidationError(field="email")
        assert exc.status_code == 422
        assert exc.details["field"] == "email"

    def test_rate_limit_error(self):
        exc = RateLimitError(retry_after=60)
        assert exc.status_code == 429
        assert exc.details["retry_after_seconds"] == 60

    def test_service_unavailable_error(self):
        exc = ServiceUnavailableError(service="Neo4j")
        assert exc.status_code == 503
        assert exc.details["service"] == "Neo4j"


# ═══════════════════════════════════════════════════════════════════════════
# ErrorCode / ErrorResponse models
# ═══════════════════════════════════════════════════════════════════════════


class TestErrorCode:
    def test_is_string_enum(self):
        assert isinstance(ErrorCode.NOT_FOUND, str)
        assert ErrorCode.NOT_FOUND == "NOT_FOUND"

    def test_all_codes_unique(self):
        values = [e.value for e in ErrorCode]
        assert len(values) == len(set(values))


class TestErrorResponse:
    def test_creation(self):
        resp = ErrorResponse(
            code=ErrorCode.NOT_FOUND,
            message="Not found",
            trace_id="req_abc",
        )
        assert resp.code == ErrorCode.NOT_FOUND
        assert resp.message == "Not found"
        assert resp.trace_id == "req_abc"
        assert resp.details is None

    def test_json_serialization(self):
        resp = ErrorResponse(
            code=ErrorCode.INTERNAL_ERROR,
            message="Oops",
            trace_id="req_xyz",
            details={"info": "test"},
        )
        d = resp.model_dump()
        assert d["code"] == "INTERNAL_ERROR"
        assert d["details"] == {"info": "test"}


class TestErrorDetail:
    def test_creation(self):
        detail = ErrorDetail(
            code=ErrorCode.NOT_FOUND,
            message="Not found",
            request_id="req_abc",
        )
        assert detail.code == ErrorCode.NOT_FOUND
        assert detail.message == "Not found"
        assert detail.request_id == "req_abc"
        assert detail.details is None

    def test_json_serialization(self):
        detail = ErrorDetail(
            code=ErrorCode.INTERNAL_ERROR,
            message="Oops",
            request_id="req_xyz",
            details={"info": "test"},
        )
        d = detail.model_dump()
        assert d["code"] == "INTERNAL_ERROR"
        assert d["request_id"] == "req_xyz"
        assert d["details"] == {"info": "test"}


class TestErrorEnvelope:
    def test_creation(self):
        envelope = ErrorEnvelope(
            error=ErrorDetail(
                code=ErrorCode.NOT_FOUND,
                message="Not found",
                request_id="req_abc",
            )
        )
        assert envelope.error.code == ErrorCode.NOT_FOUND
        assert envelope.error.message == "Not found"
        assert envelope.error.request_id == "req_abc"

    def test_json_serialization(self):
        envelope = ErrorEnvelope(
            error=ErrorDetail(
                code=ErrorCode.INTERNAL_ERROR,
                message="Oops",
                request_id="req_xyz",
                details={"info": "test"},
            )
        )
        d = envelope.model_dump()
        assert "error" in d
        assert d["error"]["code"] == "INTERNAL_ERROR"
        assert d["error"]["request_id"] == "req_xyz"
        assert d["error"]["details"] == {"info": "test"}

    def test_envelope_structure(self):
        """Verify envelope has required nested structure."""
        envelope = ErrorEnvelope(
            error=ErrorDetail(
                code=ErrorCode.VALIDATION_ERROR,
                message="Invalid input",
                request_id="req_123",
            )
        )
        d = envelope.model_dump()
        assert set(d.keys()) == {"error"}
        assert set(d["error"].keys()) == {"code", "message", "request_id", "details"}


# ═══════════════════════════════════════════════════════════════════════════
# Handlers
# ═══════════════════════════════════════════════════════════════════════════


class TestIsProduction:
    @patch.dict(os.environ, {"ENVIRONMENT": "production"})
    def test_production(self):
        assert is_production() is True

    @patch.dict(os.environ, {"ENVIRONMENT": "staging"})
    def test_staging(self):
        assert is_production() is True

    @patch.dict(os.environ, {"ENVIRONMENT": "development"})
    def test_development(self):
        assert is_production() is False

    @patch.dict(os.environ, {}, clear=True)
    def test_default_not_production(self):
        os.environ.pop("ENVIRONMENT", None)
        os.environ.pop("ENV", None)
        os.environ.pop("APP_ENV", None)
        assert is_production() is False


class TestSanitizeErrorDetails:
    def test_none_input(self):
        assert sanitize_error_details(None) is None

    def test_removes_sensitive_keys(self):
        details = {"password": "secret", "user": "alice"}
        result = sanitize_error_details(details)
        assert "password" not in result
        assert result["user"] == "alice"

    def test_removes_key_with_sensitive_substring(self):
        details = {"auth_token": "xyz", "display_name": "Bob"}
        result = sanitize_error_details(details)
        assert "auth_token" not in result
        assert result["display_name"] == "Bob"

    def test_truncates_long_values(self):
        details = {"message": "x" * 2000}
        result = sanitize_error_details(details)
        assert len(result["message"]) < 2000
        assert result["message"].endswith("... [truncated]")

    def test_returns_none_for_empty_after_sanitize(self):
        details = {"password": "secret", "token": "xyz"}
        result = sanitize_error_details(details)
        assert result is None


class TestSanitizeErrorMessage:
    def test_redacts_tenant_id(self):
        assert sanitize_error_message("tenant_id=tenant_abc123") == "tenant_id=<redacted>"

    def test_redacts_subscription_id(self):
        assert (
            sanitize_error_message("subscription_id=sub_secret_123")
            == "subscription_id=<redacted>"
        )

    def test_redacts_customer_id(self):
        assert sanitize_error_message("customer_id=cus_123") == "customer_id=<redacted>"

    def test_preserves_non_identifier_text(self):
        raw = "No active subscription found for tenant_id=tenant_abc subscription_id=sub_secret"
        sanitized = sanitize_error_message(raw)
        assert "No active subscription found" in sanitized
        assert "tenant_abc" not in sanitized
        assert "sub_secret" not in sanitized
        assert "tenant_id=<redacted>" in sanitized
        assert "subscription_id=<redacted>" in sanitized

    def test_no_change_for_safe_message(self):
        assert sanitize_error_message("Invalid plan") == "Invalid plan"


class TestSanitizeTraceId:
    def test_valid_id_passes_through(self):
        assert _sanitize_trace_id("req_abc123") == "req_abc123"

    def test_strips_invalid_characters(self):
        result = _sanitize_trace_id("req<script>alert(1)</script>")
        assert "<" not in result
        assert ">" not in result

    def test_truncates_long_id(self):
        long_id = "a" * 100
        result = _sanitize_trace_id(long_id)
        assert len(result) <= 64

    def test_empty_generates_new(self):
        result = _sanitize_trace_id("")
        assert result.startswith("req_")


# ═══════════════════════════════════════════════════════════════════════════
# Middleware
# ═══════════════════════════════════════════════════════════════════════════


class TestRequestIDMiddleware:
    """Tests for RequestIDMiddleware using FastAPI TestClient."""

    def _make_app(self, **kwargs) -> FastAPI:
        app = FastAPI()
        app.add_middleware(RequestIDMiddleware, **kwargs)

        @app.get("/test")
        async def test_endpoint(request: Request):
            return TestRequestIDMiddleware_test_endpointResult.model_validate({"trace_id": getattr(request.state, "trace_id", None)})

        return app

    def test_generates_request_id_when_missing(self):
        client = TestClient(self._make_app())
        resp = client.get("/test")
        assert resp.status_code == 200
        assert "X-Request-ID" in resp.headers
        assert resp.headers["X-Request-ID"].startswith("req_")

    def test_preserves_valid_request_id(self):
        client = TestClient(self._make_app())
        resp = client.get("/test", headers={"X-Request-ID": "my-custom-id"})
        assert resp.headers["X-Request-ID"] == "my-custom-id"

    def test_rejects_invalid_characters(self):
        client = TestClient(self._make_app())
        resp = client.get("/test", headers={"X-Request-ID": "<script>"})
        # Should generate a new ID instead
        assert "<" not in resp.headers["X-Request-ID"]
        assert resp.headers["X-Request-ID"].startswith("req_")

    def test_truncates_long_id(self):
        client = TestClient(self._make_app())
        long_id = "a" * 200
        resp = client.get("/test", headers={"X-Request-ID": long_id})
        # ID should be sanitized/truncated by the trace context module
        assert len(resp.headers["X-Request-ID"]) <= 200

    def test_custom_generator(self):
        # Contract: generator output is normalized to the canonical trace-ID
        # shape — `req_` prefix is added unless already present
        # (test_trace_id_sanitization_regression.py governs this).
        client = TestClient(self._make_app(generator=lambda: "custom-id"))
        resp = client.get("/test")
        assert resp.headers["X-Request-ID"] == "req_custom-id"

    def test_emits_structured_access_log(self, caplog):
        app = self._make_app()
        # Tenant context comes from trusted auth state, never from headers:
        # the spoofed X-Tenant-ID below must NOT win.
        app.add_middleware(_FakeTrustedAuthMiddleware, tenant_id="tenant-123")
        with caplog.at_level("INFO", logger="fabric.access"):
            client = TestClient(app)
            resp = client.get("/test", headers={"X-Tenant-ID": "tenant-spoof"})
        assert resp.status_code == 200
        access_records = [r for r in caplog.records if r.name == "fabric.access"]
        assert len(access_records) == 1
        record = access_records[0]
        assert record.message == "request"
        assert record.request_id.startswith("req_")
        assert record.tenant_id == "tenant-123"
        assert record.route == "/test"
        assert record.method == "GET"
        assert record.status_code == 200
        assert isinstance(record.latency_ms, float)


class TestGetRequestId:
    def test_from_state(self):
        request = MagicMock()
        request.state.trace_id = "from-state"
        assert get_request_id(request) == "from-state"

    def test_from_header_fallback(self):
        request = MagicMock()
        request.state = MagicMock(spec=[])  # no trace_id attribute
        request.headers = {"X-Request-ID": "from-header"}
        assert get_request_id(request) == "from-header"

    def test_unknown_fallback(self):
        request = MagicMock()
        request.state = MagicMock(spec=[])
        request.headers = {}
        assert get_request_id(request) == "unknown"


# ═══════════════════════════════════════════════════════════════════════════
# Integration: exception handlers registered on a real FastAPI app
# ═══════════════════════════════════════════════════════════════════════════


class TestRegisteredHandlers:
    """End-to-end tests using the full handler registration."""

    @pytest.fixture
    def app(self):
        app = FastAPI()
        app.add_middleware(RequestIDMiddleware)
        register_exception_handlers(app)

        @app.get("/vf-error")
        async def vf_error():
            raise NotFoundError(resource_type="Widget", resource_id="99")

        @app.get("/http-error")
        async def http_error():
            raise HTTPException(status_code=403, detail="Forbidden")

        @app.get("/unhandled")
        async def unhandled():
            raise RuntimeError("boom")

        @app.get("/needs-int")
        async def needs_int(limit: int):
            return {"limit": limit}

        return app

    @pytest.fixture
    def client(self, app):
        return TestClient(app, raise_server_exceptions=False)

    def test_vf_exception_handler(self, client):
        resp = client.get("/vf-error")
        assert resp.status_code == 404
        body = resp.json()
        # Verify envelope structure
        assert "error" in body
        assert body["error"]["code"] == "NOT_FOUND"
        assert "Widget" in body["error"]["message"]
        assert "request_id" in body["error"]
        assert "X-Request-ID" in resp.headers

    def test_http_exception_handler(self, client):
        resp = client.get("/http-error")
        assert resp.status_code == 403
        body = resp.json()
        # Verify envelope structure
        assert "error" in body
        assert body["error"]["code"] == "AUTHORIZATION_ERROR"
        assert "request_id" in body["error"]

    def test_global_exception_handler(self, client):
        resp = client.get("/unhandled")
        assert resp.status_code == 500
        body = resp.json()
        # Verify envelope structure
        assert "error" in body
        assert body["error"]["code"] == "INTERNAL_ERROR"
        assert "request_id" in body["error"]

    def test_openapi_uses_canonical_error_envelope(self, app):
        schema = app.openapi()
        error_schema = schema["components"]["schemas"]["ErrorEnvelope"]
        assert error_schema == canonical_error_response_schema()
        assert error_schema["required"] == ["error"]
        assert "error" in error_schema["properties"]
        assert schema["components"]["schemas"]["ErrorResponse"]["description"].startswith(
            "Deprecated compatibility alias"
        )
        assert schema["components"]["schemas"]["HTTPValidationError"]["description"].startswith(
            "Deprecated compatibility alias"
        )

    def test_request_validation_error_uses_canonical_envelope(self, client):
        resp = client.get("/needs-int", params={"limit": "not-int"})
        assert resp.status_code == 422
        body = resp.json()
        # Verify envelope structure
        assert "error" in body
        assert set(body["error"].keys()).issuperset({"code", "message", "request_id"})
        assert "detail" not in body
        assert body["error"]["code"] == "VALIDATION_ERROR"

    def test_raw_exception_string_not_leaked(self, client):
        """Verify raw exception strings are not exposed in error responses."""
        resp = client.get("/unhandled")
        assert resp.status_code == 500
        body = resp.json()
        # In production mode, should not contain raw exception string
        # In dev mode, may contain it but should be in details, not message
        assert "error" in body
        assert body["error"]["code"] == "INTERNAL_ERROR"
        # The message should be sanitized, not the raw "boom" string
        if is_production():
            assert "boom" not in body["error"]["message"]

    def test_request_id_present_in_all_errors(self, client):
        """Verify request_id appears in every error response."""
        # Test different error types
        endpoints = ["/vf-error", "/http-error", "/unhandled"]
        for endpoint in endpoints:
            resp = client.get(endpoint)
            body = resp.json()
            assert "error" in body
            assert "request_id" in body["error"]
            assert isinstance(body["error"]["request_id"], str)
            assert len(body["error"]["request_id"]) > 0

    def test_success_response_not_wrapped(self, client):
        """Verify success responses are not wrapped in envelope."""
        resp = client.get("/needs-int", params={"limit": "10"})
        assert resp.status_code == 200
        body = resp.json()
        # Success response should not have envelope structure
        assert "error" not in body
        assert body == {"limit": 10}

class TestSanitizedPublicErrors:
    def test_http_exception_does_not_leak_raw_detail(self):
        app = FastAPI()
        register_exception_handlers(app)

        @app.get('/boom')
        def boom():
            raise HTTPException(status_code=500, detail='db password=secret')

        client = TestClient(app)
        response = client.get('/boom')
        body = response.json()
        assert response.status_code == 500
        assert body['error']['message'] == 'Request failed'
        assert 'password' not in body['error']['message']

    def test_unhandled_exception_response_is_sanitized(self):
        app = FastAPI()
        register_exception_handlers(app)

        @app.get('/crash')
        def crash():
            raise RuntimeError('token=abc123 leaked')

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get('/crash')
        body = response.json()
        assert response.status_code == 500
        assert 'abc123' not in body['error']['message']

    def test_value_fabric_exception_redacts_identifiers_from_message(self):
        """Tenant/subscription/customer IDs must not leak in public error envelopes."""
        app = FastAPI()
        register_exception_handlers(app)

        @app.get('/billing-cancel')
        def billing_cancel():
            raise BadRequestError(
                message="No active subscription found for tenant_id=tenant_abc123 subscription_id=sub_secret_123"
            )

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get('/billing-cancel')
        body = response.json()
        assert response.status_code == 400
        assert 'tenant_abc123' not in body['error']['message']
        assert 'sub_secret_123' not in body['error']['message']
        assert 'tenant_id=<redacted>' in body['error']['message']
        assert 'subscription_id=<redacted>' in body['error']['message']
        assert 'No active subscription found' in body['error']['message']


class TestCorrelationContextMiddleware:
    def test_generates_correlation_id_when_missing(self):
        app = FastAPI()
        app.add_middleware(RequestIDMiddleware)

        @app.get("/context")
        def context(request: Request):
            return {
                "request_id": getattr(request.state, "request_id", None),
                "trace_id": getattr(request.state, "trace_id", None),
                "correlation_id": getattr(request.state, "correlation_id", None),
            }

        client = TestClient(app)
        response = client.get("/context")
        payload = response.json()
        assert response.status_code == 200
        assert payload["request_id"]
        assert payload["trace_id"] == payload["request_id"]
        assert payload["correlation_id"] == payload["request_id"]
        assert response.headers["X-Correlation-ID"] == payload["request_id"]

    def test_propagates_provided_correlation_id(self):
        app = FastAPI()
        app.add_middleware(RequestIDMiddleware)

        @app.get("/context")
        def context(request: Request):
            return {"correlation_id": getattr(request.state, "correlation_id", None)}

        client = TestClient(app)
        response = client.get("/context", headers={"X-Correlation-ID": "corr-shared-123"})
        assert response.status_code == 200
        assert response.json()["correlation_id"] == "corr-shared-123"

    def test_logging_context_available_during_request(self):
        app = FastAPI()
        app.add_middleware(RequestIDMiddleware)

        @app.get("/log-context")
        def context():
            ctx = logging_context_dict()
            return {
                "request_id": ctx.get("request_id"),
                "correlation_id": ctx.get("correlation_id"),
                "route": ctx.get("route"),
                "method": ctx.get("method"),
            }

        client = TestClient(app)
        response = client.get("/log-context", headers={"X-Request-ID": "req-shared-ctx"})
        payload = response.json()
        assert response.status_code == 200
        assert payload["request_id"] == "req-shared-ctx"
        assert payload["correlation_id"] == "req-shared-ctx"
        assert payload["route"] == "/log-context"
        assert payload["method"] == "GET"


# ═══════════════════════════════════════════════════════════════════════════
# ErrorEnvelope Contract Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestErrorEnvelopeContract:
    """Contract tests verifying each canonical exception renders ErrorEnvelope correctly."""

    @pytest.fixture
    def app(self):
        app = FastAPI()
        app.add_middleware(RequestIDMiddleware)
        register_exception_handlers(app)

        @app.get("/auth-error")
        async def auth_error():
            raise AuthenticationError(message="Invalid credentials")

        @app.get("/authz-error")
        async def authz_error():
            raise AuthorizationError(message="Access denied")

        @app.get("/tenant-error")
        async def tenant_error():
            raise TenantIsolationError(message="Cross-tenant access blocked")

        @app.get("/not-found")
        async def not_found():
            raise NotFoundError(resource_type="User", resource_id="123")

        @app.get("/validation-error")
        async def validation_error():
            raise ValidationError(message="Invalid email", field="email")

        @app.get("/bad-request")
        async def bad_request():
            raise BadRequestError(message="Malformed JSON")

        @app.get("/conflict-error")
        async def conflict_error():
            raise ConflictError(message="Resource already exists")

        @app.get("/rate-limit-error")
        async def rate_limit_error():
            raise RateLimitError(message="Too many requests", retry_after=60)

        @app.get("/service-unavailable-error")
        async def service_unavailable_error():
            raise ServiceUnavailableError(message="Database down", service="PostgreSQL")

        return app

    @pytest.fixture
    def client(self, app):
        return TestClient(app, raise_server_exceptions=False)

    def _assert_envelope_contract(
        self, response, expected_status_code, expected_error_code, expected_message_contains=None
    ):
        """Helper to assert ErrorEnvelope contract for any exception."""
        assert response.status_code == expected_status_code
        body = response.json()

        # Envelope structure
        assert "error" in body
        assert set(body["error"].keys()) == {"code", "message", "request_id", "details"}

        # HTTP status code correctness
        assert response.status_code == expected_status_code

        # Stable error code value
        assert body["error"]["code"] == expected_error_code
        assert isinstance(body["error"]["code"], str)

        # Message shape and content
        assert isinstance(body["error"]["message"], str)
        assert len(body["error"]["message"]) > 0
        if expected_message_contains:
            assert expected_message_contains in body["error"]["message"]

        # Request ID presence
        assert "request_id" in body["error"]
        assert isinstance(body["error"]["request_id"], str)
        assert len(body["error"]["request_id"]) > 0
        assert "X-Request-ID" in response.headers
        assert response.headers["X-Request-ID"] == body["error"]["request_id"]

        # Details shape (when applicable)
        assert "details" in body["error"]
        # details can be None or a dict
        if body["error"]["details"] is not None:
            assert isinstance(body["error"]["details"], dict)

        # No raw exception leakage
        # Check that response doesn't contain exception class names or stack traces
        body_str = str(body)
        assert "Traceback" not in body_str
        assert "Exception" not in body_str or body_str.count("Exception") <= 1  # Allow in message only

        # No secrets/tokens/DSNs in response
        # Check for common secret patterns
        assert "password" not in body_str.lower()
        assert "token" not in body_str.lower() or "retry_after" in body_str  # Allow retry_after
        assert "secret" not in body_str.lower()
        assert "dsn" not in body_str.lower()
        assert "postgresql://" not in body_str.lower()
        assert "mongodb://" not in body_str.lower()

    def test_authentication_error_envelope_contract(self, client):
        """AuthenticationError renders correct ErrorEnvelope."""
        resp = client.get("/auth-error")
        self._assert_envelope_contract(
            resp,
            expected_status_code=401,
            expected_error_code="AUTHENTICATION_ERROR",
            expected_message_contains="Invalid credentials",
        )

    def test_authorization_error_envelope_contract(self, client):
        """AuthorizationError renders correct ErrorEnvelope."""
        resp = client.get("/authz-error")
        self._assert_envelope_contract(
            resp,
            expected_status_code=403,
            expected_error_code="AUTHORIZATION_ERROR",
            expected_message_contains="Access denied",
        )

    def test_tenant_isolation_error_envelope_contract(self, client):
        """TenantIsolationError renders correct ErrorEnvelope."""
        resp = client.get("/tenant-error")
        self._assert_envelope_contract(
            resp,
            expected_status_code=403,
            expected_error_code="TENANT_ISOLATION_ERROR",
            expected_message_contains="Cross-tenant access blocked",
        )

    def test_not_found_error_envelope_contract(self, client):
        """NotFoundError renders correct ErrorEnvelope with details."""
        resp = client.get("/not-found")
        self._assert_envelope_contract(
            resp,
            expected_status_code=404,
            expected_error_code="NOT_FOUND",
            expected_message_contains="User",
        )
        body = resp.json()
        # Verify details shape
        assert body["error"]["details"] is not None
        assert body["error"]["details"]["resource_type"] == "User"
        assert body["error"]["details"]["resource_id"] == "123"

    def test_validation_error_envelope_contract(self, client):
        """ValidationError renders correct ErrorEnvelope with details."""
        resp = client.get("/validation-error")
        self._assert_envelope_contract(
            resp,
            expected_status_code=422,
            expected_error_code="VALIDATION_ERROR",
            expected_message_contains="Invalid email",
        )
        body = resp.json()
        # Verify details shape
        assert body["error"]["details"] is not None
        assert body["error"]["details"]["field"] == "email"

    def test_bad_request_error_envelope_contract(self, client):
        """BadRequestError renders correct ErrorEnvelope."""
        resp = client.get("/bad-request")
        self._assert_envelope_contract(
            resp,
            expected_status_code=400,
            expected_error_code="INVALID_PARAMETER",
            expected_message_contains="Malformed JSON",
        )

    def test_conflict_error_envelope_contract(self, client):
        """ConflictError renders correct ErrorEnvelope."""
        resp = client.get("/conflict-error")
        self._assert_envelope_contract(
            resp,
            expected_status_code=409,
            expected_error_code="CONFLICT",
            expected_message_contains="Resource already exists",
        )

    def test_rate_limit_error_envelope_contract(self, client):
        """RateLimitError renders correct ErrorEnvelope with retry_after."""
        resp = client.get("/rate-limit-error")
        self._assert_envelope_contract(
            resp,
            expected_status_code=429,
            expected_error_code="RATE_LIMIT_EXCEEDED",
            expected_message_contains="Too many requests",
        )
        body = resp.json()
        # Verify details shape with retry_after
        assert body["error"]["details"] is not None
        assert body["error"]["details"]["retry_after_seconds"] == 60

    def test_service_unavailable_error_envelope_contract(self, client):
        """ServiceUnavailableError renders correct ErrorEnvelope with service."""
        resp = client.get("/service-unavailable-error")
        self._assert_envelope_contract(
            resp,
            expected_status_code=503,
            expected_error_code="SERVICE_UNAVAILABLE",
            expected_message_contains="Database down",
        )
        body = resp.json()
        # Verify details shape with service
        assert body["error"]["details"] is not None
        assert body["error"]["details"]["service"] == "PostgreSQL"
