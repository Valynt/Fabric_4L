"""Live OpenAPI smoke tests for maintained service entrypoints (layer1-layer6)."""

from __future__ import annotations

import os

import requests

SERVICE_URLS = {
    "layer1": os.getenv("LAYER1_API_URL", "http://localhost:8001"),
    "layer2": os.getenv("LAYER2_API_URL", "http://localhost:8002"),
    "layer3": os.getenv("LAYER3_API_URL", "http://localhost:8003"),
    "layer4": os.getenv("LAYER4_API_URL", "http://localhost:8004"),
    "layer5": os.getenv("LAYER5_API_URL", "http://localhost:8005"),
    "layer6": os.getenv("LAYER6_API_URL", "http://localhost:8006"),
}


def test_service_entrypoints_publish_openapi_smoke() -> None:
    for layer, base_url in SERVICE_URLS.items():
        response = requests.get(f"{base_url.rstrip('/')}/openapi.json", timeout=10)
        assert response.status_code == 200, f"{layer}: /openapi.json contract endpoint must be reachable"

        payload = response.json()
        assert isinstance(payload.get("paths"), dict), f"{layer}: OpenAPI payload must include paths"
        assert payload["paths"], f"{layer}: OpenAPI paths must not be empty"
