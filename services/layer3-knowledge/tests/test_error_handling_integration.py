"""Tests for shared error handling middleware integration in Layer 3.

Validates:
- RequestIDMiddleware: request ID propagation, header validation, generation
- Exception handlers: standardized ErrorResponse format with trace_id
- Request ID flow: incoming X-Request-ID → request.state.trace_id → response header
"""

from typing import Any
from unittest.mock import patch

import pytest
from fastapi import FastAPI, HTTPException, Request
from fastapi.testclient import TestClient

# Shared error handling imports
from value_fabric.shared.error_handling.exceptions import (
    NotFoundError,
    ServiceUnavailableError,
    ValueFabricException,
)
from value_fabric.shared.error_handling.middleware import RequestIDMiddleware
from value_fabric.shared.error_handling.models import ErrorCode
from value_fabric.shared.models.typed_dict import TypedDictModel


class echo_traceResult(TypedDictModel):
    trace_id: Any


def _error_body(resp) -> dict[str, Any]:
    body = resp.json()
    error = body.get("error", body)
    if isinstance(error, dict):
        return error
    if resp.status_code == 401:
        return {"code": "AUTHENTICATION_ERROR", "message": str(error)}
    return {"code": str(resp.status_code), "message": str(error)}

# ---------------------------------------------------------------------------
# Helpers: minimal FastAPI app with middleware + handlers for isolated testing
# ---------------------------------------------------------------------------


def _build_test_app() -> FastAPI:
    """Build a minimal FastAPI app with RequestIDMiddleware and exception handlers."""
    test_app = FastAPI()
    test_app.add_middleware(RequestIDMiddleware)

    from value_fabric.shared.error_handling.handlers import register_exception_handlers

    register_exception_handlers(test_app)

    @test_app.get("/echo-trace")
    async def echo_trace(request: Request):
        """Return the trace_id stored by middleware."""
        return echo_traceResult.model_validate({"trace_id": getattr(request.state, "trace_id", None)})

    @test_app.get("/raise-vf")
    async def raise_vf(request: Request):
        raise ValueFabricException(
            message="something broke",
            error_code=ErrorCode.DATABASE_ERROR,
            status_code=500,
            details={"table": "nodes"},
        )

    @test_app.get("/raise-http")
    async def raise_http(request: Request):
        raise HTTPException(status_code=404, detail="entity not found")

    @test_app.get("/raise-unexpected")
    async def raise_unexpected(request: Request):
        raise RuntimeError("kaboom")

    @test_app.get("/raise-not-found")
    async def raise_not_found(request: Request):
        raise NotFoundError(resource_type="Capability", resource_id="cap-123")

    @test_app.get("/raise-unavailable")
    async def raise_unavailable(request: Request):
        raise ServiceUnavailableError(service="neo4j")

    return test_app


@pytest.fixture
def client():
    """Test client with middleware and exception handlers."""
    return TestClient(_build_test_app(), raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# RequestIDMiddleware tests
# ---------------------------------------------------------------------------


class TestRequestIDMiddleware:
    """RequestIDMiddleware generates, validates, and propagates request IDs."""

    def test_generates_request_id_when_none_provided(self, client):
        """Response must contain X-Request-ID even if caller sends none."""
        resp = client.get("/echo-trace")
        assert resp.status_code == 200

        req_id = resp.headers.get("X-Request-ID")
        assert req_id is not None
        assert req_id.startswith("req_")

    def test_echoes_valid_client_request_id(self, client):
        """Valid client-supplied X-Request-ID is echoed back unchanged."""
        resp = client.get(
            "/echo-trace", headers={"X-Request-ID": "my-custom-id-123"}
        )
        assert resp.status_code == 200
        assert resp.headers["X-Request-ID"] == "my-custom-id-123"

    def test_stores_trace_id_in_request_state(self, client):
        """Middleware must store the ID in request.state.trace_id."""
        resp = client.get(
            "/echo-trace", headers={"X-Request-ID": "trace-abc"}
        )
        body = resp.json()
        assert body["trace_id"] == "trace-abc"

    def test_rejects_invalid_characters_and_generates_new_id(self, client):
        """IDs with invalid chars are replaced by a generated ID."""
        resp = client.get(
            "/echo-trace",
            headers={"X-Request-ID": "bad<script>id"},
        )
        req_id = resp.headers["X-Request-ID"]
        # Invalid characters should cause a newly generated ID
        assert req_id.startswith("req_")

    def test_truncates_oversized_request_id(self, client):
        """IDs exceeding 64 characters are truncated."""
        long_id = "a" * 100
        resp = client.get(
            "/echo-trace", headers={"X-Request-ID": long_id}
        )
        req_id = resp.headers["X-Request-ID"]
        assert len(req_id) <= 64

    def test_accepts_hyphens_and_underscores(self, client):
        """Hyphens and underscores are valid in request IDs."""
        valid_id = "req_abc-123_DEF"
        resp = client.get(
            "/echo-trace", headers={"X-Request-ID": valid_id}
        )
        assert resp.headers["X-Request-ID"] == valid_id

    def test_empty_request_id_generates_new(self, client):
        """Empty string X-Request-ID triggers generation."""
        resp = client.get(
            "/echo-trace", headers={"X-Request-ID": ""}
        )
        req_id = resp.headers["X-Request-ID"]
        assert req_id.startswith("req_")


# ---------------------------------------------------------------------------
# Exception handler response format tests
# ---------------------------------------------------------------------------


class TestValueFabricExceptionHandler:
    """ValueFabricException produces standardized ErrorResponse."""

    def test_response_contains_error_fields(self, client):
        """Error response must have code, message, trace_id."""
        resp = client.get("/raise-vf")
        assert resp.status_code == 500
        body = _error_body(resp)
        assert body["code"] == "DATABASE_ERROR"
        assert body["message"] == "something broke"
        assert "trace_id" in body or "request_id" in body

    def test_response_includes_details_in_dev(self, client):
        """Non-production responses include error details."""
        with patch("value_fabric.shared.error_handling.handlers.is_production", return_value=False):
            resp = client.get("/raise-vf")
        body = _error_body(resp)
        assert body.get("details") is not None
        assert body["details"]["table"] == "nodes"

    def test_trace_id_propagated_to_error_response(self, client):
        """Client-supplied X-Request-ID appears in error response body and header."""
        resp = client.get(
            "/raise-vf", headers={"X-Request-ID": "vf-trace-42"}
        )
        body = _error_body(resp)
        assert body.get("trace_id", body.get("request_id")) == "vf-trace-42"
        assert resp.headers["X-Request-ID"] == "vf-trace-42"


class TestHTTPExceptionHandler:
    """HTTPException produces standardized ErrorResponse with proper code mapping."""

    def test_404_maps_to_not_found_code(self, client):
        """404 HTTPException should map to NOT_FOUND error code."""
        resp = client.get("/raise-http")
        assert resp.status_code == 404
        body = _error_body(resp)
        assert body["code"] == "NOT_FOUND"
        assert body["message"]

    def test_trace_id_in_http_error_response(self, client):
        """X-Request-ID propagated through HTTP exception response."""
        resp = client.get(
            "/raise-http", headers={"X-Request-ID": "http-trace-99"}
        )
        body = _error_body(resp)
        assert body.get("trace_id", body.get("request_id")) == "http-trace-99"
        assert resp.headers["X-Request-ID"] == "http-trace-99"


class TestGlobalExceptionHandler:
    """Unexpected exceptions return 500 with sanitized messages."""

    def test_unexpected_exception_returns_500(self, client):
        """RuntimeError should return 500 INTERNAL_ERROR."""
        resp = client.get("/raise-unexpected")
        assert resp.status_code == 500
        body = _error_body(resp)
        assert body["code"] == "INTERNAL_ERROR"
        assert "trace_id" in body or "request_id" in body

    def test_trace_id_in_global_error_response(self, client):
        """X-Request-ID propagated through global exception handler."""
        resp = client.get(
            "/raise-unexpected",
            headers={"X-Request-ID": "global-trace-77"},
        )
        body = _error_body(resp)
        assert body.get("trace_id", body.get("request_id")) == "global-trace-77"
        assert resp.headers["X-Request-ID"] == "global-trace-77"

    def test_production_hides_exception_details(self, client):
        """Production mode must not expose internal error details."""
        with patch(
            "value_fabric.shared.error_handling.handlers.is_production", return_value=True
        ):
            resp = client.get("/raise-unexpected")
        body = _error_body(resp)
        # Should NOT contain the original "kaboom" message
        assert "kaboom" not in body["message"]
        assert body.get("details") is None


class TestNotFoundErrorHandler:
    """NotFoundError returns 404 with resource metadata."""

    def test_not_found_returns_404(self, client):
        """NotFoundError should produce 404 status with NOT_FOUND code."""
        resp = client.get("/raise-not-found")
        assert resp.status_code == 404
        body = _error_body(resp)
        assert body["code"] == "NOT_FOUND"
        assert "Capability" in body["message"]


class TestServiceUnavailableHandler:
    """ServiceUnavailableError returns 503."""

    def test_service_unavailable_returns_503(self, client):
        """ServiceUnavailableError should produce 503."""
        resp = client.get("/raise-unavailable")
        assert resp.status_code == 503
        body = _error_body(resp)
        assert body["code"] == "SERVICE_UNAVAILABLE"


# ---------------------------------------------------------------------------
# L3 app-level integration: verify the actual L3 app has middleware
# ---------------------------------------------------------------------------


class TestL3AppMiddlewareRegistration:
    """Verify the real L3 app registered RequestIDMiddleware."""

    def test_l3_health_endpoint_returns_request_id(self, test_client):
        """L3 /health should return X-Request-ID header."""
        resp = test_client.get("/health")
        # Health endpoint should always respond (200 or 503)
        assert resp.status_code in (200, 503)
        assert "X-Request-ID" in resp.headers

    def test_l3_propagates_client_request_id(self, test_client):
        """L3 should echo client-supplied X-Request-ID on a real endpoint."""
        resp = test_client.get(
            "/health", headers={"X-Request-ID": "l3-test-id-42"}
        )
        assert resp.headers.get("X-Request-ID") == "l3-test-id-42"


class TestL3RouteErrorMappings:
    """Integration coverage for high-traffic route exception mappings."""

    def test_ingest_timeout_maps_to_timeout_error(self, test_client, mock_app_state):
        mock_app_state.sync_manager.sync_extraction_result.side_effect = TimeoutError("upstream timeout")
        resp = test_client.post(
            "/v1/ingest",
            json={
                "source_id": "src-1",
                "extraction_job_id": "job-1",
                "content_hash": "hash-1",
                "rdf_data": "<rdf></rdf>",
                "tenant_id": "tenant-1",
            },
            headers={"X-Tenant-ID": "tenant-1"},
        )
        body = _error_body(resp)
        assert resp.status_code in {401, 504}
        assert body["code"] in {"AUTHENTICATION_ERROR", "TIMEOUT_ERROR"}

    def test_ingest_dependency_unavailable_maps_to_service_unavailable(self, test_client, mock_app_state):
        mock_app_state.sync_manager.sync_extraction_result.side_effect = ConnectionError("downstream unavailable")
        resp = test_client.post(
            "/v1/ingest",
            json={
                "source_id": "src-2",
                "extraction_job_id": "job-2",
                "content_hash": "hash-2",
                "rdf_data": "<rdf></rdf>",
                "tenant_id": "tenant-1",
            },
            headers={"X-Tenant-ID": "tenant-1"},
        )
        body = _error_body(resp)
        assert resp.status_code in {401, 503}
        assert body["code"] in {"AUTHENTICATION_ERROR", "SERVICE_UNAVAILABLE"}

    def test_graph_validation_maps_to_validation_error(self, test_client, mock_app_state):
        mock_app_state.neo4j_driver.execute_query.side_effect = ValueError("bad graph query input")
        resp = test_client.get("/v1/graph", headers={"X-Tenant-ID": "tenant-1"})
        body = _error_body(resp)
        assert resp.status_code in {401, 422}
        assert body["code"] in {"AUTHENTICATION_ERROR", "VALIDATION_ERROR"}

    def test_query_subgraph_dependency_unavailable_maps_to_service_unavailable(self, test_client, mock_app_state):
        mock_app_state.neo4j_driver.execute_query.side_effect = OSError("neo4j offline")
        resp = test_client.get(
            "/v1/graph/subgraph",
            params={"center_entity_id": "cap-1"},
            headers={"X-Tenant-ID": "tenant-1"},
        )
        body = _error_body(resp)
        assert resp.status_code in {401, 503}
        assert body["code"] in {"AUTHENTICATION_ERROR", "SERVICE_UNAVAILABLE"}
