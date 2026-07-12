from types import SimpleNamespace

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from value_fabric.shared.rate_limiting.admin_api import get_rate_limiter
from value_fabric.shared.rate_limiting.tenant_rate_limiter import TenantRateLimiter


@pytest.mark.asyncio
async def test_get_rate_limiter_returns_configured_instance() -> None:
    app = SimpleNamespace(state=SimpleNamespace(tenant_rate_limiter=TenantRateLimiter(redis_client=object())))
    request = SimpleNamespace(app=app)
    limiter = await get_rate_limiter(request)  # type: ignore[arg-type]
    assert isinstance(limiter, TenantRateLimiter)


def test_get_rate_limiter_returns_structured_503_contract() -> None:
    app = FastAPI()

    @app.get('/probe')
    async def probe(limiter: TenantRateLimiter = Depends(get_rate_limiter)):
        return {'ok': limiter is not None}

    client = TestClient(app)
    response = client.get('/probe')
    assert response.status_code == 503
    body = response.json()
    assert body['detail']['code'] == 'RATE_LIMITER_UNAVAILABLE'
    assert 'not configured' in body['detail']['message']
    assert 'remediation' in body['detail']
