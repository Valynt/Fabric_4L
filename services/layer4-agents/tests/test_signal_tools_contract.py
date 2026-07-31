from __future__ import annotations

import asyncio
from types import SimpleNamespace
from uuid import UUID

import pytest
from value_fabric.shared.error_handling.exceptions import AuthenticationError
from value_fabric.shared.identity.context import RequestContext

import layer4_agents.tools.signal_tools as module

TENANT = UUID("550e8400-e29b-41d4-a716-446655440000")


class Response:
    def __init__(self, status_code, data=None):
        self.status_code = status_code
        self.data = data or {}

    def json(self):
        return self.data


class Client:
    def __init__(self):
        self.is_closed = False
        self.get_results = []
        self.post_results = []
        self.calls = []
        self.closed = 0

    async def get(self, url, **kwargs):
        self.calls.append(("get", url, kwargs))
        result = self.get_results.pop(0)
        if isinstance(result, BaseException):
            raise result
        return result

    async def post(self, url, **kwargs):
        self.calls.append(("post", url, kwargs))
        result = self.post_results.pop(0)
        if isinstance(result, BaseException):
            raise result
        return result

    async def aclose(self):
        self.closed += 1
        self.is_closed = True


@pytest.fixture
def context():
    return RequestContext(
        tenant_id=TENANT,
        user_id="user",
        request_id="request",
        trace_id="trace",
        roles=["admin"],
    )


@pytest.fixture(autouse=True)
def isolate(monkeypatch):
    monkeypatch.setattr(module, "_http_client", None)
    monkeypatch.setattr(module, "authorize_action", lambda _action, ctx: ctx)
    audits = []
    monkeypatch.setattr(module, "emit_audit_event", lambda **kwargs: audits.append(kwargs))
    return audits


def test_http_client_is_lazy_cached_and_recreated_when_closed(monkeypatch) -> None:
    created = []

    def factory(**kwargs):
        client = Client()
        created.append((client, kwargs))
        return client

    monkeypatch.setattr(module.httpx, "AsyncClient", factory)
    first = module._get_http_client()
    assert module._get_http_client() is first
    first.is_closed = True
    second = module._get_http_client()
    assert second is not first and len(created) == 2
    assert created[0][1]["timeout"] == module._HTTP_TIMEOUT


@pytest.mark.asyncio
async def test_close_http_client_closes_live_client_and_is_idempotent() -> None:
    client = Client()
    module._http_client = client
    await module.close_http_client()
    assert client.closed == 1 and module._http_client is None
    await module.close_http_client()
    closed = Client()
    closed.is_closed = True
    module._http_client = closed
    await module.close_http_client()
    assert closed.closed == 0


def test_context_fails_closed_and_headers_propagate_correlation(monkeypatch, context) -> None:
    monkeypatch.setattr(module, "get_request_context", lambda: None)
    with pytest.raises(AuthenticationError):
        module._require_tool_context()
    with pytest.raises(AuthenticationError):
        module._require_tool_context(RequestContext(user_id="user"))
    assert module._require_tool_context(context) is context
    assert module._signal_headers("tenant") == {"X-Tenant-ID": "tenant"}
    assert module._signal_headers("tenant", "request") == {
        "X-Tenant-ID": "tenant",
        "X-Request-ID": "request",
        "X-Correlation-ID": "request",
    }
    assert module._signal_headers("tenant", "request", "run")["X-Correlation-ID"] == "run"


@pytest.mark.asyncio
async def test_get_account_signals_success_filters_headers_and_audit(context, isolate) -> None:
    client = Client()
    client.get_results = [Response(200, {"items": [{"id": "signal"}]})]
    module._http_client = client
    result = await module.get_account_signals(
        "account",
        signal_types=["pain"],
        lifecycle_states=["promoted"],
        min_confidence=0.8,
        limit=7,
        context=context,
    )
    assert result == [{"id": "signal"}]
    _, url, kwargs = client.calls[0]
    assert url.endswith("/api/v1/signals")
    assert kwargs["params"] == {
        "account_id": "account",
        "min_confidence": 0.8,
        "limit": 7,
        "lifecycle_state": ["promoted"],
        "types": ["pain"],
    }
    assert kwargs["headers"]["X-Tenant-ID"] == str(TENANT)
    assert isolate[-1]["details"]["reason"] == "ok"


@pytest.mark.asyncio
async def test_get_account_signals_defaults_failures_cancellation_and_bad_authorization(
    monkeypatch, context, isolate
) -> None:
    client = Client()
    client.get_results = [Response(503), RuntimeError("offline"), asyncio.CancelledError()]
    module._http_client = client
    assert await module.get_account_signals("account", context=context) == []
    assert await module.get_account_signals("account", context=context) == []
    with pytest.raises(asyncio.CancelledError):
        await module.get_account_signals("account", context=context)
    assert client.calls[0][2]["params"]["lifecycle_state"] == ["validated", "promoted"]
    assert "types" not in client.calls[0][2]["params"]
    assert all(audit["details"]["reason"] == "error" for audit in isolate)
    monkeypatch.setattr(module, "authorize_action", lambda *_args: object())
    with pytest.raises(AuthenticationError):
        await module.get_account_signals("account", context=context)


@pytest.mark.asyncio
async def test_create_signal_builds_provenance_without_mutating_input(context, isolate) -> None:
    evidence = [{"source_ref": "document", "confidence": 0.9}]
    original = [dict(evidence[0])]
    client = Client()
    client.post_results = [Response(201, {"id": "signal", "status": "created"})]
    module._http_client = client
    result = await module.create_signal(
        "account",
        "pain",
        "Manual work",
        evidence,
        0.9,
        provenance_method="agent_inference",
        provenance_model="model",
        run_id="run",
        impact_area="cost",
        estimated_value=1000,
        source_refs=["document"],
        context=context,
    )
    assert result["id"] == "signal"
    assert evidence == original
    payload = client.calls[0][2]["json"]
    assert payload["evidence"][0]["id"]
    assert payload["provenance"]["model"] == "model"
    assert payload["impact_area"] == "cost" and payload["estimated_value"] == 1000
    assert client.calls[0][2]["headers"]["X-Correlation-ID"] == "run"
    assert isolate[-1]["resource_id"] == "signal" and isolate[-1]["details"]["reason"] == "ok"


@pytest.mark.asyncio
async def test_create_signal_failure_cancel_and_bad_authorization(
    monkeypatch, context, isolate
) -> None:
    client = Client()
    client.post_results = [Response(400), RuntimeError("offline"), asyncio.CancelledError()]
    module._http_client = client
    args = ("account", "risk", "Risk", [{"id": "evidence"}], 0.7)
    assert await module.create_signal(*args, context=context) is None
    assert await module.create_signal(*args, context=context) is None
    with pytest.raises(asyncio.CancelledError):
        await module.create_signal(*args, context=context)
    assert all(audit["details"]["reason"] == "error" for audit in isolate)
    monkeypatch.setattr(module, "authorize_action", lambda *_args: SimpleNamespace(tenant_id=None))
    with pytest.raises(AuthenticationError):
        await module.create_signal(*args, context=context)


@pytest.mark.asyncio
async def test_business_case_groups_known_unknown_and_unclassified(monkeypatch, context) -> None:
    signals = [
        {"id": "revenue", "impact_area": "revenue"},
        {"id": "other", "impact_area": "people"},
        {"id": "none"},
    ]
    calls = []

    async def get(account_id, **kwargs):
        calls.append((account_id, kwargs))
        return signals

    monkeypatch.setattr(module, "get_account_signals", get)
    grouped = await module.get_signals_for_business_case("account", context)
    assert grouped["revenue"] == [signals[0]]
    assert grouped["unclassified"] == [signals[1], signals[2]]
    assert calls[0][1]["min_confidence"] == 0.4 and calls[0][1]["limit"] == 200


@pytest.mark.asyncio
async def test_renewal_and_expansion_wrappers_use_canonical_filters(monkeypatch, context) -> None:
    calls = []

    async def get(account_id, **kwargs):
        calls.append((account_id, kwargs))
        return [{"account": account_id}]

    monkeypatch.setattr(module, "get_account_signals", get)
    assert await module.get_renewal_risk_signals("account", context) == [{"account": "account"}]
    assert await module.get_expansion_signals("account", context) == [{"account": "account"}]
    assert calls[0][1]["signal_types"] == ["risk", "renewal"]
    assert calls[0][1]["min_confidence"] == 0.3
    assert calls[1][1]["signal_types"] == ["expansion", "opportunity", "revenue_uplift"]
    assert calls[1][1]["min_confidence"] == 0.4
