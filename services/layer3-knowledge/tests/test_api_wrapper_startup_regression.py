from api.main import app


def test_wrapper_main_exposes_fastapi_app() -> None:
    assert app is not None


def test_wrapper_routes_registered() -> None:
    paths = {route.path for route in app.routes}
    assert "/health" in paths
    assert any(path.startswith("/api/v1") for path in paths)
