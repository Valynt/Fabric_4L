from __future__ import annotations

from fastapi.testclient import TestClient

from layer6_benchmarks.api.main import app


def test_readiness_alias_matches_ready_status_and_payload_contract():
    with TestClient(app) as client:
        ready_response = client.get("/ready")
        alias_response = client.get("/readiness")

    assert ready_response.status_code in {200, 503}
    assert alias_response.status_code in {200, 503}
    assert alias_response.status_code == ready_response.status_code

    ready_payload = ready_response.json().copy()
    alias_payload = alias_response.json().copy()
    ready_payload.pop("timestamp", None)
    alias_payload.pop("timestamp", None)
    assert alias_payload == ready_payload


def test_readiness_alias_openapi_contract_is_deprecated():
    openapi_spec = app.openapi()
    readiness_alias = openapi_spec["paths"]["/readiness"]["get"]

    assert readiness_alias["deprecated"] is True
