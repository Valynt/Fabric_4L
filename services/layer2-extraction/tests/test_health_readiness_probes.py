from __future__ import annotations

from datetime import datetime

import pytest

from layer2_extraction.api import main


class _PendingStore:
    def __init__(self, exc: Exception | None = None) -> None:
        self.exc = exc
        self.called_at: datetime | None = None

    async def get_due(self, due_at: datetime) -> list[object]:
        self.called_at = due_at
        if self.exc is not None:
            raise self.exc
        return []


class _QuarantineStore:
    def __init__(self, exc: Exception | None = None) -> None:
        self.exc = exc
        self.tenant_id: str | None = None

    async def list(self, *, tenant_id: str) -> list[object]:
        self.tenant_id = tenant_id
        if self.exc is not None:
            raise self.exc
        return []


@pytest.mark.asyncio
async def test_pending_ingestion_probe_reports_healthy_store(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _PendingStore()
    monkeypatch.setattr(main, "pending_ingestion_store", store)

    result = await main._pending_ingestion_probe()

    assert result.name == "pending_ingestion_store"
    assert result.healthy is True
    assert result.detail is None
    assert store.called_at is not None


@pytest.mark.asyncio
async def test_pending_ingestion_probe_reports_store_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _PendingStore(RuntimeError("pending unavailable"))
    monkeypatch.setattr(main, "pending_ingestion_store", store)

    result = await main._pending_ingestion_probe()

    assert result.name == "pending_ingestion_store"
    assert result.healthy is False
    assert result.detail == "RuntimeError"


@pytest.mark.asyncio
async def test_quarantine_probe_uses_health_probe_tenant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _QuarantineStore()
    monkeypatch.setattr(main, "quarantine_store", store)

    result = await main._quarantine_probe()

    assert result.name == "quarantine_store"
    assert result.healthy is True
    assert result.detail is None
    assert store.tenant_id == "__health_probe__"


@pytest.mark.asyncio
async def test_quarantine_probe_reports_store_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _QuarantineStore(RuntimeError("quarantine unavailable"))
    monkeypatch.setattr(main, "quarantine_store", store)

    result = await main._quarantine_probe()

    assert result.name == "quarantine_store"
    assert result.healthy is False
    assert result.detail == "RuntimeError"
