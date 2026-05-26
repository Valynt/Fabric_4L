import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.append(str(Path(__file__).resolve().parents[2] / "services/layer7-billing/src"))
from layer7_billing.api.main import app


def _headers(tenant: str, actor: str = "tester", roles: str = "billing:read,billing:write") -> dict[str, str]:
    return {"x-tenant-id": tenant, "x-actor": actor, "x-roles": roles}


def test_entitlement_contract_and_single_decision_api() -> None:
    client = TestClient(app)
    client.post("/v1/billing/plans", headers=_headers("tenant-a"), json={"plan_id": "pro", "name": "Pro", "entitlements": ["feature.alpha"]})
    resp = client.get("/v1/billing/entitlements/pro/decision", headers=_headers("tenant-a"), params={"feature": "feature.alpha"})
    body = resp.json()
    assert resp.status_code == 200
    assert body["allowed"] is True
    assert body["policy"] == "runtime-entitlement-api-v1"


def test_usage_event_append_only_and_idempotent_aggregate() -> None:
    client = TestClient(app)
    payload = {"event_id": "evt-1", "metric": "tokens", "quantity": 10, "source": "layer4", "timestamp": "2026-05-26T00:00:00Z", "request_id": "req-1"}
    first = client.post("/v1/billing/usage-events", headers=_headers("tenant-a"), json=payload)
    second = client.post("/v1/billing/usage-events", headers=_headers("tenant-a"), json=payload)
    assert first.status_code == 200
    assert second.json()["status"] == "duplicate"
    agg = client.get("/v1/billing/usage-aggregates", headers=_headers("tenant-a")).json()
    assert agg["metrics"]["tokens"] == 10
