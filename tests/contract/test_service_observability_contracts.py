from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from tests.contract.helpers.observability_endpoints import (
    assert_paths_present,
    assert_probe_response_shape,
)


@pytest.mark.unit
def test_layer1_observability_endpoints_contract() -> None:
    from layer1_ingestion.api.app_monolith import app

    assert_paths_present(app, ("/health", "/ready", "/metrics"))
    client = TestClient(app)
    assert_probe_response_shape(client, path="/health", expected_statuses={200, 503}, expected_json_keys={"status", "service"})
    assert_probe_response_shape(client, path="/ready", expected_statuses={200, 503}, expected_json_keys={"status", "service"})
    assert_probe_response_shape(client, path="/metrics", expected_statuses={200}, content_type_prefix="text/plain")


@pytest.mark.unit
def test_layer2_observability_endpoints_contract() -> None:
    from layer2_extraction.api.main import app

    assert_paths_present(app, ("/health", "/ready", "/metrics"))
    client = TestClient(app)
    assert_probe_response_shape(client, path="/health", expected_statuses={200, 503}, expected_json_keys={"status", "service"})
    assert_probe_response_shape(client, path="/ready", expected_statuses={200, 503}, expected_json_keys={"status", "service"})
    assert_probe_response_shape(client, path="/metrics", expected_statuses={200}, content_type_prefix="text/plain")


@pytest.mark.unit
def test_layer3_observability_endpoints_contract() -> None:
    from src.api.main import app

    assert_paths_present(app, ("/health", "/ready", "/metrics"))
    client = TestClient(app)
    assert_probe_response_shape(client, path="/health", expected_statuses={200, 503}, expected_json_keys={"status", "service"})
    assert_probe_response_shape(client, path="/ready", expected_statuses={200, 503}, expected_json_keys={"status", "service"})
    assert_probe_response_shape(client, path="/metrics", expected_statuses={200, 500}, content_type_prefix="text/plain")


@pytest.mark.unit
def test_layer4_observability_endpoints_contract() -> None:
    from services.layer4_agents.src.api.app_factory import create_app

    app = create_app()
    assert_paths_present(app, ("/health", "/ready", "/metrics"))
    client = TestClient(app)
    assert_probe_response_shape(client, path="/health", expected_statuses={200, 503}, expected_json_keys={"status", "service"})
    assert_probe_response_shape(client, path="/ready", expected_statuses={200, 503}, expected_json_keys={"status", "service"})
    assert_probe_response_shape(client, path="/metrics", expected_statuses={200, 401}, content_type_prefix="text/plain")


@pytest.mark.unit
def test_layer5_observability_endpoints_contract() -> None:
    from layer5_ground_truth.api.main import app

    assert_paths_present(app, ("/health", "/ready", "/metrics"))
    client = TestClient(app)
    assert_probe_response_shape(client, path="/health", expected_statuses={200, 503}, expected_json_keys={"status", "service"})
    assert_probe_response_shape(client, path="/ready", expected_statuses={200, 503}, expected_json_keys={"status", "service"})
    assert_probe_response_shape(client, path="/metrics", expected_statuses={200, 401}, content_type_prefix="text/plain")


@pytest.mark.unit
def test_layer6_observability_endpoints_contract() -> None:
    from services.layer6_benchmarks.src.api.main import app

    assert_paths_present(app, ("/health", "/ready", "/metrics"))
    client = TestClient(app)
    assert_probe_response_shape(client, path="/health", expected_statuses={200, 503}, expected_json_keys={"status", "service"})
    assert_probe_response_shape(client, path="/ready", expected_statuses={200, 503}, expected_json_keys={"status", "service"})
    assert_probe_response_shape(client, path="/metrics", expected_statuses={200, 401}, content_type_prefix="text/plain")


@pytest.mark.unit
def test_api_gateway_observability_endpoints_contract() -> None:
    from app.main import app

    assert_paths_present(app, ("/health", "/ready", "/metrics"))
    client = TestClient(app)
    assert_probe_response_shape(client, path="/health", expected_statuses={200, 503}, expected_json_keys={"status", "service"})
    assert_probe_response_shape(client, path="/ready", expected_statuses={200, 503}, expected_json_keys={"status", "service"})
    assert_probe_response_shape(client, path="/metrics", expected_statuses={200}, content_type_prefix="text/plain")
