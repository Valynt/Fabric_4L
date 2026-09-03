"""Layer-4 compat-surface contract tests (brooks R3).

Route collectors and middleware helpers are centralized in the shared harness
``tests/contract/compat_surface/harness.py``; this file keeps only the
layer-specific assertions that are not already covered by the shared helpers.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from fastapi.testclient import TestClient

from layer4_agents.api.app_factory import create_app

# The repo-root ``tests`` package is shadowed by this layer's own ``tests``
# package (it has an ``__init__.py``), so the shared harness is loaded from
# its absolute path instead of via ``from tests.contract...``.
_HARNESS_PATH = (
    Path(__file__).resolve().parents[3]
    / "tests"
    / "contract"
    / "compat_surface"
    / "harness.py"
)
_spec = importlib.util.spec_from_file_location("_compat_surface_harness", _HARNESS_PATH)
_harness = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_harness)

app_with_noop_lifespan = _harness.app_with_noop_lifespan
collect_paths = _harness.collect_paths
get_middleware_names = _harness.get_middleware_names


def _app_with_noop_lifespan(monkeypatch):
    return app_with_noop_lifespan(
        monkeypatch,
        "layer4_agents.api.app_factory.build_lifespan",
        create_app,
    )


def test_l4_middleware_registration_and_effective_wrapping_order(monkeypatch):
    app = _app_with_noop_lifespan(monkeypatch)

    middleware_names = get_middleware_names(app)
    # user_middleware is reverse-registration order (outermost first)
    assert middleware_names[:3] == [
        "CORSMiddleware",
        "SecurityMiddleware",
        "GovernanceMiddleware",
    ]


def test_l4_health_and_metrics_route_contract_presence(monkeypatch):
    app = _app_with_noop_lifespan(monkeypatch)

    paths = collect_paths(app.routes)
    assert "/health" in paths
    assert "/metrics" in paths


def test_l4_health_and_metrics_response_contract(monkeypatch):
    app = _app_with_noop_lifespan(monkeypatch)

    with TestClient(app) as client:
        health = client.get("/health")
        assert health.status_code == 200
        payload = health.json()
        assert payload["status"] == "ok"
        assert payload["service"] == "layer4-agents"
        assert "timestamp" in payload

        metrics = client.get("/metrics")
        assert metrics.status_code in {200, 403, 503}
        assert metrics.headers["content-type"].startswith("text/plain")
