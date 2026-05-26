from fastapi.testclient import TestClient

from app.main import app
from app.tests.conftest import auth_headers


client = TestClient(app)
HEADERS = auth_headers()


def test_canonical_intelligence_routes_use_accounts_prefix():
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
    response = client.get('/v1/intelligence/account/acc-allego/signals', headers=HEADERS)
    assert response.status_code == 200

    response = client.get('/v1/intelligence/account/acc-allego/stakeholders', headers=HEADERS)
    assert response.status_code == 200

    response = client.get('/v1/intelligence/account/acc-allego/ontology-match', headers=HEADERS)
    assert response.status_code == 200

    response = client.get('/v1/intelligence/account/acc-allego/enrichment', headers=HEADERS)
    assert response.status_code == 200
