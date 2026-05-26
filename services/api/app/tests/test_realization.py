from fastapi.testclient import TestClient

from app.main import app

from .conftest import TENANT_ALPHA, auth_headers

HEADERS = auth_headers(TENANT_ALPHA)


def test_create_realization_plan_rejects_missing_required_fields_with_422():
    with TestClient(app) as client:
        response = client.post(
            "/v1/accounts/acc-allego/realization-plans",
            json={"id": "plan-1"},
            headers=HEADERS,
        )
        assert response.status_code == 422


def test_update_realization_actuals_rejects_malformed_payload_with_422():
    with TestClient(app) as client:
        # Seed plan
        create_response = client.post(
            "/v1/accounts/acc-allego/realization-plans",
            json={"id": "plan-2", "scenario_id": "scenario-1", "total_benefit": 10},
            headers=HEADERS,
        )
        assert create_response.status_code == 200

        update_response = client.patch(
            "/v1/accounts/acc-allego/realization-plans/plan-2/actuals",
            json={"actual_benefit": "not-a-number"},
            headers=HEADERS,
        )
        assert update_response.status_code == 422


def test_openapi_realization_routes_use_typed_request_schemas():
    with TestClient(app) as client:
        response = client.get("/openapi.json")
        assert response.status_code == 200
        openapi = response.json()

        create_ref = (
            openapi["paths"]["/v1/accounts/{account_id}/realization-plans"]["post"]["requestBody"][
                "content"
            ]["application/json"]["schema"]["$ref"]
        )
        patch_ref = (
            openapi["paths"]["/v1/accounts/{account_id}/realization-plans/{plan_id}/actuals"]["patch"][
                "requestBody"
            ]["content"]["application/json"]["schema"]["$ref"]
        )
        assert create_ref.endswith("/RealizationPlanCreateRequest")
        assert patch_ref.endswith("/RealizationActualsUpdateRequest")
