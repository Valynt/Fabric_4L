from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.testclient import TestClient
from value_fabric.shared.error_handling.handlers import register_exception_handlers
from value_fabric.shared.error_handling.middleware import RequestIDMiddleware
from value_fabric.shared.observability.trace_context import CANONICAL_TRACE_HEADER


def _build_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(RequestIDMiddleware)
    register_exception_handlers(app)

    @app.get("/boom")
    async def boom() -> None:
        raise RuntimeError("raw provider token sk-live-secret should not appear")

    return app


def test_error_response_contains_trace_id_and_canonical_header() -> None:
    response = TestClient(_build_app(), raise_server_exceptions=False).get(
        "/boom",
        headers={CANONICAL_TRACE_HEADER: "req-error-contract"},
    )
    payload = response.json()

    assert response.status_code == 500
    assert response.headers[CANONICAL_TRACE_HEADER] == "req-error-contract"
    assert payload.get("trace_id") == "req-error-contract" or payload.get("error", {}).get("request_id") == "req-error-contract"


def test_error_response_does_not_expose_stacktrace_or_raw_secret() -> None:
    response = TestClient(_build_app(), raise_server_exceptions=False).get("/boom")
    serialized = response.text.lower()

    assert "traceback" not in serialized
    assert "sk-live-secret" not in serialized
    assert "raw provider token" not in serialized


def test_unhandled_exception_log_has_correlation_id(caplog) -> None:
    client = TestClient(_build_app(), raise_server_exceptions=False)
    with caplog.at_level(logging.ERROR):
        response = client.get("/boom", headers={CANONICAL_TRACE_HEADER: "req-log-contract"})

    assert response.status_code == 500
    assert any(
        record.message == "Unhandled exception"
        and getattr(record, "correlation_id", None) == "req-log-contract"
        for record in caplog.records
    )
