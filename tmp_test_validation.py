import sys
sys.path.insert(0, "services/layer1-ingestion/src")
sys.path.insert(0, "packages/shared/src")

from fastapi.testclient import TestClient
from starlette.middleware.base import BaseHTTPMiddleware
from uuid import UUID
from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.middleware import GovernanceMiddleware

async def _mock_check_rate_limit(self, request, ctx):
    return type("_MockResult", (), {"allowed": True})()
GovernanceMiddleware._check_rate_limit = _mock_check_rate_limit

from layer1_ingestion.api.app_monolith import app

class _InjectGovernanceMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        tid = UUID("11111111-1111-1111-1111-111111111111")
        uid = UUID("22222222-2222-2222-2222-222222222222")
        request.state.governance_context = RequestContext(
            tenant_id=tid, user_id=str(uid), roles=["admin"], auth_source="jwt_claim"
        )
        request.state.rate_limit_result = type("_MockResult", (), {"allowed": True})()
        request.state.rate_limit_config = type("_MockConfig", (), {"requests_per_minute": 1000, "scope": type("_Scope", (), {"value": "tenant"})})()
        return await call_next(request)

wrapped = _InjectGovernanceMiddleware(app)
with TestClient(wrapped) as c:
    resp = c.post("/api/v1/ingestion/jobs/batch", json={"operation": "execute", "target_ids": []}, headers={"X-Organization-ID": "11111111-1111-1111-1111-111111111111"})
    print("status:", resp.status_code)
    print("body:", resp.json())
