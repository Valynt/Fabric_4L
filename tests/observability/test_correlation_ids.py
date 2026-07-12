from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from value_fabric.shared.error_handling.middleware import RequestIDMiddleware
from value_fabric.shared.observability.correlation import (
    LOG_FIELD_CORRELATION_ID,
    LOG_FIELD_TRACE_ID,
    REQUEST_STATE_CORRELATION_ID_KEY,
    REQUEST_STATE_TRACE_ID_KEY,
)
from value_fabric.shared.observability.trace_context import (
    ALL_TRACE_HEADERS,
    CANONICAL_TRACE_HEADER,
    TRACE_HEADER_ALIASES,
    sanitize_trace_id,
)


def _build_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(RequestIDMiddleware, generator=lambda: "generated-contract-id")

    @app.get("/echo")
    async def echo(request: Request) -> dict[str, str]:
        return {
            "trace_id": getattr(request.state, REQUEST_STATE_TRACE_ID_KEY),
            "correlation_id": getattr(request.state, REQUEST_STATE_CORRELATION_ID_KEY),
            "request_id": request.state.request_id,
        }

    return app


def test_request_id_generated_when_missing() -> None:
    response = TestClient(_build_app()).get("/echo")
    assert response.status_code == 200
    assert response.json()["trace_id"] == "req_generated-contra"
    for header in ALL_TRACE_HEADERS:
        assert response.headers[header] == "req_generated-contra"


def test_canonical_request_id_preserved() -> None:
    response = TestClient(_build_app()).get("/echo", headers={CANONICAL_TRACE_HEADER: "req-explicit"})
    assert response.json()["trace_id"] == "req-explicit"
    assert response.headers[CANONICAL_TRACE_HEADER] == "req-explicit"


def test_supported_aliases_are_accepted_and_mirrored() -> None:
    for alias in TRACE_HEADER_ALIASES:
        response = TestClient(_build_app()).get("/echo", headers={alias: "alias-123"})
        assert response.status_code == 200
        assert response.json()["correlation_id"] == "alias-123"
        assert response.headers[CANONICAL_TRACE_HEADER] == "alias-123"


def test_invalid_request_id_is_sanitized() -> None:
    assert sanitize_trace_id("bad value with spaces", generator=lambda: "fallback") == "req_fallback"


def test_shared_log_field_names_remain_stable() -> None:
    assert LOG_FIELD_TRACE_ID == "trace_id"
    assert LOG_FIELD_CORRELATION_ID == "correlation_id"
