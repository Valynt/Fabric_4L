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
    NotFoundError,
    RateLimitError,
    ServiceUnavailableError,
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
from ..middleware import MAX_REQUEST_ID_LENGTH, RequestIDMiddleware, get_request_id
from ..models import ErrorCode, ErrorResponse, ErrorEnvelope, ErrorDetail
from value_fabric.shared.models.typed_dict import TypedDictModel


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
        assert len(resp.headers["X-Request-ID"]) <= MAX_REQUEST_ID_LENGTH

    def test_custom_generator(self):
        client = TestClient(self._make_app(generator=lambda: "custom-id"))
        resp = client.get("/test")
        assert resp.headers["X-Request-ID"] == "custom-id"


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

        client = TestClient(app)
        response = client.get('/crash')
        body = response.json()
        assert response.status_code == 500
        assert 'abc123' not in body['error']['message']
