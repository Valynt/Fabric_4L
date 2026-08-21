from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from tests.contract.helpers.observability_endpoints import (
    assert_paths_present,
    assert_probe_response_shape,
)

_BYPASS_FLAGS = (
    "ALLOW_INSECURE_DEV_AUTH_BYPASS",
    "DEV_AUTH_BYPASS",
    "AUTH_BYPASS_ENABLED",
    "ALLOW_DEV_AUTH_BYPASS",
)


def _force_test_startup_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("APP_ENV", "test")
    for flag in _BYPASS_FLAGS:
        monkeypatch.delenv(flag, raising=False)


@pytest.mark.unit
def test_layer1_observability_endpoints_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    from unittest.mock import MagicMock

    import layer1_ingestion.shared.database as l1_db
    from layer1_ingestion.api.main import app
    import layer1_ingestion.api.main as l1_main

    # Mock engine.connect and _new_session so DB health/readiness probes execute cleanly without network timeouts
    mock_session = MagicMock()
    mock_conn = MagicMock()
    mock_engine = MagicMock()
    mock_engine.connect.return_value = mock_conn
    monkeypatch.setattr(l1_main, "engine", mock_engine)
    monkeypatch.setattr(l1_db, "engine", mock_engine)
    monkeypatch.setattr(l1_db, "_new_session", lambda: mock_session)

    assert_paths_present(app, ("/health", "/ready", "/metrics"))
    client = TestClient(app)
    assert_probe_response_shape(client, path="/health", expected_statuses={200, 503}, expected_json_keys={"status", "service"})
    assert_probe_response_shape(client, path="/ready", expected_statuses={200, 503}, expected_json_keys={"status", "service"})
    assert_probe_response_shape(client, path="/metrics", expected_statuses={200, 401, 403}, content_type_prefix="text/plain")


@pytest.mark.unit
def test_layer2_observability_endpoints_contract() -> None:
    from layer2_extraction.api.main import app

    assert_paths_present(app, ("/health", "/ready", "/metrics"))
    client = TestClient(app)
    assert_probe_response_shape(client, path="/health", expected_statuses={200, 503}, expected_json_keys={"status", "service"})
    assert_probe_response_shape(client, path="/ready", expected_statuses={200, 503}, expected_json_keys={"status", "service"})
    assert_probe_response_shape(client, path="/metrics", expected_statuses={200, 401, 403}, content_type_prefix="text/plain")


@pytest.mark.unit
def test_layer3_observability_endpoints_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    _force_test_startup_environment(monkeypatch)
    monkeypatch.setenv("TESTING", "true")
    from src.api.main import app

    assert_paths_present(app, ("/health", "/ready", "/metrics"))
    client = TestClient(app)
    assert_probe_response_shape(client, path="/health", expected_statuses={200, 503}, expected_json_keys={"status", "service"})
    assert_probe_response_shape(client, path="/ready", expected_statuses={200, 503}, expected_json_keys={"status", "service"})
    assert_probe_response_shape(client, path="/metrics", expected_statuses={200, 401, 403}, content_type_prefix="text/plain")


@pytest.mark.unit
def test_layer4_observability_endpoints_contract() -> None:
    from services.layer4_agents.src.api.app_factory import create_app

    app = create_app()
    assert_paths_present(app, ("/health", "/ready", "/metrics"))
    client = TestClient(app)
    assert_probe_response_shape(client, path="/health", expected_statuses={200, 503}, expected_json_keys={"status", "service"})
    assert_probe_response_shape(client, path="/ready", expected_statuses={200, 503}, expected_json_keys={"status", "service"})
    assert_probe_response_shape(client, path="/metrics", expected_statuses={200, 401, 403}, content_type_prefix="text/plain")


@pytest.mark.unit
def test_layer5_observability_endpoints_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    from layer5_ground_truth.api.main import app
    import layer5_ground_truth.api.main as l5_main

    async def _mock_db_connectivity():
        return None

    async def _mock_schema_alignment():
        return {"ready": True, "schema": "aligned", "reason": "schema_aligned", "current_revisions": ["head"], "expected_heads": ["head"]}

    monkeypatch.setattr(l5_main, "_check_database_connectivity", _mock_db_connectivity)
    monkeypatch.setattr(l5_main, "_check_schema_migration_alignment", _mock_schema_alignment)

    assert_paths_present(app, ("/health", "/ready", "/metrics"))
    client = TestClient(app)
    assert_probe_response_shape(client, path="/health", expected_statuses={200, 503}, expected_json_keys={"status", "service"})
    assert_probe_response_shape(client, path="/ready", expected_statuses={200, 503}, expected_json_keys={"status", "service"})
    assert_probe_response_shape(client, path="/metrics", expected_statuses={200, 401, 403}, content_type_prefix="text/plain")


@pytest.mark.unit
def test_layer6_observability_endpoints_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    _force_test_startup_environment(monkeypatch)
    # docker-compose.test.yml provisions Neo4j with the short password "test"
    # (mirrored by the global test env). Layer 6 enforces a >=12 char secret via
    # fail-closed settings validation at import time, so provide an import-valid
    # password locally without disturbing the global value that real Neo4j
    # integration tests rely on for container authentication.
    monkeypatch.setenv("NEO4J_PASSWORD", "test-neo4j-password-123")
    from layer6_benchmarks.settings import get_layer6_settings

    get_layer6_settings.cache_clear()
    from layer6_benchmarks.api.main import app
    import layer6_benchmarks.api.main as l6_main

    # Mock neo4j health check and benchmark repo check so static contract test doesn't spend ~15s on retry backoffs
    async def _mock_neo4j_health():
        return {"status": "healthy"}

    monkeypatch.setattr(l6_main, "neo4j_health_check", _mock_neo4j_health)

    assert_paths_present(app, ("/health", "/ready", "/metrics"))
    client = TestClient(app)
    assert_probe_response_shape(client, path="/health", expected_statuses={200, 503}, expected_json_keys={"status", "service"})
    assert_probe_response_shape(client, path="/ready", expected_statuses={200, 503}, expected_json_keys={"status", "service"})
    assert_probe_response_shape(client, path="/metrics", expected_statuses={200, 401, 403}, content_type_prefix="text/plain")


@pytest.mark.unit
def test_api_gateway_observability_endpoints_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    import httpx
    import respx

    from app.core.config import get_settings
    from app.core.database import InMemoryDatabase
    from app.services.distributed_store import InMemoryDistributedStore
    from app.main import app

    # Mock the underlying probe dependencies
    monkeypatch.setattr("app.core.database.create_database", lambda: InMemoryDatabase())
    monkeypatch.setattr("app.services.distributed_store.get_distributed_store", lambda: InMemoryDistributedStore())

    settings = get_settings()
    layer4_url = f"{settings.layer4_api_base_url.rstrip('/')}/ready"

    # Mock layer4 probe http call
    def mock_layer4_ready(url, *args, **kwargs):
        if url == layer4_url:
            return httpx.Response(200, json={"status": "ready", "service": "layer4-agents"})
        return httpx.Response(404)

    monkeypatch.setattr(httpx, "get", mock_layer4_ready)

    assert_paths_present(app, ("/health", "/ready", "/metrics"))
    client = TestClient(app)
    assert_probe_response_shape(client, path="/health", expected_statuses={200, 503}, expected_json_keys={"status", "service"})
    assert_probe_response_shape(client, path="/ready", expected_statuses={200, 503}, expected_json_keys={"status", "service"})
    assert_probe_response_shape(client, path="/metrics", expected_statuses={200, 401, 403}, content_type_prefix="text/plain")
