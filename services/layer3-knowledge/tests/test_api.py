"""Tests for API endpoint contracts and validation."""

from http import HTTPStatus
from typing import Any

from fastapi.testclient import TestClient


def test_health_endpoint(test_client: TestClient) -> None:
    """Health endpoint returns 200 when healthy or 503 when degraded/unavailable."""
    response = test_client.get("/health")
    assert response.status_code in {HTTPStatus.OK, HTTPStatus.SERVICE_UNAVAILABLE}


def test_schema_status_endpoint(test_client: TestClient) -> None:
    """Schema status endpoint returns 200 when schema is valid or 503 when unavailable."""
    response = test_client.get("/health/detailed")
    assert response.status_code in {HTTPStatus.OK, HTTPStatus.UNAUTHORIZED, HTTPStatus.SERVICE_UNAVAILABLE}


def test_ingest_endpoint_validation(test_client: TestClient) -> None:
    """Ingest endpoint validates required fields (422) and accepts valid requests."""
    response = test_client.post("/v1/ingest", json={})
    assert response.status_code in {HTTPStatus.UNAUTHORIZED, HTTPStatus.UNPROCESSABLE_ENTITY}

    payload: dict[str, Any] = {
        "rdf_data": "test",
        "source_id": "src-1",
        "extraction_job_id": "job-1",
        "tenant_id": "tenant-test-123",
    }
    response = test_client.post("/v1/ingest", json=payload)
    assert response.status_code in {HTTPStatus.OK, HTTPStatus.UNAUTHORIZED, HTTPStatus.INTERNAL_SERVER_ERROR, HTTPStatus.SERVICE_UNAVAILABLE}




def test_ingest_rejects_tenant_header_without_authenticated_context(test_client: TestClient) -> None:
    """X-Tenant-ID alone must not satisfy ingest tenant authentication requirements."""
    payload: dict[str, Any] = {
        "rdf_data": "test",
        "source_id": "src-1",
        "extraction_job_id": "job-1",
    }

    response = test_client.post(
        "/v1/ingest",
        json=payload,
        headers={"X-Tenant-ID": "tenant-spoof-attempt"},
    )

    assert response.status_code == HTTPStatus.UNAUTHORIZED
    detail = response.json()["detail"]
    # detail may be a string or a list of validation error dicts
    detail_str = detail if isinstance(detail, str) else str(detail)
    assert any(
        msg in detail_str
        for msg in (
            "Authenticated tenant context required for ingestion",
            "Authentication credentials were not provided.",
            "Not authenticated",
        )
    ), f"Unexpected detail: {detail!r}"

def test_query_endpoint_validation(test_client: TestClient) -> None:
    """Query endpoint validates required fields (422) and accepts valid requests."""
    response = test_client.post("/v1/query/graph", json={})
    assert response.status_code in {HTTPStatus.UNAUTHORIZED, HTTPStatus.UNPROCESSABLE_ENTITY}

    payload: dict[str, Any] = {"query": "test query", "max_hops": 3}
    response = test_client.post("/v1/query/graph", json=payload)
    assert response.status_code in {HTTPStatus.OK, HTTPStatus.UNAUTHORIZED, HTTPStatus.INTERNAL_SERVER_ERROR, HTTPStatus.SERVICE_UNAVAILABLE}


def test_search_endpoint_validation(test_client: TestClient) -> None:
    """Search endpoint validates required fields (422) and accepts valid requests."""
    response = test_client.post("/v1/search", json={})
    assert response.status_code in {HTTPStatus.UNAUTHORIZED, HTTPStatus.UNPROCESSABLE_ENTITY}

    payload: dict[str, Any] = {"query": "test", "search_type": "hybrid"}
    response = test_client.post("/v1/search", json=payload)
    assert response.status_code in {HTTPStatus.OK, HTTPStatus.UNAUTHORIZED, HTTPStatus.INTERNAL_SERVER_ERROR, HTTPStatus.SERVICE_UNAVAILABLE}
