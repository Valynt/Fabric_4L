from fastapi.testclient import TestClient

from app.core.database import db
from app.main import app
from app.models.schemas import Account, User
from app.routers.accounts import get_share_link_repo
from app.routers.auth import get_impersonation_repo
from app.services.distributed_store import StoreUnavailableError
from app.core.security import create_access_token


def test_share_link_store_unavailable_returns_503(auth_headers):
    class BrokenShareRepo:
        def create(self, **kwargs):
            raise StoreUnavailableError("down")

    app.dependency_overrides[get_share_link_repo] = lambda: BrokenShareRepo()
    try:
        db.accounts.insert("acc-store-fail", Account(id="acc-store-fail", tenant_id="tenant-alpha", name="x", industry="y"))
        with TestClient(app) as client:
            res = client.post("/v1/accounts/acc-store-fail/share", headers=auth_headers("tenant-alpha"))
            assert res.status_code == 503
    finally:
        app.dependency_overrides.pop(get_share_link_repo, None)


def test_impersonation_store_unavailable_fails_closed():
    class BrokenImpRepo:
        def create(self, **kwargs):
            raise StoreUnavailableError("down")

    app.dependency_overrides[get_impersonation_repo] = lambda: BrokenImpRepo()
    try:
        admin = User(id="admin-1", tenant_id="tenant-alpha", email="admin1@test.com", name="Admin", role="tenant_admin", status="active")
        target = User(id="target-1", tenant_id="tenant-alpha", email="target1@test.com", name="Target", role="read_only", status="active")
        db.users.insert(admin.id, admin)
        db.users.insert(target.id, target)
        token = create_access_token(subject=admin.id, tenant_id="tenant-alpha")
        with TestClient(app) as client:
            res = client.post("/v1/auth/impersonation/start", json={"target_user_id": target.id, "reason": "support"}, headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": "tenant-alpha"})
            assert res.status_code == 503
    finally:
        app.dependency_overrides.pop(get_impersonation_repo, None)
