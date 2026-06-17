from fastapi.testclient import TestClient

from app.main import app
from app.tests.conftest import TENANT_ALPHA, auth_headers

client = TestClient(app)


def test_same_tenant_wrong_account_cannot_read_signals() -> None:
    allowed_headers = auth_headers(
        tenant_id=TENANT_ALPHA, extra_claims={"account_ids": ["acc-allowed"]}
    )

    ok = client.get("/v1/accounts/acc-allowed/signals", headers=allowed_headers)
    assert ok.status_code == 200

    denied = client.get("/v1/accounts/acc-forbidden/signals", headers=allowed_headers)
    assert denied.status_code == 403


def test_same_tenant_wrong_account_cannot_traverse_stakeholders() -> None:
    allowed_headers = auth_headers(
        tenant_id=TENANT_ALPHA, extra_claims={"account_ids": ["acc-allowed"]}
    )

    ok = client.get("/v1/accounts/acc-allowed/stakeholders", headers=allowed_headers)
    assert ok.status_code == 200

    denied = client.get(
        "/v1/accounts/acc-forbidden/stakeholders", headers=allowed_headers
    )
    assert denied.status_code == 403


def test_same_tenant_wrong_account_cannot_read_evidence() -> None:
    allowed_headers = auth_headers(
        tenant_id=TENANT_ALPHA, extra_claims={"account_ids": ["acc-allowed"]}
    )

    ok = client.get("/v1/accounts/acc-allowed/evidence", headers=allowed_headers)
    assert ok.status_code == 200

    denied = client.get("/v1/accounts/acc-forbidden/evidence", headers=allowed_headers)
    assert denied.status_code == 403
