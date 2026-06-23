"""Tenant isolation tests — updated for JWT-authenticated requests."""

from fastapi.testclient import TestClient

from app.main import app

from .conftest import TENANT_ALPHA, TENANT_BETA, auth_headers


def test_cross_tenant_access_blocked():
    """A resource owned by tenant-alpha must not be visible to tenant-beta."""
    with TestClient(app) as client:
        alpha = auth_headers(TENANT_ALPHA)
        client.post(
            "/v1/accounts",
            json={"id": "acc-allego", "name": "Alpha Account", "industry": "Software", "tenant_id": TENANT_ALPHA},
            headers=alpha,
        )
        response = client.get("/v1/accounts/acc-allego", headers=alpha)
        assert response.status_code == 200

        beta = auth_headers(TENANT_BETA)
        response = client.get("/v1/accounts/acc-allego", headers=beta)
        assert response.status_code == 404


def test_missing_credentials_returns_401():
    """Requests with no credentials must be rejected."""
    with TestClient(app) as client:
        response = client.get("/v1/accounts")
        assert response.status_code == 401


def test_tenant_header_without_jwt_returns_401():
    """X-Tenant-ID alone (no JWT) must not grant access."""
    with TestClient(app) as client:
        response = client.get("/v1/accounts", headers={"X-Tenant-ID": TENANT_ALPHA})
        assert response.status_code == 401


def test_tenant_a_cannot_insert_row_for_tenant_b_from_payload():
    """Authenticated tenant context wins over a forged body tenant_id."""
    with TestClient(app) as client:
        payload = {
            "id": "acc-forged-insert-beta",
            "name": "Forged Beta Insert",
            "industry": "Software",
            "tenant_id": TENANT_BETA,
        }
        response = client.post("/v1/accounts", json=payload, headers=auth_headers(TENANT_ALPHA))
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "TENANT_CONTEXT_MISMATCH"

        beta_read = client.get("/v1/accounts/acc-forged-insert-beta", headers=auth_headers(TENANT_BETA))
        assert beta_read.status_code == 404


def test_tenant_a_cannot_update_tenant_b_row_even_with_tenant_b_in_payload():
    """Tenant predicates must use authenticated context, not request payload."""
    with TestClient(app) as client:
        beta_headers = auth_headers(TENANT_BETA)
        create_response = client.post(
            "/v1/accounts",
            json={
                "id": "acc-beta-update-guard",
                "name": "Original Beta",
                "industry": "Software",
                "tenant_id": TENANT_BETA,
            },
            headers=beta_headers,
        )
        assert create_response.status_code == 201

        forged_update = client.patch(
            "/v1/accounts/acc-beta-update-guard",
            json={"tenant_id": TENANT_BETA, "name": "Forged Alpha Update"},
            headers=auth_headers(TENANT_ALPHA),
        )
        assert forged_update.status_code == 404

        beta_read = client.get("/v1/accounts/acc-beta-update-guard", headers=beta_headers)
        assert beta_read.status_code == 200
        assert beta_read.json()["name"] == "Original Beta"


def test_tenant_a_cannot_read_tenant_b_row_even_with_tenant_b_in_payload():
    """A forged body tenant_id must not widen read scope."""
    with TestClient(app) as client:
        beta_headers = auth_headers(TENANT_BETA)
        create_response = client.post(
            "/v1/accounts",
            json={
                "id": "acc-beta-read-guard",
                "name": "Beta Read Guard",
                "industry": "Software",
                "tenant_id": TENANT_BETA,
            },
            headers=beta_headers,
        )
        assert create_response.status_code == 201

        forged_read = client.request(
            "GET",
            "/v1/accounts/acc-beta-read-guard",
            json={"tenant_id": TENANT_BETA},
            headers=auth_headers(TENANT_ALPHA),
        )
        assert forged_read.status_code == 404
