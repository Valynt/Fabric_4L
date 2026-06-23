"""Runtime regression tests for the canonical API error envelope.

Each maintained L2-L6 layer must register shared exception handlers that emit
one envelope shape for auth, authorization, not-found, validation, and 500s:

{
  "error": {"code": "...", "message": "...", "request_id": "...", "details": ...}
}
"""

from __future__ import annotations

import importlib.util
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "packages" / "shared" / "src"))

from value_fabric.shared.error_handling.exceptions import (  # noqa: E402
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
)

pytestmark = pytest.mark.contract_static_no_service

LAYER_ADAPTERS = {
    "layer2-extraction": REPO_ROOT
    / "services/layer2-extraction/src/layer2_extraction/adapters/value_fabric_api.py",
    "layer3-knowledge": REPO_ROOT
    / "services/layer3-knowledge/src/adapters/value_fabric_api.py",
    "layer4-agents": REPO_ROOT
    / "services/layer4-agents/src/adapters/value_fabric_api.py",
    "layer5-ground-truth": REPO_ROOT
    / "services/layer5-ground-truth/src/layer5_ground_truth/adapters/value_fabric_api.py",
    "layer6-benchmarks": REPO_ROOT
    / "services/layer6-benchmarks/src/layer6_benchmarks/adapters/value_fabric_api.py",
}


class ValidationPayload(BaseModel):
    name: str


def _load_register_exception_handlers(layer: str) -> Callable[[FastAPI], None]:
    adapter_path = LAYER_ADAPTERS[layer]
    spec = importlib.util.spec_from_file_location(
        f"{layer.replace('-', '_')}_value_fabric_api", adapter_path
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.register_exception_handlers


def _build_client(layer: str) -> TestClient:
    app = FastAPI(title=f"{layer} error contract test")
    _load_register_exception_handlers(layer)(app)

    @app.get("/auth")
    def auth() -> None:
        raise AuthenticationError()

    @app.get("/forbidden")
    def forbidden() -> None:
        raise AuthorizationError()

    @app.get("/missing")
    def missing() -> None:
        raise NotFoundError(resource_type="widget", resource_id="missing")

    @app.post("/validation")
    def validation(payload: ValidationPayload) -> dict[str, str]:
        return {"name": payload.name}

    @app.get("/boom")
    def boom() -> None:
        raise RuntimeError("simulated internal failure")

    @app.get("/http-500")
    def http_500() -> None:
        raise HTTPException(status_code=500, detail="internal failure")

    return TestClient(app, raise_server_exceptions=False)


def _assert_envelope(body: dict[str, Any], *, expected_code: str) -> None:
    assert set(body) == {"error"}
    error = body["error"]
    assert set(error).issubset({"code", "message", "request_id", "details"})
    assert error["code"] == expected_code
    assert isinstance(error["message"], str) and error["message"]
    assert isinstance(error["request_id"], str) and error["request_id"]
    assert "trace_id" not in error
    assert "error_code" not in error


@pytest.mark.parametrize("layer", list(LAYER_ADAPTERS))
@pytest.mark.parametrize(
    ("method", "path", "json", "status_code", "error_code"),
    [
        ("get", "/auth", None, 401, "AUTHENTICATION_ERROR"),
        ("get", "/forbidden", None, 403, "AUTHORIZATION_ERROR"),
        ("get", "/missing", None, 404, "NOT_FOUND"),
        ("post", "/validation", {}, 422, "VALIDATION_ERROR"),
        ("get", "/boom", None, 500, "INTERNAL_ERROR"),
        ("get", "/http-500", None, 500, "INTERNAL_ERROR"),
    ],
)
def test_layer_error_handlers_emit_canonical_envelope(
    layer: str,
    method: str,
    path: str,
    json: dict[str, Any] | None,
    status_code: int,
    error_code: str,
) -> None:
    client = _build_client(layer)

    request = getattr(client, method)
    response = request(path, json=json) if json is not None else request(path)

    assert response.status_code == status_code
    _assert_envelope(response.json(), expected_code=error_code)
