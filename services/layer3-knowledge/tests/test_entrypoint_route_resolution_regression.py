from fastapi.routing import APIRoute

from src.api.main import app


def _get_route_prefix(route: object) -> str:
    include_context = getattr(route, "include_context", None)
    if include_context is not None:
        return getattr(include_context, "prefix", "") or ""
    return getattr(route, "path", "") or ""


def _collect_paths(routes, prefix: str = ""):
    paths = set()
    for route in routes:
        if isinstance(route, APIRoute):
            paths.add(prefix + route.path)
        elif hasattr(route, "original_router"):
            paths.update(
                _collect_paths(route.original_router.routes, prefix + _get_route_prefix(route))
            )
        elif hasattr(route, "routes"):
            paths.update(_collect_paths(route.routes, prefix + _get_route_prefix(route)))
    return paths


def test_layer3_entrypoint_exposes_expected_routes() -> None:
    paths = _collect_paths(app.routes)
    expected = {
        "/health",
        "/v1/entities/",
    }
    assert expected.issubset(paths)
