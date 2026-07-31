from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

import layer4_agents.services.export_storage as storage_module
import layer4_agents.services.plan_version_service as plan_module
from layer4_agents.services.plan_version_service import PlanVersionService


class Result:
    def __init__(self, *, value=None, first=None):
        self.value = value
        self.first_value = first

    def scalar_one_or_none(self):
        return self.value

    def scalars(self):
        return SimpleNamespace(first=lambda: self.first_value)


class DB:
    def __init__(self, results=()):
        self.results = list(results)
        self.added = []
        self.flushes = 0

    async def execute(self, _query):
        return self.results.pop(0)

    def add(self, value):
        self.added.append(value)

    async def flush(self):
        self.flushes += 1


def test_tenant_storage_key_rejects_cross_scope_paths() -> None:
    assert storage_module._tenant_key("tenant", "exports/report.pdf") == "tenant/exports/report.pdf"
    assert storage_module._tenant_key("tenant", "tenant/report.pdf") == "tenant/report.pdf"
    for tenant, key in [("", "key"), ("tenant", ""), ("tenant", "/root"), ("tenant", "../x")]:
        with pytest.raises(ValueError):
            storage_module._tenant_key(tenant, key)


@pytest.mark.asyncio
async def test_storage_upload_and_signed_download(monkeypatch) -> None:
    calls = []

    class Client:
        def put_object(self, **kwargs):
            calls.append(("put", kwargs))
            return {"ETag": "etag"}

        def generate_presigned_url(self, operation, **kwargs):
            calls.append((operation, kwargs))
            return "https://signed.example.test"

    settings = SimpleNamespace(
        export_storage_bucket="exports",
        export_signed_url_ttl_seconds=90,
    )
    monkeypatch.setattr(storage_module, "_s3_client", Client)
    monkeypatch.setattr(storage_module, "get_settings", lambda: settings)
    stored = await storage_module.upload_bytes(
        tenant_id="tenant",
        object_key="report.pdf",
        content=b"data",
        content_type="application/pdf",
        metadata={"kind": "report"},
    )
    assert (
        stored.bucket == "exports" and stored.key == "tenant/report.pdf" and stored.etag == "etag"
    )
    url = await storage_module.generate_download_url(
        tenant_id="tenant", object_key="report.pdf", expires_in_seconds=30
    )
    assert url == "https://signed.example.test"
    assert calls[-1][1]["ExpiresIn"] == 30


@pytest.mark.asyncio
async def test_plan_version_lookup_bootstrap_and_subscription(monkeypatch) -> None:
    now = datetime.now(UTC)
    effective = object()
    db = DB([Result(first=effective)])
    service = PlanVersionService(db)
    assert await service.get_effective_plan_version("free", now) is effective

    existing = object()
    outcomes = {"free": existing, "pro": None, "enterprise": None}
    monkeypatch.setattr(
        service, "get_effective_plan_version", lambda plan_id, _at: _value(outcomes[plan_id])
    )
    monkeypatch.setattr(
        plan_module,
        "build_plan_version_payload",
        lambda plan_id: {"features": [plan_id], "usage_limits": {"requests": 1}},
    )
    await service.ensure_bootstrap_defaults()
    assert {item.plan_id for item in db.added} == {"pro", "enterprise"}
    assert db.flushes == 1

    monkeypatch.setattr(service, "get_effective_plan_version", lambda plan_id, _at: _value(plan_id))
    assert await service.get_subscription_plan_version(None, now) == "free"
    subscription = SimpleNamespace(plan_version_id="version", plan_id="pro", tenant_id="tenant")
    pinned = object()
    db.results = [Result(value=pinned), Result(value=None)]
    assert await service.get_subscription_plan_version(subscription, now) is pinned
    assert await service.get_subscription_plan_version(subscription, now) == "pro"


async def _value(value):
    return value
