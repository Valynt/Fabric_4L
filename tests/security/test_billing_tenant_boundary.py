import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.append(str(Path(__file__).resolve().parents[2] / "services/layer7-billing/src"))
from layer7_billing.api.main import app


def _headers(tenant: str, actor: str = "tester", roles: str = "billing:read,billing:write") -> dict[str, str]:
    return {"x-tenant-id": tenant, "x-actor": actor, "x-roles": roles}


def test_tenant_a_cannot_read_tenant_b_usage() -> None:
    client = TestClient(app)
    client.post("/v1/billing/usage-events", headers=_headers("tenant-b"), json={"event_id": "evt-b-1", "metric": "jobs", "quantity": 3, "source": "api", "timestamp": "2026-05-26T00:00:00Z", "request_id": "req-b-1"})
    tenant_a = client.get("/v1/billing/usage-aggregates", headers=_headers("tenant-a")).json()
    assert tenant_a["metrics"].get("jobs") in (None, 0)


def test_rbac_enforced_for_mutation() -> None:
    client = TestClient(app)
    resp = client.post("/v1/billing/plans", headers=_headers("tenant-a", roles="billing:read"), json={"plan_id": "starter", "name": "Starter", "entitlements": []})
    assert resp.status_code == 403
