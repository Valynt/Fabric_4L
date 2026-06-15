from __future__ import annotations

from collections.abc import Iterable

from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient


def _get_route_prefix(route: object) -> str:
    """Return the URL prefix for an included router or mount."""
    include_context = getattr(route, "include_context", None)
    if include_context is not None:
        return getattr(include_context, "prefix", "") or ""
    return getattr(route, "path", "") or ""


def _collect_api_paths(routes: Iterable, prefix: str = "") -> set[str]:
    """Recursively collect APIRoute paths, including those in included routers."""
    paths: set[str] = set()
    for route in routes:
        if isinstance(route, APIRoute):
            paths.add(prefix + route.path)
        elif hasattr(route, "original_router"):
            # FastAPI's internal representation of an included APIRouter.
            sub_prefix = prefix + _get_route_prefix(route)
            paths.update(
                _collect_api_paths(route.original_router.routes, prefix=sub_prefix)
            )
        elif hasattr(route, "routes"):
            # Generic mounts / sub-routers (e.g. Starlette Mount).
            sub_prefix = prefix + _get_route_prefix(route)
            paths.update(_collect_api_paths(route.routes, prefix=sub_prefix))
    return paths


def assert_paths_present(app: FastAPI, paths: Iterable[str]) -> None:
    registered_paths = _collect_api_paths(app.routes)
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
