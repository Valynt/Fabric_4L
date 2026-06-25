"""Health and metrics endpoint tests.

RB-8 FIX: The original test_metrics() test assumed unauthenticated access to
/metrics always returns 200. This is only true in development mode with
ALLOW_INSECURE_DEV_AUTH_BYPASS=true. In production/staging environments the
endpoint correctly returns 403 for unauthenticated requests.

The tests are now split into:
  - test_health_check: always passes (no auth required)
  - test_metrics_unauthenticated_returns_403_in_production: verifies that
    unauthenticated scrape requests are rejected when the dev bypass is off
  - test_metrics_with_scrape_token_returns_200: verifies that a valid
    METRICS_INTERNAL_SCRAPE_TOKEN grants access in any environment
  - test_metrics_dev_bypass_allows_unauthenticated: verifies the dev bypass
    path still works in development mode (regression guard)
"""

import os

import pytest
from fastapi.testclient import TestClient


def test_health_check():
    """Health endpoint must always return 200 with correct payload."""
    # Import here so conftest env overrides are applied first
    from app.main import app

    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "fabric-4l-api"


def test_metrics_unauthenticated_returns_403_in_production(monkeypatch):
    """Unauthenticated /metrics requests must be rejected (403) when the dev
    bypass is disabled, regardless of environment.

    This is the security regression guard: if this test fails it means the
    metrics endpoint has been accidentally opened to unauthenticated access.
    """
    monkeypatch.setenv("ALLOW_INSECURE_DEV_AUTH_BYPASS", "false")
    monkeypatch.delenv("METRICS_INTERNAL_SCRAPE_TOKEN", raising=False)

    from app.main import app

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/metrics")
        assert response.status_code == 403, (
            f"Expected 403 for unauthenticated /metrics access with bypass disabled, "
            f"got {response.status_code}. "
            "This means the metrics endpoint is open to unauthenticated access."
        )


def test_metrics_with_scrape_token_returns_200(monkeypatch):
    """A valid METRICS_INTERNAL_SCRAPE_TOKEN must grant access to /metrics
    and the response must contain the expected Prometheus metric families.
    """
    scrape_token = "test-scrape-token-abc123-secure"
    monkeypatch.setenv("METRICS_INTERNAL_SCRAPE_TOKEN", scrape_token)
    monkeypatch.setenv("ALLOW_INSECURE_DEV_AUTH_BYPASS", "false")

    from app.main import app

    with TestClient(app) as client:
        # Trigger a request first so counters are non-zero
        client.get("/health")
        response = client.get(
            "/metrics",
            headers={"Authorization": f"Bearer {scrape_token}"},
        )
        assert response.status_code == 200, (
            f"Expected 200 for authenticated /metrics access, got {response.status_code}. "
            f"Body: {response.text[:200]}"
        )
        assert response.headers["content-type"].startswith("text/plain")
        body = response.text
        assert "fabric_api_http_requests_total" in body, (
            "fabric_api_http_requests_total counter missing from /metrics output"
        )
        assert "fabric_api_http_request_duration_seconds_bucket" in body, (
            "fabric_api_http_request_duration_seconds_bucket histogram missing"
        )
        assert "fabric_api_http_errors_total" in body, (
            "fabric_api_http_errors_total counter missing from /metrics output"
        )
        assert 'fabric_api_dependency_health{dependency="database"}' in body, (
            'fabric_api_dependency_health{dependency="database"} gauge missing'
        )


def test_metrics_with_x_prometheus_scrape_token_returns_200(monkeypatch):
    """The X-Prometheus-Scrape-Token header must also grant access to /metrics."""
    scrape_token = "test-scrape-token-abc123-secure"
    monkeypatch.setenv("METRICS_INTERNAL_SCRAPE_TOKEN", scrape_token)
    monkeypatch.setenv("ALLOW_INSECURE_DEV_AUTH_BYPASS", "false")

    from app.main import app

    with TestClient(app) as client:
        client.get("/health")
        response = client.get(
            "/metrics",
            headers={"X-Prometheus-Scrape-Token": scrape_token},
        )
        assert response.status_code == 200


def test_metrics_dev_bypass_allows_unauthenticated(monkeypatch):
    """In development mode with ALLOW_INSECURE_DEV_AUTH_BYPASS=true, unauthenticated
    /metrics access must succeed (regression guard for the dev bypass path).
    """
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("ALLOW_INSECURE_DEV_AUTH_BYPASS", "true")
    monkeypatch.delenv("METRICS_INTERNAL_SCRAPE_TOKEN", raising=False)

    from app.main import app

    with TestClient(app) as client:
        client.get("/health")
        response = client.get("/metrics")
        assert response.status_code == 200, (
            f"Dev bypass should allow unauthenticated /metrics access, "
            f"got {response.status_code}"
        )
