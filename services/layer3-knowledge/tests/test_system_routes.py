"""Focused tests for the extracted Layer 3 system routes."""

from collections.abc import Iterator

from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from conftest import TestUtils
from src.api.dependencies import get_schema_initializer
from src.api.routes import system as system_routes


@pytest.fixture
def system_test_client(mock_app_state: Any) -> Iterator[TestClient]:
    """Mount the extracted system router directly for focused route tests."""
    app = FastAPI()
    app.include_router(system_routes.router)
    app.dependency_overrides[get_schema_initializer] = lambda: mock_app_state.schema_initializer
    app.state.metrics = None

    mock_app_state.schema_initializer._driver = object()
    system_routes.set_app_metrics(None)

    with TestClient(app) as client:
        yield client


class TestSystemRoutes:
    """Validate the extracted operational routes remain wired through the app."""

    def test_health_route_returns_contract(
        self,
        system_test_client: TestClient,
        test_utils: TestUtils,
    ) -> None:
        """The extracted health route still returns the canonical health contract."""
        response = system_test_client.get("/health")

        assert response.status_code == 200
        data: dict[str, Any] = response.json()

        test_utils.assert_valid_health_response(data)
        assert data["neo4j"]["status"] == "healthy"


    def test_health_route_reports_non_ready_when_neo4j_driver_missing(
        self,
        system_test_client: TestClient,
        mock_app_state: Any,
    ) -> None:
        mock_app_state.schema_initializer._driver = None

        response = system_test_client.get("/health")

        assert response.status_code == 200
        data: dict[str, Any] = response.json()
        assert data["readiness"] == {"is_ready": False, "reason": "neo4j_uninitialized"}
        assert data["neo4j"]["status"] == "unavailable"

    def test_health_route_reports_non_ready_when_schema_verify_fails(
        self,
        system_test_client: TestClient,
        mock_app_state: Any,
    ) -> None:
        mock_app_state.schema_initializer.verify_schema.return_value = {
            "status": "error",
            "message": "constraints missing",
        }

        response = system_test_client.get("/health")

        assert response.status_code == 200
        data: dict[str, Any] = response.json()
        assert data["readiness"] == {"is_ready": False, "reason": "schema_verification_failed"}
        assert data["schema_status"]["status"] == "error"

    def test_health_route_reports_non_ready_when_dependency_unhealthy(
        self,
        system_test_client: TestClient,
        mock_app_state: Any,
    ) -> None:
        mock_app_state.schema_initializer.health_check.return_value = {
            "status": "unhealthy",
            "error": "neo4j down",
        }

        response = system_test_client.get("/health")

        assert response.status_code == 200
        data: dict[str, Any] = response.json()
        assert data["readiness"] == {"is_ready": False, "reason": "dependency_unhealthy"}
        assert data["dependencies"][0]["status"] == "unhealthy"

    def test_metrics_route_requires_internal_access(
        self,
        system_test_client: TestClient,
        monkeypatch,
    ) -> None:
        """The extracted metrics route stays internal-only by default."""
        monkeypatch.setattr(system_routes, "verify_metrics_access", lambda request: False)

        response = system_test_client.get("/metrics")

        assert response.status_code == 403
        assert response.json() == {"detail": "Metrics endpoint requires internal access"}