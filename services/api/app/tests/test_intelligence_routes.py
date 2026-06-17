from fastapi.testclient import TestClient

from app.main import app
from app.tests.conftest import TENANT_ALPHA, auth_headers


client = TestClient(app)
HEADERS = auth_headers()


def _ensure_account() -> None:
    """Create the test account used by ontology/enrichment routes."""
    account = {
        "id": "acc-allego",
        "tenant_id": TENANT_ALPHA,
        "name": "Allego",
        "industry": "Software",
    }
    resp = client.post("/v1/accounts", json=account, headers=HEADERS)
    # 201 on first creation; allow 200/201/409 for idempotent test runs.
    assert resp.status_code in {200, 201, 409}


def test_canonical_intelligence_routes_use_accounts_prefix():
    _ensure_account()

    response = client.get('/v1/accounts/acc-allego/signals', headers=HEADERS)
    assert response.status_code == 200
    assert "items" in response.json()

    response = client.get('/v1/accounts/acc-allego/stakeholders', headers=HEADERS)
    assert response.status_code == 200
    assert "items" in response.json()

    response = client.get('/v1/accounts/acc-allego/ontology-match', headers=HEADERS)
    assert response.status_code == 200
    assert {"account_id", "matched_pack", "confidence", "gaps"} <= set(response.json().keys())

    response = client.get('/v1/accounts/acc-allego/enrichment', headers=HEADERS)
    assert response.status_code == 200
    assert {"account_id", "firmographics", "tech_stack", "public_sources"} <= set(response.json().keys())


def test_legacy_intelligence_routes_are_supported_as_aliases():
    _ensure_account()

    response = client.get('/v1/intelligence/account/acc-allego/signals', headers=HEADERS)
    assert response.status_code == 200

    response = client.get('/v1/intelligence/account/acc-allego/stakeholders', headers=HEADERS)
    assert response.status_code == 200

    response = client.get('/v1/intelligence/account/acc-allego/ontology-match', headers=HEADERS)
    assert response.status_code == 200

    response = client.get('/v1/intelligence/account/acc-allego/enrichment', headers=HEADERS)
    assert response.status_code == 200
