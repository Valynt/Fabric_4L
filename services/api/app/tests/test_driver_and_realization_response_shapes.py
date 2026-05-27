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


def test_create_realization_plan_missing_required_fields_returns_422_with_field_locations():
    response = client.post('/v1/accounts/acc-allego/realization-plans', json={}, headers=HEADERS)
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert isinstance(detail, list)
    assert any(err.get("loc") == ["body", "id"] for err in detail)
    assert any(err.get("loc") == ["body", "scenario_id"] for err in detail)


def test_create_realization_plan_invalid_types_and_constraints_return_422():
    payload = {
        "id": "roi-invalid-1",
        "scenario_id": "scenario-invalid",
        "revenue_uplift": "high",
        "solution_cost": -5,
    }
    response = client.post('/v1/accounts/acc-allego/realization-plans', json=payload, headers=HEADERS)
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert isinstance(detail, list)
    assert any(err.get("loc") == ["body", "revenue_uplift"] for err in detail)
    assert any(err.get("loc") == ["body", "solution_cost"] for err in detail)


def test_patch_realization_actuals_malformed_payload_returns_422():
    seed_payload = {
        "id": "roi-invalid-actuals",
        "scenario_id": "scenario-actuals",
        "revenue_uplift": 100,
    }
    seed_response = client.post('/v1/accounts/acc-allego/realization-plans', json=seed_payload, headers=HEADERS)
    assert seed_response.status_code == 200

    patch_payload = {
        "calculation_trace": "not-a-list",
        "payback_months": -1,
    }
    response = client.patch(
        '/v1/accounts/acc-allego/realization-plans/roi-invalid-actuals/actuals',
        json=patch_payload,
        headers=HEADERS,
    )
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert isinstance(detail, list)
    assert any(err.get("loc") == ["body", "calculation_trace"] for err in detail)
    assert any(err.get("loc") == ["body", "payback_months"] for err in detail)
