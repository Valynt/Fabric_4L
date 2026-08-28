from __future__ import annotations

import asyncio

import httpx
import pytest

from layer4_agents.integration.layer1_client import (
    Layer1ClientError,
    Layer1IngestionClient,
)
from layer4_agents.integration.layer2_client import (
    Layer2ClientError,
    Layer2ExtractionClient,
)
from layer4_agents.integration.layer3_client import Layer3Client, Layer3ClientError
from layer4_agents.integration.layer5_client import Layer5GroundTruthClient


class Response:
    def __init__(self, data=None, *, status_code=200, text="response"):
        self.data = data if data is not None else {"ok": True}
        self.status_code = status_code
        self.text = text

    def json(self):
        return self.data

    def raise_for_status(self):
        if self.status_code >= 400:
            request = httpx.Request("GET", "https://service.test")
            response = httpx.Response(self.status_code, request=request, text=self.text)
            raise httpx.HTTPStatusError("failure", request=request, response=response)


class Client:
    def __init__(self, responses=()):
        self.responses = list(responses)
        self.calls = []
        self.closed = False

    async def _call(self, method, path, **kwargs):
        self.calls.append((method, path, kwargs))
        outcome = self.responses.pop(0) if self.responses else Response()
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome

    async def request(self, method, url, **kwargs):
        return await self._call(method, url, **kwargs)

    async def get(self, path, **kwargs):
        return await self._call("GET", path, **kwargs)

    async def post(self, path, **kwargs):
        return await self._call("POST", path, **kwargs)

    async def patch(self, path, **kwargs):
        return await self._call("PATCH", path, **kwargs)

    async def aclose(self):
        self.closed = True


@pytest.mark.asyncio
async def test_layer1_complete_request_surface_and_cleanup(monkeypatch) -> None:
    monkeypatch.setenv("SERVICE_AUTH_SECRET", "service-secret")
    client = Layer1IngestionClient(base_url="https://l1/", api_key="api", tenant_id="tenant")
    fake = Client(
        [
            Response({"job_id": "job"}),
            Response({"status": "completed"}),
            Response({"result": "done"}),
            Response({"id": "target"}),
            Response({"job_id": "crawl"}),
            Response({"id": "target-2"}),
            Response({"job_id": "crawl-2"}),
        ]
    )
    await client.client.aclose()
    client.client = fake

    assert (await client.create_job("https://doc", tenant_id="tenant"))["job_id"] == "job"
    assert (await client.wait_for_completion("job", poll_interval=0))["status"] == "completed"
    assert (await client.get_extraction_result("job"))["result"] == "done"
    target = await client.create_website_target("https://site", tenant_id="tenant")
    assert target["id"] == "target"
    assert (await client.execute_target("target", tenant_id="tenant"))["job_id"] == "crawl"
    assert (await client.crawl_website("https://site2", tenant_id="tenant"))[
        "target_id"
    ] == "target-2"
    assert client._get_headers()["X-Service-Auth"] == "service-secret"
    await client.close()
    assert fake.closed


def test_layer1_requires_tenant_except_audited_system_calls() -> None:
    client = Layer1IngestionClient()
    with pytest.raises(Layer1ClientError, match="Missing tenant context"):
        client._require_tenant(None, operation="crawl")
    assert (
        client._require_tenant(
            None, operation="crawl", allow_system_call=True, audit_reason="maintenance"
        )
        == ""
    )


@pytest.mark.asyncio
async def test_layer1_timeout_missing_target_and_http_error(monkeypatch) -> None:
    client = Layer1IngestionClient(tenant_id="tenant")
    await client.client.aclose()
    client.client = Client([Response(status_code=500)])
    with pytest.raises(Layer1ClientError, match="Failed to create job"):
        await client.create_job("https://doc")

    async def pending(_job_id):
        return {"status": "running"}

    client.get_job_status = pending
    monkeypatch.setattr("layer4_agents.integration.layer1_client.time.monotonic", lambda: 10)
    with pytest.raises(Layer1ClientError, match="Timeout"):
        await client.wait_for_completion("job", timeout=-1, poll_interval=0)

    async def missing(**_kwargs):
        return {}

    client.create_website_target = missing
    with pytest.raises(Layer1ClientError, match="missing 'id'"):
        await client.crawl_website("https://site", tenant_id="tenant")


@pytest.mark.asyncio
async def test_layer2_complete_request_surface_and_error(monkeypatch) -> None:
    monkeypatch.setenv("SERVICE_AUTH_SECRET", "service-secret")
    client = Layer2ExtractionClient(api_key="api", tenant_id="tenant")
    fake = Client([Response({"index": i}) for i in range(7)])
    await client.client.aclose()
    client.client = fake

    assert (await client.extract_filing("url", "10-K", "ACME", ["revenue"]))["index"] == 0
    assert (await client.transcribe_earnings_call("audio", "Acme", "Q1", 2026))["index"] == 1
    assert (await client.extract_financial_metrics("text", ["revenue"], "ACME"))["index"] == 2
    assert (await client.identify_risk_factors("text", ["security"]))["index"] == 3
    assert (await client.extract_and_ingest("url", "10-K", "ACME"))["index"] == 4
    assert (await client.extract_operational_signals({"company": "Acme"}, "trace"))["index"] == 5
    assert (await client.extract_value_attributes("content", "url", "markdown"))["index"] == 6
    assert client._get_headers()["X-Service-Auth"] == "service-secret"
    await client.close()
    assert fake.closed

    no_tenant = Layer2ExtractionClient()
    with pytest.raises(Layer2ClientError, match="Missing tenant context"):
        no_tenant._require_tenant(None, operation="extract")
    await no_tenant.client.aclose()


@pytest.mark.parametrize(
    ("method", "args", "message"),
    [
        ("extract_filing", ("url", "10-K"), "Failed to extract filing"),
        ("transcribe_earnings_call", ("url", "Acme", "Q1", 2026), "Failed to transcribe"),
        ("extract_financial_metrics", ("text",), "Failed to extract metrics"),
        ("identify_risk_factors", ("text",), "Failed to identify risks"),
        ("extract_and_ingest", ("url", "10-K"), "Failed to extract and ingest"),
        ("extract_operational_signals", ({},), "Failed to extract signals"),
        ("extract_value_attributes", ("id", "url", "text"), "Failed to extract value attributes"),
    ],
)
@pytest.mark.asyncio
async def test_layer2_http_errors_are_typed(method, args, message) -> None:
    client = Layer2ExtractionClient(tenant_id="tenant")
    await client.client.aclose()
    client.client = Client([httpx.ConnectError("offline")])
    with pytest.raises(Layer2ClientError, match=message):
        await getattr(client, method)(*args)


@pytest.mark.asyncio
async def test_layer3_public_methods_preserve_tenant_and_payloads(monkeypatch) -> None:
    monkeypatch.setenv("SERVICE_AUTH_SECRET", "secret")
    client = Layer3Client("https://l3/", tenant_id="tenant")
    calls = []

    async def make(method, url, tenant_id, **kwargs):
        calls.append((method, url, tenant_id, kwargs))
        return {
            "signal_id": "signal",
            "matches": [{"id": "evidence"}],
            "links_created": 2,
            "signals": [{"id": "signal"}],
            "ok": True,
        }

    client._make_request = make
    assert (await client.query_graph("MATCH (n)", {"x": 1}))["ok"]
    await client.get_subgraph("entity", 3)
    await client.semantic_search("query", ["Account"], 5)
    await client.get_entity("entity")
    assert await client.persist_signal({"name": "signal"}) == "signal"
    assert await client.find_matching_evidence("pain", "SaaS", 3)
    await client.quantify_signal("name", "desc", ["cost"], "SaaS", {})
    assert await client.link_evidence("signal", []) == 2
    assert await client.get_signals_for_account("account", category="Operational")
    await client.get_benchmark_variables("SaaS")
    await client.get_value_driver_formulas(["driver-1", "driver-2"])
    await client.review_signal("signal", "account", "approved", "reviewer", "note")
    await client.decide_evidence("evidence", "account", "case", "accept", "reviewer", "note")
    await client.link_evidence_driver("evidence", "driver", "account", "case")
    assert calls and all(call[2] == "tenant" for call in calls)
    assert client._get_headers()["X-Service-Auth"] == "secret"
    with pytest.raises(ValueError, match="non-empty"):
        await client.get_value_driver_formulas([])


@pytest.mark.asyncio
async def test_layer3_request_retry_404_client_error_and_cleanup() -> None:
    client = Layer3Client("https://l3", tenant_id="tenant", max_retries=2)
    fake = Client([httpx.ConnectError("offline"), Response({"ok": True})])
    client._client = fake
    assert await client._make_request("GET", "https://l3/value", "tenant") == {"ok": True}

    client._client = Client([Response(status_code=404)])
    assert await client._make_request("GET", "url", "tenant", allow_404=True) is None
    client._client = Client([Response(status_code=403)])
    with pytest.raises(Layer3ClientError, match="HTTP 403"):
        await client._make_request("GET", "url", "tenant")
    client._client = Client([RuntimeError("broken")])
    with pytest.raises(Layer3ClientError, match="broken"):
        await client._make_request("GET", "url", "tenant")
    with pytest.raises(Layer3ClientError, match="Tenant ID required"):
        Layer3Client("https://l3")._get_effective_tenant(None)
    await client.close()
    assert client._client is None
    async with Layer3Client("https://l3") as entered:
        assert entered is not None


@pytest.mark.asyncio
async def test_layer5_success_surface_auth_tenant_and_cleanup(monkeypatch) -> None:
    monkeypatch.setenv("SERVICE_AUTH_SECRET", "secret")
    client = Layer5GroundTruthClient(tenant_id="tenant")
    fake = Client(
        [
            Response(status_code=200),
            Response({"synced": 1}),
            Response({"id": "truth"}),
            Response({"items": [], "total": 0}),
            Response({"id": "truth", "status": "approved"}),
            Response({"id": "truth"}),
            Response([{"action": "approved"}]),
            Response({"total_count": 1}),
            Response({"items": []}),
            Response({"levels": []}),
        ]
    )
    await client._client.aclose()
    client._client = fake
    assert await client.ping()
    assert fake.calls[0][0:2] == ("GET", "/health")
    assert (await client.sync_validated_truths("tenant"))["synced"] == 1
    assert (
        await client.submit_truth(
            "claim",
            "metric",
            0.9,
            "tenant",
            value=3,
            applies_to={"account_id": "a"},
            sources=[{"url": "u"}],
            extraction_job_id="job",
            extraction_model="model",
            raw_extraction_data={"x": 1},
        )
    )["id"] == "truth"
    await client.list_truths(
        "tenant",
        status="approved",
        claim_type="metric",
        min_maturity=2,
        min_confidence=0.8,
        applies_to_opportunity="opp",
    )
    await client.validate_truth("truth", "approve", "actor", organization_id="tenant", notes="ok")
    await client.get_truth("truth", "tenant")
    assert (await client.get_truth_audit("truth", "tenant"))["events"]
    await client.get_freshness_summary("tenant")
    await client.get_stale_truths("tenant", 5, 2)
    await client.get_maturity_ladder("tenant")
    await client.close()
    assert fake.closed


def test_layer5_rejects_untrusted_tenant_fallback(monkeypatch) -> None:
    monkeypatch.delenv("SERVICE_AUTH_SECRET", raising=False)
    with pytest.raises(ValueError, match="SERVICE_AUTH_SECRET"):
        Layer5GroundTruthClient(tenant_id="tenant")
    client = Layer5GroundTruthClient(service_token="token")
    with pytest.raises(ValueError, match="Missing tenant context"):
        client._require_organization_id(None, operation="sync")
    assert (
        client._require_organization_id(
            None, operation="sync", allow_system_call=True, audit_reason="maintenance"
        )
        == {}
    )


@pytest.mark.asyncio
async def test_layer5_failures_are_non_blocking_and_cancellation_propagates() -> None:
    client = Layer5GroundTruthClient(service_token="token")
    await client._client.aclose()
    operations = [
        ("sync_validated_truths", ("tenant",)),
        ("submit_truth", ("claim", "metric", 0.5, "tenant")),
        ("list_truths", ("tenant",)),
        ("validate_truth", ("truth", "approve", "actor")),
        ("get_truth", ("truth",)),
        ("get_truth_audit", ("truth",)),
        ("get_freshness_summary", ()),
        ("get_stale_truths", ()),
        ("get_maturity_ladder", ()),
    ]
    for name, args in operations:
        client._client = Client([RuntimeError("offline")])
        result = await getattr(client, name)(*args)
        assert getattr(result, "error", None) or result.get("error")
    client._client = Client([asyncio.CancelledError()])
    with pytest.raises(asyncio.CancelledError):
        await client.ping()


@pytest.mark.asyncio
async def test_layer5_degradation_increments_metric_when_initialized() -> None:
    """Swallowed L5 errors increment the degradation counter when metrics are on."""
    from layer4_agents.metrics.prometheus_metrics import initialize_metrics

    metrics = initialize_metrics()

    client = Layer5GroundTruthClient(service_token="token")
    await client._client.aclose()
    client._client = Client([RuntimeError("offline")])
    result = await client.list_truths("tenant")
    assert result.get("error")

    output = metrics.get_metrics()
    assert "l5_degradation_events_total" in output
    assert 'operation="list_truths"' in output
    assert 'error_class="RuntimeError"' in output

    # Degradation recording must never raise even when metrics are missing.
    client._client = Client([RuntimeError("offline")])
    out = await client.get_maturity_ladder()
    assert out.get("error")


@pytest.mark.asyncio
async def test_get_layer5_client_singleton_and_arg_keyed_isolation() -> None:
    """No-arg calls share one cached client; arg-keyed calls are fresh + isolated.

    Regression for the W2 factory: an arg-keyed call must never overwrite the
    module-level singleton (which would bleed config across call sites and let
    one caller's close() invalidate another's client).
    """
    import layer4_agents.integration.layer5_client as l5

    original = l5._client_instance
    try:
        l5._client_instance = None

        # No-arg: cached singleton, reused across calls.
        first = l5.get_layer5_client()
        second = l5.get_layer5_client()
        assert first is second
        assert first.base_url == l5._DEFAULT_BASE_URL

        # Arg-keyed: fresh instances, distinct for distinct args, and the
        # cached singleton is not mutated in place.
        a = l5.get_layer5_client(base_url="http://l5-a:8005", service_token="tok")
        b = l5.get_layer5_client(base_url="http://l5-b:8005", service_token="tok")
        assert a is not b
        assert a is not first
        assert a.base_url == "http://l5-a:8005"

        # Singleton unchanged by the arg-keyed calls above.
        assert l5._client_instance is first
        assert l5._client_instance.base_url == l5._DEFAULT_BASE_URL

        # close() on the arg-keyed client must not close the shared singleton.
        await a.close()
        assert l5._client_instance is first
    finally:
        # Restore the pre-existing singleton so the degradation test (which
        # relies on its own client) is unaffected.
        l5._client_instance = original
