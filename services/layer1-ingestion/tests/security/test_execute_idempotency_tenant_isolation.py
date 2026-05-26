from uuid import UUID

from fastapi import Request
from fastapi.testclient import TestClient
from starlette.middleware.base import BaseHTTPMiddleware

from value_fabric.layer1.api.app_monolith import app
from value_fabric.layer1.shared.database import get_db_from_context_sync
from value_fabric.layer1.shared.models import ScrapingJob, create_scraping_target


class _Ctx:
    def __init__(self, tenant_id: UUID, user_id: UUID):
        self.tenant_id = tenant_id
        self.user_id = str(user_id)
        self.roles = ["admin"]


class _InjectCtx(BaseHTTPMiddleware):
    def __init__(self, wrapped_app, tenant_id: UUID, user_id: UUID):
        super().__init__(wrapped_app)
        self._tenant_id = tenant_id
        self._user_id = user_id

    async def dispatch(self, request: Request, call_next):
        request.state.governance_context = _Ctx(self._tenant_id, self._user_id)
        return await call_next(request)


def test_duplicate_idempotency_key_different_tenants_get_distinct_jobs(db, org_id, other_org_id, user_id, monkeypatch):
    target_a = create_scraping_target(tenant_id=org_id, name="A", url="https://a.com", source_category="general", extraction_config={})
    target_b = create_scraping_target(tenant_id=other_org_id, name="B", url="https://b.com", source_category="general", extraction_config={})
    db.add_all([target_a, target_b])
    db.commit()

    app.dependency_overrides[get_db_from_context_sync] = lambda: db
    monkeypatch.setattr("value_fabric.layer1.api.app_monolith.process_scraping_job.delay", lambda *a, **k: None)

    with TestClient(_InjectCtx(app, tenant_id=org_id, user_id=user_id)) as client_a:
        r1 = client_a.post(f"/api/v1/ingestion/targets/{target_a.id}/execute", json={"idempotency_key": "shared-key"})
    with TestClient(_InjectCtx(app, tenant_id=other_org_id, user_id=user_id)) as client_b:
        r2 = client_b.post(f"/api/v1/ingestion/targets/{target_b.id}/execute", json={"idempotency_key": "shared-key"})

    assert r1.status_code == 202
    assert r2.status_code == 202
    assert r1.json()["job_id"] != r2.json()["job_id"]
    assert db.query(ScrapingJob).filter(ScrapingJob.idempotency_key == "shared-key").count() == 2
    app.dependency_overrides.clear()
