
import httpx
import pytest
import respx

from app.clients.billing_publisher import BillingEventPublisher
from app.models.usage_event import UsageEventRecord


def test_billing_publisher_payload_uses_tenant_as_customer(monkeypatch):
    monkeypatch.setenv("SERVICE_AUTH_SECRET", "svc-secret")
    publisher = BillingEventPublisher(base_url="http://billing")
    event = UsageEventRecord(
        event_id="evt-1",
        tenant_id="tenant-a",
        api_key_id="key-1",
        endpoint="/v1/benchmarks",
        method="GET",
        product_code="benchmarks",
        quantity=1.0,
        unit="request",
    )
    payload = publisher._payload(event)
    assert payload["customer_id"] == "tenant-a"
    assert payload["metric_name"] == "benchmarks"
    assert payload["quantity"] == 1.0


@pytest.mark.asyncio
async def test_billing_publisher_forwards_to_layer4(monkeypatch):
    monkeypatch.setenv("SERVICE_AUTH_SECRET", "svc-secret")
    publisher = BillingEventPublisher(base_url="http://billing")
    event = UsageEventRecord(
        event_id="evt-1",
        tenant_id="tenant-a",
        api_key_id="key-1",
        endpoint="/v1/benchmarks",
        method="GET",
        product_code="benchmarks",
        quantity=1.0,
        unit="request",
    )

    with respx.mock:
        route = respx.post("http://billing/v1/billing/events").mock(return_value=httpx.Response(201, json={"received": True}))
        result = await publisher.publish(event)

    assert route.called
    request = route.calls.last.request
    assert request.headers["X-Tenant-ID"] == "tenant-a"
    assert request.headers["X-Service-Auth"] == "svc-secret"
    assert result == {"received": True}
