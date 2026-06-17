"""Tests for value-case CRUD, publish, and tenant isolation."""

from fastapi.testclient import TestClient

from app.main import app

_REQUIRED_CASE_KEYS = {"id", "account_id", "tenant_id", "title", "status", "value_case", "audit"}


def test_create_and_get_value_case(alpha_headers):
    payload = {
        "title": "Q3 Expansion",
        "value_case": {
            "inputs": {"account_name": "Acme"},
            "sections": [
                {
                    "id": "s1",
                    "type": "executive_summary",
                    "title": "Summary",
                    "content": "Expansion summary content",
                }
            ],
            "assumption_ids": ["a1"],
            "evidence_ids": ["e1"],
            "stakeholder_framing": [{"persona": "CFO"}],
            "claim_ids": ["c1"],
        },
    }
    with TestClient(app) as client:
        create_response = client.post(
            "/v1/accounts/acc-1/value-case", json=payload, headers=alpha_headers
        )
        assert create_response.status_code == 201
        created = create_response.json()
        assert _REQUIRED_CASE_KEYS.issubset(created.keys())
        case_id = created["id"]

        get_response = client.get(
            f"/v1/accounts/acc-1/value-cases/{case_id}", headers=alpha_headers
        )
        assert get_response.status_code == 200
        fetched = get_response.json()
        assert _REQUIRED_CASE_KEYS.issubset(fetched.keys())
        assert fetched["value_case"]["assumption_ids"] == ["a1"]


def test_tenant_isolation(alpha_headers, beta_headers):
    payload = {"title": "Secret", "value_case": {"inputs": {}, "sections": []}}
    with TestClient(app) as client:
        create_response = client.post(
            "/v1/accounts/acc-2/value-case", json=payload, headers=alpha_headers
        )
        assert create_response.status_code == 201
        case_id = create_response.json()["id"]

        get_response = client.get(
            f"/v1/accounts/acc-2/value-cases/{case_id}", headers=beta_headers
        )
        assert get_response.status_code == 404

        patch_response = client.patch(
            f"/v1/accounts/acc-2/value-cases/{case_id}",
            json={"title": "Hacked"},
            headers=beta_headers,
        )
        assert patch_response.status_code == 404


def test_cross_account_isolation_within_same_tenant(alpha_headers):
    payload = {"title": "Alpha One", "value_case": {"inputs": {}, "sections": []}}
    with TestClient(app) as client:
        create_response = client.post(
            "/v1/accounts/acc-alpha-1/value-case", json=payload, headers=alpha_headers
        )
        assert create_response.status_code == 201
        case_id = create_response.json()["id"]

        get_response = client.get(
            f"/v1/accounts/acc-alpha-2/value-cases/{case_id}", headers=alpha_headers
        )
        assert get_response.status_code == 404


def test_patch_value_case_happy_path(alpha_headers):
    payload = {"title": "Original Title", "value_case": {"inputs": {}, "sections": []}}
    with TestClient(app) as client:
        create_response = client.post(
            "/v1/accounts/acc-patch/value-case", json=payload, headers=alpha_headers
        )
        assert create_response.status_code == 201
        case_id = create_response.json()["id"]

        patch_response = client.patch(
            f"/v1/accounts/acc-patch/value-cases/{case_id}",
            json={"title": "Updated Title"},
            headers=alpha_headers,
        )
        assert patch_response.status_code == 200
        assert patch_response.json()["title"] == "Updated Title"


def test_publish_transition(alpha_headers):
    payload = {
        "title": "Draft to Publish",
        "value_case": {"inputs": {}, "sections": []},
    }
    with TestClient(app) as client:
        create_response = client.post(
            "/v1/accounts/acc-3/value-case", json=payload, headers=alpha_headers
        )
        assert create_response.status_code == 201
        created = create_response.json()
        assert created["status"] == "draft"
        case_id = created["id"]

        publish_response = client.post(
            f"/v1/accounts/acc-3/value-cases/{case_id}/publish",
            headers=alpha_headers,
        )
        assert publish_response.status_code == 200
        assert publish_response.json()["status"] == "published"


def test_list_value_cases_for_account(alpha_headers):
    with TestClient(app) as client:
        for i in range(2):
            payload = {
                "title": f"Case {i}",
                "value_case": {"inputs": {}, "sections": []},
            }
            response = client.post(
                "/v1/accounts/acc-list/value-case",
                json=payload,
                headers=alpha_headers,
            )
            assert response.status_code == 201

        list_response = client.get(
            "/v1/accounts/acc-list/value-cases", headers=alpha_headers
        )
        assert list_response.status_code == 200
        cases = list_response.json()
        assert len(cases) == 2
        for case in cases:
            assert _REQUIRED_CASE_KEYS.issubset(case.keys())
        updated_ats = [c["audit"]["updated_at"] for c in cases]
        assert updated_ats == sorted(updated_ats, reverse=True)


def test_create_value_case_unauthenticated():
    payload = {"title": "No Auth", "value_case": {"inputs": {}, "sections": []}}
    with TestClient(app) as client:
        response = client.post("/v1/accounts/acc-unauth/value-case", json=payload)
        assert response.status_code in {401, 403}
