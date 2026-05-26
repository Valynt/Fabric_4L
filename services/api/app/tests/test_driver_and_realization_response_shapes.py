from fastapi.testclient import TestClient

from app.main import app
from app.tests.conftest import TENANT_ALPHA, auth_headers


client = TestClient(app)
HEADERS = auth_headers(TENANT_ALPHA)


def test_value_tree_has_typed_categories():
    response = client.get('/v1/accounts/acc-allego/value-tree', headers=HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert data["account_id"] == "acc-allego"
    assert set(data["categories"].keys()) == {"revenue_uplift", "cost_savings", "risk_reduction"}


def test_realization_list_and_variance_shape():
    list_response = client.get('/v1/accounts/acc-allego/realization-plans', headers=HEADERS)
    assert list_response.status_code == 200
    assert isinstance(list_response.json(), list)

    create_payload = {
        "id": "roi-shape-1",
        "scenario_id": "scenario-1",
        "revenue_uplift": 1000,
    }
    create_response = client.post('/v1/accounts/acc-allego/realization-plans', json=create_payload, headers=HEADERS)
    assert create_response.status_code == 200
    created = create_response.json()
    assert created["account_id"] == "acc-allego"
    assert created["tenant_id"] == TENANT_ALPHA

    variance_response = client.get('/v1/accounts/acc-allego/realization-plans/roi-shape-1/variance', headers=HEADERS)
    assert variance_response.status_code == 200
    variance = variance_response.json()
    assert set(variance.keys()) == {"plan_id", "projected", "actual", "variance"}


def test_realization_create_request_validation_errors():
    missing_required = client.post(
        '/v1/accounts/acc-allego/realization-plans',
        json={"revenue_uplift": 10},
        headers=HEADERS,
    )
    assert missing_required.status_code == 422
    missing_detail = missing_required.json()["detail"]
    assert any(err["loc"] == ["body", "id"] for err in missing_detail)
    assert any(err["loc"] == ["body", "scenario_id"] for err in missing_detail)

    invalid_types = client.post(
        '/v1/accounts/acc-allego/realization-plans',
        json={"id": "roi-invalid", "scenario_id": "s1", "revenue_uplift": "a lot"},
        headers=HEADERS,
    )
    assert invalid_types.status_code == 422
    invalid_detail = invalid_types.json()["detail"]
    assert any(err["loc"] == ["body", "revenue_uplift"] for err in invalid_detail)

    invalid_constraints = client.post(
        '/v1/accounts/acc-allego/realization-plans',
        json={"id": "roi-invalid2", "scenario_id": "s1", "cost_savings": -5},
        headers=HEADERS,
    )
    assert invalid_constraints.status_code == 422
    constraint_detail = invalid_constraints.json()["detail"]
    assert any(err["loc"] == ["body", "cost_savings"] for err in constraint_detail)


def test_realization_actuals_patch_rejects_malformed_payload():
    create_payload = {"id": "roi-patch-validation", "scenario_id": "scenario-1", "revenue_uplift": 1000}
    create_response = client.post('/v1/accounts/acc-allego/realization-plans', json=create_payload, headers=HEADERS)
    assert create_response.status_code == 200

    malformed = client.patch(
        '/v1/accounts/acc-allego/realization-plans/roi-patch-validation/actuals',
        json={"payback_months": "soon", "unexpected": 5},
        headers=HEADERS,
    )
    assert malformed.status_code == 422
    detail = malformed.json()["detail"]
    assert any(err["loc"] == ["body", "payback_months"] for err in detail)
    assert any(err["loc"] == ["body", "unexpected"] for err in detail)
