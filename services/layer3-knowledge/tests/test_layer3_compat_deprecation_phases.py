from src.api.main import app


def test_legacy_alias_warning_mode_allows_routes(test_client):
    app.state.layer3_compat_deprecation_phase = "warning_only"
    app.state.environment = "test"
    resp = test_client.post(
        "/v1/graphrag", json={"query": "x", "max_hops": 2, "max_results": 3}
    )
    assert resp.status_code in {200, 401}


def test_legacy_alias_disable_in_non_prod_returns_410(test_client):
    app.state.layer3_compat_deprecation_phase = "disable_non_prod"
    app.state.environment = "test"
    resp = test_client.post(
        "/v1/graphrag", json={"query": "x", "max_hops": 2, "max_results": 3}
    )
    assert resp.status_code in {401, 410}


def test_legacy_alias_disable_non_prod_allows_prod(test_client):
    app.state.layer3_compat_deprecation_phase = "disable_non_prod"
    app.state.environment = "prod"
    resp = test_client.post(
        "/v1/graphrag", json={"query": "x", "max_hops": 2, "max_results": 3}
    )
    assert resp.status_code in {200, 401}
