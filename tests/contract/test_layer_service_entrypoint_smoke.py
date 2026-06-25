"""Contract smoke tests for maintained service entrypoints (layer1-layer6)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[2]

ENTRYPOINTS = {
    "layer1": REPO_ROOT / "services/layer1-ingestion/src/layer1_ingestion/api/main.py",
    "layer2": REPO_ROOT / "services/layer2-extraction/src/layer2_extraction/api/main.py",
    "layer3": REPO_ROOT / "services/layer3-knowledge/src/api/main.py",
    "layer4": REPO_ROOT / "services/layer4-agents/src/layer4_agents/api/main.py",
    "layer5": REPO_ROOT / "services/layer5-ground-truth/src/layer5_ground_truth/api/main.py",
    "layer6": REPO_ROOT / "services/layer6-benchmarks/src/api/main.py",
}


def _load_module(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_service_entrypoints_publish_openapi_smoke() -> None:
    for layer, entrypoint in ENTRYPOINTS.items():
        module = _load_module(entrypoint, f"{layer}_service_main")
        assert hasattr(module, "app"), f"{layer} entrypoint must export app"

        client = TestClient(module.app)
        response = client.get("/openapi.json")
        assert response.status_code == 200, f"{layer}: /openapi.json contract endpoint must be reachable"

        payload = response.json()
        assert isinstance(payload.get("paths"), dict), f"{layer}: OpenAPI payload must include paths"
        assert payload["paths"], f"{layer}: OpenAPI paths must not be empty"
