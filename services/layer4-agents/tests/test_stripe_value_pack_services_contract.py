from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

import layer4_agents.services.stripe_client as stripe_module
import layer4_agents.services.value_pack_service as pack_module
from layer4_agents.interfaces.value_pack_service import (
    FormulaRef,
    PackExecutionRequest,
    PackStatus,
    ValuePack,
)
from layer4_agents.services.stripe_client import (
    StripeMeterEventError,
    StripeNotConfiguredError,
)
from layer4_agents.services.value_pack_service import Neo4jValuePackService


def stripe_api(*, create=None, retrieve=None, meters=()):
    return SimpleNamespace(
        api_key="key",
        billing=SimpleNamespace(
            meter_event=SimpleNamespace(create=create),
            meter=SimpleNamespace(retrieve=retrieve, list=lambda: SimpleNamespace(data=meters)),
        ),
    )


def test_stripe_configuration_and_prices(monkeypatch) -> None:
    monkeypatch.setattr(stripe_module, "stripe", None)
    with pytest.raises(StripeNotConfiguredError, match="not installed"):
        stripe_module.get_stripe()
    monkeypatch.setattr(stripe_module, "stripe", SimpleNamespace(api_key=""))
    with pytest.raises(StripeNotConfiguredError, match="not configured"):
        stripe_module.get_stripe()
    configured = SimpleNamespace(api_key="key")
    monkeypatch.setattr(stripe_module, "stripe", configured)
    assert stripe_module.get_stripe() is configured
    monkeypatch.setattr(stripe_module, "STRIPE_PRICE_PRO", "price_pro")
    assert stripe_module.get_price_id("pro") == "price_pro"
    assert stripe_module.get_price_id("enterprise") == ""
    assert stripe_module.get_price_id("invalid") is None


def test_meter_events_disabled_success_failure_and_cancellation(monkeypatch) -> None:
    monkeypatch.setattr(stripe_module, "STRIPE_METER_EVENTS_ENABLED", False)
    skipped = stripe_module.report_meter_event("cus", "tokens", 1)
    assert skipped.skipped and skipped.reason == "disabled"
    assert stripe_module.get_billing_meter() is None

    captured = {}

    def create(**payload):
        captured.update(payload)
        return SimpleNamespace(id="evt", event_name=payload["event_name"], status="active")

    monkeypatch.setattr(stripe_module, "STRIPE_METER_EVENTS_ENABLED", True)
    monkeypatch.setattr(stripe_module, "stripe", stripe_api(create=create))
    result = stripe_module.report_meter_event(
        "cus", "tokens", 2.75, datetime(2025, 1, 1, tzinfo=UTC), "stable"
    )
    assert result.id == "evt" and result.event_name == "llm_tokens"
    assert captured["identifier"] == "stable" and captured["payload"]["value"] == "2"
    assert captured["timestamp"] == 1735689600

    monkeypatch.setattr(
        stripe_module, "stripe", stripe_api(create=lambda **_kwargs: _raise(ValueError("safe")))
    )
    with pytest.raises(StripeMeterEventError, match="safe"):
        stripe_module.report_meter_event("cus", "custom", 1)
    monkeypatch.setattr(
        stripe_module,
        "stripe",
        stripe_api(create=lambda **_kwargs: _raise(asyncio.CancelledError())),
    )
    with pytest.raises(asyncio.CancelledError):
        stripe_module.report_meter_event("cus", "tokens", 1)


def test_get_billing_meter_contract(monkeypatch) -> None:
    meter = SimpleNamespace(id="m", display_name="Usage", event_name="tokens", status="active")
    monkeypatch.setattr(stripe_module, "STRIPE_METER_EVENTS_ENABLED", True)
    monkeypatch.setattr(
        stripe_module, "stripe", stripe_api(retrieve=lambda _id: meter, meters=[meter])
    )
    assert stripe_module.get_billing_meter("m").id == "m"
    assert stripe_module.get_billing_meter()[0]["event_name"] == "tokens"
    monkeypatch.setattr(
        stripe_module,
        "stripe",
        stripe_api(retrieve=lambda _id: _raise(RuntimeError("unavailable"))),
    )
    assert stripe_module.get_billing_meter("m") is None


class UsageDB:
    def __init__(self, total, count, events=()):
        self.results = [
            SimpleNamespace(one=lambda: SimpleNamespace(total=total, count=count)),
            SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: list(events))),
        ]
        self.flushes = 0

    async def execute(self, _query):
        return self.results.pop(0)

    async def flush(self):
        self.flushes += 1


@pytest.mark.asyncio
async def test_sync_usage_success_empty_and_failure(monkeypatch) -> None:
    empty = await stripe_module.sync_usage_to_stripe(UsageDB(0, 0), "t", "c", "tokens", "cus")
    assert empty.synced == 0 and empty.total_quantity == 0
    events = [SimpleNamespace(status=None, processed_at=None) for _ in range(2)]
    db = UsageDB(7, 2, events)
    monkeypatch.setattr(stripe_module, "report_meter_event", lambda **_kwargs: {"id": "event"})
    result = await stripe_module.sync_usage_to_stripe(db, "t", "c", "tokens", "cus")
    assert result.synced == 2 and result.total_quantity == 7 and db.flushes == 1
    assert all(event.processed_at is not None for event in events)
    monkeypatch.setattr(
        stripe_module,
        "report_meter_event",
        lambda **_kwargs: _raise(StripeMeterEventError("failed")),
    )
    failed = await stripe_module.sync_usage_to_stripe(UsageDB(3, 1), "t", "c", "tokens", "cus")
    assert failed.error == "STRIPE_SYNC_ERROR" and failed.total_quantity == 3


def record(pack_id="pack", **overrides):
    value = {
        "id": pack_id,
        "name": "Pack",
        "description": "Description",
        "industry": "software",
        "status": "published",
        "version": "1.2.3",
        "createdAt": "2025-01-01T00:00:00+00:00",
    }
    value.update(overrides)
    return {"vp": value, "drivers": [], "formulas": [], "benchmarks": []}


@pytest.mark.asyncio
async def test_value_pack_reads_loads_saves_and_errors(monkeypatch) -> None:
    responses = [
        [record()],
        [],
        [record()],
        [record()],
        [{"vp": {"updatedAt": "2025-02-01T00:00:00+00:00"}}],
    ]
    calls = []

    async def fetch(**kwargs):
        calls.append(kwargs)
        return responses.pop(0)

    monkeypatch.setattr(pack_module, "fetch_tenant_validated_records", fetch)
    service = Neo4jValuePackService(object())
    packs = await service.list_packs("tenant", industry="software", status=PackStatus.PUBLISHED)
    assert packs[0].pack_id == "pack" and calls[0]["params"]["tenant_id"] == "tenant"
    assert await service.get_pack("missing", "tenant") is None
    loaded = await service.load_pack_into_workspace("pack", "workspace", "tenant")
    assert loaded.is_loaded and loaded.workspace_id == "workspace"
    loaded.name = "Changed"
    saved = await service.save_pack(loaded, "tenant")
    assert saved.updated_at == datetime(2025, 2, 1, tzinfo=UTC)
    monkeypatch.setattr(service, "get_pack", lambda *_args: _value(None))
    with pytest.raises(ValueError, match="not found"):
        await service.load_pack_into_workspace("missing", "workspace", "tenant")
    assert service._increment_version("1.2.3") == "1.2.4"
    assert service._increment_version("invalid") == "1.0.0"


@pytest.mark.asyncio
async def test_value_pack_execution_and_customization(monkeypatch) -> None:
    formula = FormulaRef(formula_id="x + y", name="total", version="1", variables=["x", "y"])
    pack = ValuePack(
        pack_id="pack",
        name="Pack",
        description="D",
        industry="software",
        segment=None,
        status=PackStatus.PUBLISHED,
        version="1.2.3",
        formulas=[formula],
    )
    service = Neo4jValuePackService(object())
    monkeypatch.setattr(service, "get_pack", lambda *_args: _value(pack))
    calls = []

    async def fetch(**kwargs):
        calls.append(kwargs)
        if kwargs["operation"].endswith("customize_pack"):
            return [{"new": record("new")["vp"]}]
        return []

    monkeypatch.setattr(pack_module, "fetch_tenant_validated_records", fetch)
    request = PackExecutionRequest(pack_id="pack", workspace_id="workspace", variables={"x": 2})
    result = await service.execute_pack(request, "tenant")
    assert result.status == "success" and result.outputs["total"] == 2
    assert request.variables == {"x": 2}
    customized = await service.customize_pack(
        "pack", "workspace", "tenant", {"name": "Custom", "user_id": "user"}
    )
    assert customized.pack_id == "new" and customized.is_loaded

    monkeypatch.setattr(service, "get_pack", lambda *_args: _value(None))
    missing = await service.execute_pack(request, "tenant")
    assert missing.status == "failed" and "not found" in missing.errors[0]
    with pytest.raises(ValueError, match="not found"):
        await service.customize_pack("missing", "workspace", "tenant", {})


def _raise(error):
    raise error


async def _value(value):
    return value
