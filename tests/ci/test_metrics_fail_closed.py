"""Tests for /metrics endpoint fail-closed behavior."""
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "services" / "layer4-agents" / "src"))

from layer4_agents.api.core_routes import register_core_routes


def _setup_app(metrics_available: bool, authorized: bool = True) -> tuple[FastAPI, TestClient, Any, Any]:
    import layer4_agents.api.core_routes as core_routes

    # Directly manipulate module globals so runtime lookups see the mocked state
    orig_metrics_available = core_routes.METRICS_ACCESS_AVAILABLE
    orig_verify_metrics_access = core_routes.verify_metrics_access

    core_routes.METRICS_ACCESS_AVAILABLE = metrics_available
    core_routes.verify_metrics_access = (
        (lambda _r: (authorized, None)) if metrics_available else None
    )

    app = FastAPI()
    register_core_routes(app)

    app.state.metrics = MagicMock()
    app.state.metrics.get_metrics = MagicMock(return_value="# test\n")
    return app, TestClient(app), orig_metrics_available, orig_verify_metrics_access


class TestMetricsEndpoint:
    def test_metrics_auth_available_and_authorized(self):
        """When auth module is available and request is authorized, metrics are served."""
        import layer4_agents.api.core_routes as core_routes

        _, client, orig_ma, orig_va = _setup_app(metrics_available=True, authorized=True)
        try:
            response = client.get("/metrics")
            assert response.status_code == 200
            assert "# test" in response.text
        finally:
            core_routes.METRICS_ACCESS_AVAILABLE = orig_ma
            core_routes.verify_metrics_access = orig_va

    def test_metrics_auth_available_and_unauthorized(self):
        """When auth module is available but request is unauthorized, return 401."""
        import layer4_agents.api.core_routes as core_routes

        _, client, orig_ma, orig_va = _setup_app(metrics_available=True, authorized=False)
        try:
            response = client.get("/metrics")
            assert response.status_code == 401
            assert "Unauthorized" in response.text
        finally:
            core_routes.METRICS_ACCESS_AVAILABLE = orig_ma
            core_routes.verify_metrics_access = orig_va

    def test_metrics_auth_unavailable_fails_closed(self):
        """When auth module is unavailable, /metrics must fail closed with 403."""
        import layer4_agents.api.core_routes as core_routes

        _, client, orig_ma, orig_va = _setup_app(metrics_available=False)
        try:
            response = client.get("/metrics")
            assert response.status_code == 403
            assert "unavailable" in response.text.lower()
        finally:
            core_routes.METRICS_ACCESS_AVAILABLE = orig_ma
            core_routes.verify_metrics_access = orig_va
