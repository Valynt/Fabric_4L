from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException


_ALLOWED_STATUSES = {"completed", "ready", "succeeded"}


@dataclass
class ResolvedIngestionRecord:
    ingestion_id: str
    source_url: str
    markdown_content: str
    content_hash: str


class Layer1IngestionAdapter:
    """Resolve and validate ingestion provenance from Layer 1 metadata."""

    async def fetch_ingestion_record(self, ingestion_id: str) -> dict[str, Any] | None:
        """Fetch metadata from Layer 1.

        Implemented as an override/monkeypatch seam for now.
        """
        return None

    async def resolve_or_raise(self, *, ingestion_id: str, tenant_id: str | None) -> ResolvedIngestionRecord:
        record = await self.fetch_ingestion_record(ingestion_id)
        if not record:
            raise HTTPException(status_code=404, detail="Invalid ingestion provenance")

        record_tenant = str(record.get("tenant_id") or "")
        if tenant_id and record_tenant and record_tenant != str(tenant_id):
            raise HTTPException(status_code=403, detail="Invalid ingestion provenance")

        status = str(record.get("status") or "").lower()
        if status not in _ALLOWED_STATUSES:
            raise HTTPException(status_code=409, detail="Invalid ingestion provenance")

        content = str(record.get("markdown_content") or "")
        source_url = str(record.get("source_url") or "")
        content_hash = str(record.get("content_hash") or "")
        calculated = hashlib.sha256(content.encode("utf-8")).hexdigest()
        if not content_hash or content_hash != calculated:
            raise HTTPException(status_code=409, detail="Invalid ingestion provenance")

        return ResolvedIngestionRecord(
            ingestion_id=ingestion_id,
            source_url=source_url,
            markdown_content=content,
            content_hash=content_hash,
        )


def build_layer1_ingestion_adapter() -> Layer1IngestionAdapter:
    return Layer1IngestionAdapter()
