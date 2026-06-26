from uuid import uuid4

from fastapi import Request
from value_fabric.shared.identity.context import RequestContext

from app.core.usage_meter import record_usage


def _mock_request(path: str = "/v1/benchmarks", method: str = "GET") -> Request:
    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "headers": [],
        "query_string": b"",
    }
    return Request(scope)


def test_record_usage_persists_event():
    tenant_id = str(uuid4())
    ctx = RequestContext(tenant_id=tenant_id, source="api_key", api_key_id="vf_key_123")
    request = _mock_request()
    event = record_usage(request=request, ctx=ctx, product_code="benchmarks")
    assert event.tenant_id == tenant_id
    assert event.product_code == "benchmarks"
    assert event.quantity == 1.0
    assert event.api_key_id == "vf_key_123"
