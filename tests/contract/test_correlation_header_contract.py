import logging

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from value_fabric.shared.error_handling.handlers import register_exception_handlers
from value_fabric.shared.error_handling.middleware import RequestIDMiddleware
from value_fabric.shared.observability.trace_context import CANONICAL_TRACE_HEADER


def _build_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(RequestIDMiddleware)
    register_exception_handlers(app)
    logger = logging.getLogger("tests.correlation.contract")

    @app.get("/ok")
    async def ok(request: Request):
        logger.info(
            "contract-log",
            extra={"correlation_id": getattr(request.state, "correlation_id", None)},
        )
        return {"ok": True}

    @app.get("/boom")
    async def boom():
        raise RuntimeError("boom")

    return app


def test_correlation_alias_accepted_canonical_and_alias_headers_emitted_and_log_matches(caplog):
    client = TestClient(_build_app(), raise_server_exceptions=False)
    with caplog.at_level(logging.INFO):
        response = client.get("/ok", headers={"X-Correlation-ID": "corr-12345"})

    assert response.status_code == 200
    assert CANONICAL_TRACE_HEADER in response.headers
    assert response.headers[CANONICAL_TRACE_HEADER] == "corr-12345"
    assert response.headers["X-Correlation-ID"] == "corr-12345"
    assert response.headers["X-Trace-ID"] == "corr-12345"

    matching_logs = [
        rec
        for rec in caplog.records
        if rec.message == "contract-log" and hasattr(rec, "correlation_id")
    ]
    assert matching_logs, "Expected log record with correlation_id field"
    assert matching_logs[-1].correlation_id == response.headers[CANONICAL_TRACE_HEADER]


def test_error_response_includes_canonical_header_and_trace_id():
    client = TestClient(_build_app(), raise_server_exceptions=False)
    response = client.get("/boom", headers={"X-Trace-ID": "trace-999"})

    assert response.status_code == 500
    assert response.headers.get(CANONICAL_TRACE_HEADER) == "trace-999"
    assert response.json()["error"]["request_id"] == "trace-999"
