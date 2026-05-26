"""Account endpoint tests — updated for JWT-authenticated requests."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.schemas import AccountUpdateRequest

from .conftest import TENANT_ALPHA, TENANT_BETA, auth_headers

HEADERS = auth_headers(TENANT_ALPHA)


def test_list_accounts():
    with TestClient(app) as client:
        response = client.get("/v1/accounts", headers=HEADERS)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data


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


def test_account_summary_and_share_responses_are_typed():
    with TestClient(app) as client:
        summary = client.get("/v1/accounts/acc-allego/summary", headers=HEADERS)
        assert summary.status_code == 200
        summary_data = summary.json()
        assert set(summary_data.keys()) == {
            "account",
            "signal_count",
            "hypothesis_count",
            "roi_calculation_count",
        }
        assert summary_data["account"]["id"] == "acc-allego"

        share = client.post("/v1/accounts/acc-allego/share", headers=HEADERS)
        assert share.status_code == 200
        share_data = share.json()
        assert "share_token" in share_data
        assert share_data["account_id"] == "acc-allego"
        assert share_data["role"] == "read_only"

        revoke = client.delete("/v1/accounts/acc-allego/share", headers=HEADERS)
        assert revoke.status_code == 200
        assert revoke.json() == {"revoked": True, "account_id": "acc-allego"}


def test_patch_account_invalid_type_returns_422_with_field_location():
    with TestClient(app) as client:
        response = client.patch(
            "/v1/accounts/acc-allego",
            json={"employee_count": "many"},
            headers=HEADERS,
        )
        assert response.status_code == 422
        detail = response.json()["detail"]
        assert isinstance(detail, list)
        assert any(err.get("loc") == ["body", "employee_count"] for err in detail)


def test_patch_account_constraint_violation_returns_422_with_field_location():
    with TestClient(app) as client:
        response = client.patch(
            "/v1/accounts/acc-allego",
            json={"annual_revenue": -1},
            headers=HEADERS,
        )
        assert response.status_code == 422
        detail = response.json()["detail"]
        assert isinstance(detail, list)
        assert any(err.get("loc") == ["body", "annual_revenue"] for err in detail)


def test_patch_account_missing_required_field_returns_422_when_required_fields_exist():
    required_patch_fields = {
        field_name
        for field_name, field_info in AccountUpdateRequest.model_fields.items()
        if field_info.is_required()
    }
    if not required_patch_fields:
        pytest.skip("AccountUpdateRequest has no required fields to validate missing-field 422 behavior")

    missing_field = sorted(required_patch_fields)[0]
    with TestClient(app) as client:
        response = client.patch(
            "/v1/accounts/acc-allego",
            json={},
            headers=HEADERS,
        )
        assert response.status_code == 422
        detail = response.json()["detail"]
        assert isinstance(detail, list)
        assert any(err.get("loc") == ["body", missing_field] for err in detail)


def test_patch_account_unknown_field_returns_422_when_extras_forbidden():
    extra_mode = AccountUpdateRequest.model_config.get("extra")
    if extra_mode != "forbid":
        pytest.skip("AccountUpdateRequest extras are not forbidden")

    with TestClient(app) as client:
        response = client.patch(
            "/v1/accounts/acc-allego",
            json={"unknown_field": "unexpected"},
            headers=HEADERS,
        )
        assert response.status_code == 422
        detail = response.json()["detail"]
        assert isinstance(detail, list)
        assert any(err.get("loc") == ["body", "unknown_field"] for err in detail)
