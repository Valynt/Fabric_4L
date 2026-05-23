from __future__ import annotations

import pytest

from layer2_extraction.api import main as api_main


@pytest.mark.asyncio
async def test_extract_rejects_invalid_ingestion_id(async_client, monkeypatch: pytest.MonkeyPatch) -> None:
    async def _missing(*, ingestion_id: str, tenant_id: str | None):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Invalid ingestion provenance")

    monkeypatch.setattr(api_main.layer1_ingestion_adapter, "resolve_or_raise", _missing)

    response = await async_client.post("/v1/extract", json={"ingestion_id": "missing-1"})
    assert response.status_code == 404
    assert response.json()["detail"] == "Invalid ingestion provenance"


@pytest.mark.asyncio
async def test_extract_rejects_wrong_tenant_ingestion_id(async_client, monkeypatch: pytest.MonkeyPatch) -> None:
    async def _wrong_tenant(*, ingestion_id: str, tenant_id: str | None):
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Invalid ingestion provenance")

    monkeypatch.setattr(api_main.layer1_ingestion_adapter, "resolve_or_raise", _wrong_tenant)

    response = await async_client.post("/v1/extract-and-ingest", json={"ingestion_id": "tenant-b-record"})
    assert response.status_code == 403
    assert response.json()["detail"] == "Invalid ingestion provenance"


@pytest.mark.asyncio
async def test_extract_rejects_invalid_ingestion_status(async_client, monkeypatch: pytest.MonkeyPatch) -> None:
    async def _bad_status(*, ingestion_id: str, tenant_id: str | None):
        from fastapi import HTTPException
        raise HTTPException(status_code=409, detail="Invalid ingestion provenance")

    monkeypatch.setattr(api_main.layer1_ingestion_adapter, "resolve_or_raise", _bad_status)

    response = await async_client.post("/v1/extract/batch", json=[{"ingestion_id": "stale-status"}])
    assert response.status_code == 409
    assert response.json()["detail"] == "Invalid ingestion provenance"
