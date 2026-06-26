from uuid import uuid4

from fastapi import Request
from value_fabric.shared.identity.context import RequestContext

from app.core.quota_service import QuotaService
from app.core.usage_meter import record_usage


def _mock_request():
    scope = {"type": "http", "method": "GET", "path": "/v1/benchmarks", "headers": [], "query_string": b""}
    return Request(scope)


def test_quota_unlimited_by_default():
    svc = QuotaService()
    tenant_id = str(uuid4())
    check = svc.check(tenant_id, "benchmarks")
    assert check["allowed"] is True
    assert check["limit"] == -1
    assert check["remaining"] is None


def test_quota_enforces_limit(monkeypatch):
    tenant_id = str(uuid4())
    monkeypatch.setenv("QUOTA_BENCHMARKS", "2")
    svc = QuotaService()

    ctx = RequestContext(tenant_id=tenant_id, source="api_key")
    req = _mock_request()
    record_usage(request=req, ctx=ctx, product_code="benchmarks")

    check = svc.check(tenant_id, "benchmarks", quantity=1.0)
    assert check["used"] == 1
    assert check["remaining"] == 1
    assert check["allowed"] is True

    record_usage(request=req, ctx=ctx, product_code="benchmarks")
    check = svc.check(tenant_id, "benchmarks", quantity=1.0)
    assert check["allowed"] is False
    assert check["remaining"] == 0
