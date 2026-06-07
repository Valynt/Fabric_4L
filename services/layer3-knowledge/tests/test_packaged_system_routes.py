from __future__ import annotations

"""Packaged-app proof tests for extracted Layer 3 operational routes."""


from typing import Any

from fastapi.testclient import TestClient

from conftest import TestUtils
from src.api.routes import system as system_routes
from src.api.models import ServiceMetrics


class TestPackagedSystemRoutes:
    """Validate the packaged ASGI app serves the extracted operational routes."""

    def test_packaged_health_route_uses_extracted_system_module(
        self,
        test_client: TestClient,
        test_utils: TestUtils,
        monkeypatch,
    ) -> None:
        """The packaged app should serve /health through the extracted system router."""

        def fake_metrics() -> ServiceMetrics:
            return ServiceMetrics(
                uptime_seconds=123.45,
                memory_usage_mb=67.89,
                cpu_percent=10.5,
                active_connections=2,
                total_requests=42,
                error_rate_percent=0.0,
            )

        monkeypatch.setattr(system_routes, "get_system_metrics", fake_metrics)

        response = test_client.get("/health")

        assert response.status_code == 200
        data: dict[str, Any] = response.json()
        test_utils.assert_valid_health_response(data)
        assert data["metrics"]["uptime_seconds"] == 123.45
        assert data["metrics"]["total_requests"] == 42

    def test_packaged_metrics_route_keeps_internal_gate(
        self,
        test_client: TestClient,
        monkeypatch,
    ) -> None:
        """The packaged app should preserve the extracted metrics access gate."""
        monkeypatch.setattr(system_routes, "verify_metrics_access", lambda request: False)

        response = test_client.get("/metrics")

        assert response.status_code == 403
        data = response.json()
        assert data["code"] == "AUTHORIZATION_ERROR"
        assert data["message"] == "Metrics endpoint requires internal access"
