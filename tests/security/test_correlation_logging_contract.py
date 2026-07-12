import logging

from fastapi import FastAPI
from fastapi.testclient import TestClient
from value_fabric.shared.error_handling.handlers import register_exception_handlers
from value_fabric.shared.error_handling.middleware import RequestIDMiddleware


def test_global_exception_log_contains_correlation_id(caplog):
    app = FastAPI()
    app.add_middleware(RequestIDMiddleware)
    register_exception_handlers(app)

    @app.get("/critical/boom")
    async def boom():
        raise RuntimeError("boom")

    client = TestClient(app, raise_server_exceptions=False)
    with caplog.at_level(logging.ERROR):
        response = client.get("/critical/boom")

    assert response.status_code == 500
    payload = response.json()
    assert payload.get("trace_id") or payload.get("error", {}).get("request_id")
    found = False
    for rec in caplog.records:
        if rec.message == "Unhandled exception" and hasattr(rec, "correlation_id"):
            assert rec.correlation_id
            found = True
    assert found, "Expected correlation_id field on unhandled exception logs"
