from __future__ import annotations

from contextlib import asynccontextmanager

from value_fabric.layer4.api.app_factory import create_app


def _app_with_noop_lifespan(monkeypatch):
    @asynccontextmanager
    async def _noop_lifespan(app):
        yield

    monkeypatch.setattr(
        "value_fabric.layer4.api.app_factory.build_lifespan",
        lambda **_: _noop_lifespan,
    )
    return create_app()


def test_l4_middleware_registration_and_effective_wrapping_order(monkeypatch):
    app = _app_with_noop_lifespan(monkeypatch)

    middleware_names = [mw.cls.__name__ for mw in app.user_middleware]
    # user_middleware is reverse-registration order (outermost first)
    assert middleware_names[:4] == [
        "CORSMiddleware",
        "MetricsMiddleware",
        "SecurityMiddleware",
        "GovernanceMiddleware",
    ]


def test_l4_health_and_metrics_route_contract_presence(monkeypatch):
    app = _app_with_noop_lifespan(monkeypatch)

    paths = {route.path for route in app.routes}
    assert "/health" in paths
    assert "/metrics" in paths
