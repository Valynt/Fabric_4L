from fastapi.testclient import TestClient

from app.main import app

from .conftest import TENANT_ALPHA, auth_headers

HEADERS = auth_headers(TENANT_ALPHA)


def test_review_queue():
    with TestClient(app) as client:
        response = client.get("/v1/governance/review-queue", headers=HEADERS)
        assert response.status_code == 200
        data = response.json()
        assert "hypotheses" in data
        assert "formulas" in data
        assert "evidence" in data


def test_prod_gates():
    with TestClient(app) as client:
        response = client.get("/v1/governance/prod-gates", headers=HEADERS)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert len(data["items"]) >= 1


def test_create_review_decision():
    with TestClient(app) as client:
        payload = {
            "id": "rd-test-1",
            "tenant_id": "tenant-alpha",
            "object_type": "hypothesis",
            "object_id": "hyp-1",
            "decision": "approve",
            "reason": "Validated with customer",
        }
        response = client.post("/v1/governance/review-decisions", json=payload, headers=HEADERS)
        assert response.status_code == 201
        data = response.json()
        assert data["decision"] == "approve"


def test_audit_log_returns_list_envelope():
    with TestClient(app) as client:
        response = client.get("/v1/governance/audit-log", headers=HEADERS)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert isinstance(data["items"], list)
