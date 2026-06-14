from src.api.main import app


def test_layer3_entrypoint_exposes_expected_routes() -> None:
    paths = {route.path for route in app.routes}
    expected = {
        "/health",
        "/v1/entities/",
    }
    assert expected.issubset(paths)
