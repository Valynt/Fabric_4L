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
def test_layer1_observability_endpoints_contract() -> None:
    from layer1_ingestion.api.app_monolith import app

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
def test_layer5_observability_endpoints_contract() -> None:
    from layer5_ground_truth.api.main import app

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

    assert_paths_present(app, ("/health", "/ready", "/metrics"))
    client = TestClient(app)
    assert_probe_response_shape(client, path="/health", expected_statuses={200, 503}, expected_json_keys={"status", "service"})
    assert_probe_response_shape(client, path="/ready", expected_statuses={200, 503}, expected_json_keys={"status", "service"})
    assert_probe_response_shape(client, path="/metrics", expected_statuses={200, 401, 403}, content_type_prefix="text/plain")


@pytest.mark.unit
def test_api_gateway_observability_endpoints_contract() -> None:
    from app.main import app

    assert_paths_present(app, ("/health", "/ready", "/metrics"))
    client = TestClient(app)
    assert_probe_response_shape(client, path="/health", expected_statuses={200, 503}, expected_json_keys={"status", "service"})
    assert_probe_response_shape(client, path="/ready", expected_statuses={200, 503}, expected_json_keys={"status", "service"})
    assert_probe_response_shape(client, path="/metrics", expected_statuses={200, 401, 403}, content_type_prefix="text/plain")
