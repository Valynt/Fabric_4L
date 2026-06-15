from fastapi.routing import APIRoute

from layer6_benchmarks.api.main import app


def _get_route_prefix(route: object) -> str:
    include_context = getattr(route, "include_context", None)
    if include_context is not None:
        return getattr(include_context, "prefix", "") or ""
    return getattr(route, "path", "") or ""


def _collect_paths(routes, prefix: str = "") -> set[str]:
    paths: set[str] = set()
    for route in routes:
        if isinstance(route, APIRoute):
            paths.add(prefix + route.path)
        elif hasattr(route, "original_router"):
            paths.update(
                _collect_paths(
                    route.original_router.routes,
                    prefix + _get_route_prefix(route),
                )
            )
        elif hasattr(route, "routes"):
            paths.update(
                _collect_paths(route.routes, prefix + _get_route_prefix(route))
            )
    return paths


def test_wrapper_main_exposes_fastapi_app() -> None:
    assert app is not None


def test_wrapper_routes_registered() -> None:
    paths = _collect_paths(app.routes)
    assert "/health" in paths
    assert any(path.startswith("/v1/benchmarks") for path in paths)
