from __future__ import annotations

from collections.abc import Iterable

from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient


def assert_paths_present(app: FastAPI, paths: Iterable[str]) -> None:
    registered_paths = {route.path for route in app.routes if isinstance(route, APIRoute)}
    for path in paths:
        assert path in registered_paths, f"Missing observability path: {path}"


def assert_probe_response_shape(
    client: TestClient,
    *,
    path: str,
    expected_statuses: set[int],
    expected_json_keys: set[str] | None = None,
    content_type_prefix: str | None = None,
) -> None:
    response = client.get(path)
    assert response.status_code in expected_statuses, response.text

    # Content-type is only meaningful for a served payload. Denied probes
    # (e.g. an internal-only /metrics returning 401/403) emit a JSON error body,
    # so only assert the success content-type when the endpoint actually served.
    if content_type_prefix is not None and response.status_code == 200:
        assert response.headers.get("content-type", "").startswith(content_type_prefix)

    if expected_json_keys is not None and response.status_code == 200:
        body = response.json()
        for key in expected_json_keys:
            assert key in body, f"Missing key '{key}' in {path} payload"
