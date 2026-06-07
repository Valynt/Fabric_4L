from src.api.main import app


def test_layer3_entrypoint_exposes_expected_routes() -> None:
    paths = {route.path for route in app.routes}
    expected = {
        "/health",
        "/api/v1/query/search",
        "/api/v1/entities",
        "/api/v1/system/health",
    }
    assert expected.issubset(paths)
