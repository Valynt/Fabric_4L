"""App-level routing-precedence guard (V1-ROUTING-001 PR-3, review finding F-5).

The layer_delegation catch-all shares URL segments with layer_proxy's typed
routes (/v1/extract, /v1/truths, /v1/workflows, ...). Matching follows
registration order, so precedence depends on layer_delegation being registered
LAST in main.py. These tests resolve requests against the real app's route
table and fail if a reordering ever lets the catch-all swallow a typed route.

Route resolution notes: this FastAPI version wraps each included router in an
``_IncludedRouter``; identity of the owning router is established via
``route.original_router``.
"""

from __future__ import annotations

from starlette.routing import Match

from app.main import app
from app.routers import layer_delegation, layer_proxy


def _resolve_owner(method: str, path: str):
    """Return the router object owning the first FULL match, in registration order."""
    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "headers": [],
        "query_string": b"",
        "root_path": "",
    }
    for route in app.routes:
        try:
            match, _ = route.matches(scope)
        except Exception:  # non-HTTP route types (websocket, lifespan wrappers)
            continue
        if match == Match.FULL:
            return getattr(route, "original_router", None)
    return None


class TestTypedRoutersKeepPrecedence:
    """Paths owned by typed routers must never resolve to the catch-all."""

    def test_post_extract_resolves_to_layer_proxy(self) -> None:
        assert _resolve_owner("POST", "/v1/extract") is layer_proxy.router

    def test_get_truths_resolves_to_layer_proxy(self) -> None:
        assert _resolve_owner("GET", "/v1/truths") is layer_proxy.router

    def test_post_workflows_resolves_to_layer_proxy(self) -> None:
        assert _resolve_owner("POST", "/v1/workflows") is layer_proxy.router

    def test_get_truths_freshness_summary_resolves_to_layer_proxy(self) -> None:
        assert _resolve_owner("GET", "/v1/truths/freshness-summary") is layer_proxy.router


class TestDelegationCatchAllServesUnownedPaths:
    """Positive control: the catch-all does serve paths no typed router owns."""

    def test_get_extract_delegates(self) -> None:
        # layer_proxy owns POST /v1/extract only; GET has no typed route.
        assert _resolve_owner("GET", "/v1/extract") is layer_delegation.router

    def test_graph_subpath_delegates(self) -> None:
        assert _resolve_owner("GET", "/v1/graph/entities") is layer_delegation.router

    def test_delegation_registered_after_layer_proxy(self) -> None:
        """Ordering witness: the delegation wrapper sits after the layer_proxy
        wrapper in the app's route table (registration order is precedence)."""
        owners = [getattr(r, "original_router", None) for r in app.routes]
        assert layer_proxy.router in owners and layer_delegation.router in owners
        assert owners.index(layer_delegation.router) > owners.index(layer_proxy.router)
