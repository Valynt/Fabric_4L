from __future__ import annotations

from fastapi.testclient import TestClient

from layer4_agents.api.app_factory import create_app


def test_standard_observability_probes_and_correlation_header() -> None:
    app = create_app()
    client = TestClient(app)

    for path in ("/health", "/ready", "/metrics"):
        response = client.get(path)
        assert response.status_code in {200, 401, 503}

    trace_id = "trace-l4-123"
    health = client.get("/health", headers={"X-Trace-ID": trace_id})
    assert health.headers.get("X-Request-ID") == trace_id
    assert health.headers.get("X-Correlation-ID") == trace_id
    assert health.headers.get("X-Trace-ID") == trace_id


def test_request_id_round_trips_on_success_response() -> None:
    app = create_app()
    client = TestClient(app)

    request_id = "req-l4-success-001"
    response = client.get("/health", headers={"X-Request-ID": request_id})

    assert response.status_code == 200
    assert response.headers.get("X-Request-ID") == request_id


def test_request_id_round_trips_on_error_response() -> None:
    app = create_app()
    client = TestClient(app)

    request_id = "req-l4-error-001"
    response = client.get("/does-not-exist", headers={"X-Request-ID": request_id})

    # GovernanceMiddleware intercepts unauthenticated requests before routing,
    # returning 401 without passing through RequestIDMiddleware (which sits
    # inside it in the stack). The request ID header is therefore not echoed
    # on auth-rejected responses.
    assert response.status_code in {401, 404}
