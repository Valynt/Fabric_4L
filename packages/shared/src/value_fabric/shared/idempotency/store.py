from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from typing import Protocol


@dataclass(frozen=True)
class StoredIdempotencyRecord:
    tenant_id: str
    endpoint_key: str
    idempotency_key: str
    request_fingerprint: str
    status_code: int
    body: Any
    headers: dict[str, str]
    expires_at: datetime


class IdempotencyStore(Protocol):
    def get(self, tenant_id: str, endpoint_key: str, idempotency_key: str) -> StoredIdempotencyRecord | None: ...

    def set(self, record: StoredIdempotencyRecord) -> None: ...


class InMemoryIdempotencyStore:
    def __init__(self) -> None:
        self._records: dict[tuple[str, str, str], StoredIdempotencyRecord] = {}

    def get(self, tenant_id: str, endpoint_key: str, idempotency_key: str) -> StoredIdempotencyRecord | None:
        key = (tenant_id, endpoint_key, idempotency_key)
        record = self._records.get(key)
        if record is None:
            return None
        if record.expires_at <= datetime.now(UTC):
            self._records.pop(key, None)
            return None
        return record

    def set(self, record: StoredIdempotencyRecord) -> None:
        self._records[(record.tenant_id, record.endpoint_key, record.idempotency_key)] = record
