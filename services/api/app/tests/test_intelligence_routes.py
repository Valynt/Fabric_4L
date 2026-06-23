import pytest
from fastapi.testclient import TestClient
from value_fabric.shared.identity.context import RequestContext, RequestContextManager

from app.core.database import db
from app.main import app
from app.models.schemas import Account, Signal
from app.tests.conftest import TENANT_ALPHA, auth_headers

client = TestClient(app)
HEADERS = auth_headers()

TEST_ACCOUNT_ID = "acc-allego"
TEST_OTHER_ACCOUNT_ID = "other-account"


@pytest.fixture(autouse=True)
def _seed_test_account(_reset_lazy_db):
    """Seed acc-allego for the canonical tenant so account-scoped routes resolve."""
    ctx = RequestContext(tenant_id=TENANT_ALPHA, auth_source="jwt_claim")
    with RequestContextManager(ctx):
        db.accounts.insert(
            TEST_ACCOUNT_ID,
            Account(
                id=TEST_ACCOUNT_ID,
                tenant_id=TENANT_ALPHA,
                name="Allegro Dynamics",
                industry="Software",
                value_pack_id=None,
            ),
        )
    yield


def test_canonical_intelligence_routes_use_accounts_prefix():
    response = client.get(f"/v1/accounts/{TEST_ACCOUNT_ID}/signals", headers=HEADERS)
    assert response.status_code == 200
    assert "items" in response.json()

    response = client.get(
        f"/v1/accounts/{TEST_ACCOUNT_ID}/stakeholders", headers=HEADERS
    )
    assert response.status_code == 200
    assert "items" in response.json()

    response = client.get(
        f"/v1/accounts/{TEST_ACCOUNT_ID}/ontology-match", headers=HEADERS
    )
    assert response.status_code == 200
    assert {"account_id", "matched_pack", "confidence", "gaps"} <= set(
        response.json().keys()
    )

    response = client.get(f"/v1/accounts/{TEST_ACCOUNT_ID}/enrichment", headers=HEADERS)
    assert response.status_code == 200
    assert {"account_id", "firmographics", "tech_stack", "public_sources"} <= set(
        response.json().keys()
    )


def test_legacy_intelligence_routes_are_supported_as_aliases():
    response = client.get(
        f"/v1/intelligence/account/{TEST_ACCOUNT_ID}/signals", headers=HEADERS
    )
    assert response.status_code == 200

    response = client.get(
        f"/v1/intelligence/account/{TEST_ACCOUNT_ID}/stakeholders", headers=HEADERS
    )
    assert response.status_code == 200

    response = client.get(
        f"/v1/intelligence/account/{TEST_ACCOUNT_ID}/ontology-match", headers=HEADERS
    )
    assert response.status_code == 200

    response = client.get(
        f"/v1/intelligence/account/{TEST_ACCOUNT_ID}/enrichment", headers=HEADERS
    )
    assert response.status_code == 200


def _sample_signal() -> Signal:
    return Signal(
        id="sig-test-001",
        account_id=TEST_ACCOUNT_ID,
        tenant_id=TENANT_ALPHA,
        title="Test signal",
    )


def test_legacy_intelligence_signal_extract_creates_signal():
    response = client.post(
        f"/v1/intelligence/account/{TEST_ACCOUNT_ID}/signals/extract",
        headers=HEADERS,
        json=_sample_signal().model_dump(mode="json"),
    )
    assert response.status_code == 201
    data = response.json()
    assert data["id"] == "sig-test-001"
    assert data["account_id"] == TEST_ACCOUNT_ID
    assert data["tenant_id"] == TENANT_ALPHA


def test_canonical_intelligence_routes_require_authorization():
    # Missing Authorization header must fail with 401 on every canonical route.
    no_auth_headers = {"X-Tenant-ID": HEADERS["X-Tenant-ID"]}

    response = client.get(
        f"/v1/accounts/{TEST_ACCOUNT_ID}/signals", headers=no_auth_headers
    )
    assert response.status_code == 401

    response = client.post(
        f"/v1/accounts/{TEST_ACCOUNT_ID}/signals/extract",
        headers=no_auth_headers,
        json=_sample_signal().model_dump(mode="json"),
    )
    assert response.status_code == 401

    response = client.get(
        f"/v1/accounts/{TEST_ACCOUNT_ID}/stakeholders", headers=no_auth_headers
    )
    assert response.status_code == 401

    response = client.get(
        f"/v1/accounts/{TEST_ACCOUNT_ID}/ontology-match", headers=no_auth_headers
    )
    assert response.status_code == 401

    response = client.get(
        f"/v1/accounts/{TEST_ACCOUNT_ID}/enrichment", headers=no_auth_headers
    )
    assert response.status_code == 401


def test_canonical_intelligence_routes_require_account_scope():
    # Token scoped to a different account must be rejected with 403.
    scoped_headers = auth_headers(
        extra_claims={
            "account_ids": [TEST_OTHER_ACCOUNT_ID],
            "account_id": TEST_OTHER_ACCOUNT_ID,
        }
    )

    response = client.get(
        f"/v1/accounts/{TEST_ACCOUNT_ID}/signals", headers=scoped_headers
    )
    assert response.status_code == 403

    response = client.post(
        f"/v1/accounts/{TEST_ACCOUNT_ID}/signals/extract",
        headers=scoped_headers,
        json=_sample_signal().model_dump(mode="json"),
    )
    assert response.status_code == 403

    response = client.get(
        f"/v1/accounts/{TEST_ACCOUNT_ID}/stakeholders", headers=scoped_headers
    )
    assert response.status_code == 403

    response = client.get(
        f"/v1/accounts/{TEST_ACCOUNT_ID}/ontology-match", headers=scoped_headers
    )
    assert response.status_code == 403

    response = client.get(
        f"/v1/accounts/{TEST_ACCOUNT_ID}/enrichment", headers=scoped_headers
    )
    assert response.status_code == 403


def test_legacy_intelligence_routes_require_authorization():
    # Missing Authorization header must fail with 401 on every legacy route.
    no_auth_headers = {"X-Tenant-ID": HEADERS["X-Tenant-ID"]}

    response = client.get(
        f"/v1/intelligence/account/{TEST_ACCOUNT_ID}/signals", headers=no_auth_headers
    )
    assert response.status_code == 401

    response = client.post(
        f"/v1/intelligence/account/{TEST_ACCOUNT_ID}/signals/extract",
        headers=no_auth_headers,
        json=_sample_signal().model_dump(mode="json"),
    )
    assert response.status_code == 401

    response = client.get(
        f"/v1/intelligence/account/{TEST_ACCOUNT_ID}/stakeholders",
        headers=no_auth_headers,
    )
    assert response.status_code == 401

    response = client.get(
        f"/v1/intelligence/account/{TEST_ACCOUNT_ID}/ontology-match",
        headers=no_auth_headers,
    )
    assert response.status_code == 401

    response = client.get(
        f"/v1/intelligence/account/{TEST_ACCOUNT_ID}/enrichment",
        headers=no_auth_headers,
    )
    assert response.status_code == 401


def test_legacy_intelligence_routes_require_account_scope():
    # Token scoped to a different account must be rejected with 403.
    scoped_headers = auth_headers(
        extra_claims={
            "account_ids": [TEST_OTHER_ACCOUNT_ID],
            "account_id": TEST_OTHER_ACCOUNT_ID,
        }
    )

    response = client.get(
        f"/v1/intelligence/account/{TEST_ACCOUNT_ID}/signals", headers=scoped_headers
    )
    assert response.status_code == 403

    response = client.post(
        f"/v1/intelligence/account/{TEST_ACCOUNT_ID}/signals/extract",
        headers=scoped_headers,
        json=_sample_signal().model_dump(mode="json"),
    )
    assert response.status_code == 403

    response = client.get(
        f"/v1/intelligence/account/{TEST_ACCOUNT_ID}/stakeholders",
        headers=scoped_headers,
    )
    assert response.status_code == 403

    response = client.get(
        f"/v1/intelligence/account/{TEST_ACCOUNT_ID}/ontology-match",
        headers=scoped_headers,
    )
    assert response.status_code == 403

    response = client.get(
        f"/v1/intelligence/account/{TEST_ACCOUNT_ID}/enrichment", headers=scoped_headers
    )
    assert response.status_code == 403


def test_cross_tenant_intelligence_access_is_denied_for_both_prefixes(
    beta_headers: dict[str, str],
):
    # TENANT_BETA requests an account owned by TENANT_ALPHA must fail with 403.
    beta = beta_headers

    response = client.get(f"/v1/accounts/{TEST_ACCOUNT_ID}/signals", headers=beta)
    assert response.status_code == 403

    response = client.get(
        f"/v1/intelligence/account/{TEST_ACCOUNT_ID}/signals", headers=beta
    )
    assert response.status_code == 403

    response = client.post(
        f"/v1/accounts/{TEST_ACCOUNT_ID}/signals/extract",
        headers=beta,
        json=_sample_signal().model_dump(mode="json"),
    )
    assert response.status_code == 403

    response = client.post(
        f"/v1/intelligence/account/{TEST_ACCOUNT_ID}/signals/extract",
        headers=beta,
        json=_sample_signal().model_dump(mode="json"),
    )
    assert response.status_code == 403

    response = client.get(f"/v1/accounts/{TEST_ACCOUNT_ID}/stakeholders", headers=beta)
    assert response.status_code == 403

    response = client.get(
        f"/v1/intelligence/account/{TEST_ACCOUNT_ID}/stakeholders", headers=beta
    )
    assert response.status_code == 403

    response = client.get(
        f"/v1/accounts/{TEST_ACCOUNT_ID}/ontology-match", headers=beta
    )
    assert response.status_code == 403

    response = client.get(
        f"/v1/intelligence/account/{TEST_ACCOUNT_ID}/ontology-match", headers=beta
    )
    assert response.status_code == 403

    response = client.get(f"/v1/accounts/{TEST_ACCOUNT_ID}/enrichment", headers=beta)
    assert response.status_code == 403

    response = client.get(
        f"/v1/intelligence/account/{TEST_ACCOUNT_ID}/enrichment", headers=beta
    )
    assert response.status_code == 403
