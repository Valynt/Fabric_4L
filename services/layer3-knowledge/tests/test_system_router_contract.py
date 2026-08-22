"""Contract and characterization tests for Layer 3 system routes."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from src.api.dependencies import get_schema_initializer
from src.api.main import app
from src.api.models import DependencyStatus
from src.api.routes.system import (
    _build_configuration,
    _build_system_info,
    _check_neo4j_dependency,
    _check_pinecone_dependency,
    _derive_overall_status,
    _derive_readiness,
    _resolve_neo4j_and_schema_status,
)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_check_neo4j_dependency_uninitialized():
    """Verify degraded status when driver is None."""
    mock_init = SimpleNamespace(_driver=None)
    mock_settings = SimpleNamespace(neo4j_uri="bolt://localhost:7687", neo4j_database="neo4j")

    status = await _check_neo4j_dependency(mock_init, mock_settings)
    assert status.name == "neo4j"
    assert status.status == "degraded"
    assert status.failure_reason == "neo4j_not_initialized"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_check_neo4j_dependency_healthy():
    """Verify healthy status when health_check succeeds."""
    mock_init = SimpleNamespace(
        _driver=MagicMock(),
        health_check=AsyncMock(return_value={"status": "healthy"}),
    )
    mock_settings = SimpleNamespace(neo4j_uri="bolt://localhost:7687", neo4j_database="neo4j")

    status = await _check_neo4j_dependency(mock_init, mock_settings)
    assert status.name == "neo4j"
    assert status.status == "healthy"
    assert status.failure_reason is None
    assert status.response_time_ms is not None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_check_neo4j_dependency_connection_error():
    """Verify unhealthy status on connection failure."""
    mock_init = SimpleNamespace(
        _driver=MagicMock(),
        health_check=AsyncMock(side_effect=ConnectionError("Cannot connect")),
    )
    mock_settings = SimpleNamespace(neo4j_uri="bolt://localhost:7687", neo4j_database="neo4j")

    status = await _check_neo4j_dependency(mock_init, mock_settings)
    assert status.name == "neo4j"
    assert status.status == "unhealthy"
    assert status.failure_reason == "neo4j_connection_error"


@pytest.mark.unit
def test_check_pinecone_dependency():
    """Verify pinecone dependency checking behavior."""
    # When unconfigured
    settings_no_pinecone = SimpleNamespace(pinecone_api_key=None)
    assert _check_pinecone_dependency(settings_no_pinecone) is None

    # When configured
    settings_pinecone = SimpleNamespace(
        pinecone_api_key="pk-123",
        pinecone_index="kb-index",
    )
    dep = _check_pinecone_dependency(settings_pinecone)
    assert dep is not None
    assert dep.name == "pinecone"
    assert dep.status == "healthy"
    assert dep.details == {"index": "kb-index"}


@pytest.mark.unit
def test_derive_overall_status_and_readiness():
    """Verify overall status aggregation and readiness determination."""
    healthy_neo = DependencyStatus(name="neo4j", status="healthy")
    unhealthy_neo = DependencyStatus(name="neo4j", status="unhealthy")
    degraded_neo = DependencyStatus(name="neo4j", status="degraded")
    dummy_init = SimpleNamespace(_driver=MagicMock())

    # Overall status
    assert _derive_overall_status([healthy_neo], dummy_init) == "healthy"
    assert _derive_overall_status([healthy_neo], None) == "degraded"
    assert _derive_overall_status([unhealthy_neo], dummy_init) == "unhealthy"
    assert _derive_overall_status([degraded_neo], dummy_init) == "degraded"

    # Readiness
    assert _derive_readiness(
        dependencies=[healthy_neo],
        schema_initializer=dummy_init,
        schema_status={"valid": True},
    ) == {"is_ready": True, "reason": "dependencies_available"}

    assert _derive_readiness(
        dependencies=[healthy_neo],
        schema_initializer=dummy_init,
        schema_status={"valid": False},
    ) == {"is_ready": False, "reason": "schema_verification_failed"}

    assert _derive_readiness(
        dependencies=[unhealthy_neo],
        schema_initializer=dummy_init,
        schema_status={"valid": True},
    ) == {"is_ready": False, "reason": "dependency_unhealthy"}


@pytest.mark.unit
def test_build_system_info_and_configuration():
    """Verify system info and config dictionary construction."""
    sys_info = _build_system_info()
    assert "platform" in sys_info
    assert "python_version" in sys_info
    assert "cpu_count" in sys_info
    assert "memory_total_gb" in sys_info

    mock_settings = SimpleNamespace(
        api_host="0.0.0.0",
        api_port=8003,
        log_level="INFO",
        log_format="json",
        neo4j_database="neo4j",
        neo4j_max_pool_size=50,
        pinecone_api_key="pk-test",
    )
    config = _build_configuration(mock_settings)
    assert config["api_host"] == "0.0.0.0"
    assert config["pinecone_configured"] is True


@pytest.mark.unit
def test_health_endpoints_contract():
    """Verify /health and /health/detailed endpoints return proper responses."""
    mock_init = SimpleNamespace(
        _driver=MagicMock(),
        health_check=AsyncMock(return_value={"status": "healthy"}),
        verify_schema=AsyncMock(return_value={"valid": True}),
    )
    app.dependency_overrides[get_schema_initializer] = lambda: mock_init
    try:
        client = TestClient(app)

        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "layer3-knowledge"
        assert "status" in data
        assert "readiness" in data
        assert "dependencies" in data

        response_detailed = client.get("/health/detailed")
        assert response_detailed.status_code == 200
        detailed_data = response_detailed.json()
        assert "system_info" in detailed_data
        assert "configuration" in detailed_data
        assert "uptime_seconds" in detailed_data
    finally:
        app.dependency_overrides.pop(get_schema_initializer, None)
