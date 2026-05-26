"""Account endpoint tests — updated for JWT-authenticated requests."""

from fastapi.testclient import TestClient

from app.main import app

from .conftest import TENANT_ALPHA, TENANT_BETA, auth_headers

HEADERS = auth_headers(TENANT_ALPHA)


def test_list_accounts():
    with TestClient(app) as client:
        response = client.get("/v1/accounts", headers=HEADERS)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1


def test_get_account():
    with TestClient(app) as client:
        response = client.get("/v1/accounts/acc-allego", headers=HEADERS)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "acc-allego"
        assert data["tenant_id"] == TENANT_ALPHA


def test_get_account_not_found():
    with TestClient(app) as client:
        response = client.get("/v1/accounts/nonexistent", headers=HEADERS)
        assert response.status_code == 404


def test_create_account():
    with TestClient(app) as client:
        payload = {
            "id": "acc-test-1",
            "name": "Test Account",
            "industry": "Software",
            "tenant_id": TENANT_ALPHA,
        }
        response = client.post("/v1/accounts", json=payload, headers=HEADERS)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Account"


def test_unauthenticated_returns_401():
    with TestClient(app) as client:
        response = client.get("/v1/accounts")
        assert response.status_code == 401


def test_create_account_rejects_body_tenant_mismatch():
    with TestClient(app) as client:
        payload = {"id": "acc-test-mismatch", "name": "Mismatch", "industry": "Software", "tenant_id": TENANT_BETA}
        response = client.post("/v1/accounts", json=payload, headers=HEADERS)
        assert response.status_code == 403
        assert response.json()["detail"]["code"] == "TENANT_CONTEXT_MISMATCH"


def test_tenant_a_cannot_read_tenant_b_account():
    with TestClient(app) as client:
        beta_headers = auth_headers(TENANT_BETA)
        payload = {"id": "acc-test-beta-only", "name": "Beta", "industry": "Software", "tenant_id": TENANT_BETA}
        create_response = client.post("/v1/accounts", json=payload, headers=beta_headers)
        assert create_response.status_code == 201

        read_response = client.get("/v1/accounts/acc-test-beta-only", headers=HEADERS)
        assert read_response.status_code == 404


def test_update_account_rejects_malformed_payload_with_422():
    with TestClient(app) as client:
        response = client.patch(
            "/v1/accounts/acc-allego",
            json={"employee_count": -1},
            headers=HEADERS,
        )
        assert response.status_code == 422


def test_update_account_rejects_wrong_field_types_with_422():
    with TestClient(app) as client:
        response = client.patch(
            "/v1/accounts/acc-allego",
            json={"name": 123},
            headers=HEADERS,
        )
        assert response.status_code == 422


def test_openapi_accounts_patch_uses_typed_request_schema():
    with TestClient(app) as client:
        response = client.get("/openapi.json")
        assert response.status_code == 200
        openapi = response.json()
        schema_ref = (
            openapi["paths"]["/v1/accounts/{account_id}"]["patch"]["requestBody"]["content"][
                "application/json"
            ]["schema"]["$ref"]
        )
        assert schema_ref.endswith("/AccountUpdateRequest")
