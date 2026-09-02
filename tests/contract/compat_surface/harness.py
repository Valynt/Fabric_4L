"""Shared helpers for per-layer app-surface contract tests (brooks R3).

Centralizes the route-collection and middleware-order helpers that were
previously triplicated across the L4/L5/L6 ``test_compat_app_surface_contract.py``
files, so a compat-surface decision is enforced in exactly one place. Each
layer's test file keeps only its layer-specific assertions and imports from
here.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi.routing import APIRoute


def get_route_prefix(route: object) -> str:
    """Return the effective URL prefix for a mounted router or a bare path."""
    include_context = getattr(route, "include_context", None)
    if include_context is not None:
        return getattr(include_context, "prefix", "") or ""
    return getattr(route, "path", "") or ""


def _collect_paths(routes, prefix: str = "") -> set[str]:
    """Recursively collect absolute URL paths from an app's route list."""
    paths: set[str] = set()
    for route in routes:
        if isinstance(route, APIRoute):
            paths.add(prefix + route.path)
        elif hasattr(route, "original_router"):
            paths.update(
                _collect_paths(route.original_router.routes, prefix + get_route_prefix(route))
            )
        elif hasattr(route, "routes"):
            paths.update(_collect_paths(route.routes, prefix + get_route_prefix(route)))
    return paths


def collect_paths(app_routes, prefix: str = "") -> set[str]:
    """Public wrapper marking the route collector as import-stable."""
    return _collect_paths(app_routes, prefix=prefix)


def _collect_routes(routes, prefix: str = "") -> list:
    """Recursively collect APIRoute objects, prefixing paths in place."""
    result: list = []
    for route in routes:
        if isinstance(route, APIRoute):
            route.path = prefix + route.path
            result.append(route)
        elif hasattr(route, "original_router"):
            result.extend(
                _collect_routes(
                    route.original_router.routes,
                    prefix + get_route_prefix(route),
                )
            )
        elif hasattr(route, "routes"):
            result.extend(_collect_routes(route.routes, prefix + get_route_prefix(route)))
    return result


def collect_routes(app_routes, prefix: str = "") -> list:
    """Public wrapper marking the route-object collector as import-stable."""
    return _collect_routes(app_routes, prefix=prefix)


def get_middleware_names(app) -> list[str]:
    """Return effective user-middleware class names, outermost first."""
    return [mw.cls.__name__ for mw in app.user_middleware]


def app_with_noop_lifespan(monkeypatch, build_lifespan_path: str, create_app):
    """Build an app whose lifespan is stubbed out (used when lifespan startup
    would touch external services during compat-surface checks).

    ``build_lifespan_path`` is the dotted module path whose ``build_lifespan``
    is monkeypatched; ``create_app`` is the app factory called afterwards.
    """
    @asynccontextmanager
    async def _noop_lifespan(app):
        yield

    monkeypatch.setattr(build_lifespan_path, lambda **_: _noop_lifespan)
    return create_app()
