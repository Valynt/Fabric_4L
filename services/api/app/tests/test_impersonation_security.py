from fastapi.testclient import TestClient

from app.core.database import db
from app.core.security import create_access_token
from app.main import app
from app.models.schemas import User

TENANT_A = "11111111-1111-4111-8111-111111111111"
TENANT_B = "22222222-2222-4222-8222-222222222222"


def _auth(token: str, tenant_id: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id}


def test_unauthorized_impersonation_fails_closed() -> None:
    with TestClient(app) as client:
        user = User(id="analyst-a", tenant_id=TENANT_A, email="a@test.com", name="A", role="analyst", status="active")
        target = User(id="target-a", tenant_id=TENANT_A, email="t@test.com", name="T", role="read_only", status="active")
        db.users.insert(user.id, user)
        db.users.insert(target.id, target)
        token = create_access_token(subject=user.id, tenant_id=TENANT_A)
        res = client.post("/v1/auth/impersonation/start", json={"target_user_id": target.id, "reason": "support"}, headers=_auth(token, TENANT_A))
        assert res.status_code == 403


def test_impersonation_audit_and_tenant_boundary() -> None:
    with TestClient(app) as client:
        admin = User(id="admin-a", tenant_id=TENANT_A, email="admin@test.com", name="Admin", role="tenant_admin", status="active")
        target = User(id="target-a", tenant_id=TENANT_A, email="t@test.com", name="T", role="read_only", status="active")
        other_tenant_user = User(id="other-b", tenant_id=TENANT_B, email="b@test.com", name="B", role="read_only", status="active")
        db.users.insert(admin.id, admin)
        db.users.insert(target.id, target)
        db.users.insert(other_tenant_user.id, other_tenant_user)

        admin_token = create_access_token(subject=admin.id, tenant_id=TENANT_A)
        deny = client.post("/v1/auth/impersonation/start", json={"target_user_id": other_tenant_user.id, "reason": "support"}, headers=_auth(admin_token, TENANT_A))
        assert deny.status_code == 404

        start = client.post("/v1/auth/impersonation/start", json={"target_user_id": target.id, "reason": "support", "notify_email": True}, headers=_auth(admin_token, TENANT_A))
        assert start.status_code == 200
        body = start.json()
        imp_token = body["access_token"]
        stop = client.post("/v1/auth/impersonation/stop", headers=_auth(imp_token, TENANT_A))
        assert stop.status_code == 204

        logs = db.audit_logs.list(tenant_id=TENANT_A)
        actions = [entry.action for entry in logs if entry.action.startswith("impersonation.")]
        assert "impersonation.start" in actions
        assert "impersonation.stop" in actions
        for entry in logs:
            if entry.action.startswith("impersonation."):
                assert entry.payload is not None
                assert entry.payload.get("impersonated_by")
                assert entry.payload.get("tenant_notifications", {}).get("in_app") is True
