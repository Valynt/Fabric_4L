from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from .store import IdempotencyStore, StoredIdempotencyRecord


def build_request_fingerprint(method: str, path: str, body: dict) -> str:
    stable = json.dumps(body, sort_keys=True, separators=(",", ":"))
    payload = f"{method.upper()}|{path}|{stable}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class IdempotencyConflictError(ValueError):
    pass


@dataclass(frozen=True)
class IdempotencyRequest:
    tenant_id: str
    endpoint_key: str
    idempotency_key: str
    request_fingerprint: str


@dataclass(frozen=True)
class IdempotencyRecord:
    status_code: int
    body: Any
    headers: dict[str, str]


class IdempotencyService:
    def __init__(self, store: IdempotencyStore, ttl_seconds: int = 24 * 60 * 60) -> None:
        self._store = store
        self._ttl_seconds = ttl_seconds

    def check_replay(self, request: IdempotencyRequest) -> IdempotencyRecord | None:
        existing = self._store.get(request.tenant_id, request.endpoint_key, request.idempotency_key)
        if existing is None:
            return None
        if existing.request_fingerprint != request.request_fingerprint:
            raise IdempotencyConflictError("Idempotency key replayed with different payload")
        return IdempotencyRecord(
            status_code=existing.status_code,
            body=existing.body,
            headers=existing.headers,
        )

    def store_response(self, request: IdempotencyRequest, response: IdempotencyRecord) -> None:
        self._store.set(
            StoredIdempotencyRecord(
                tenant_id=request.tenant_id,
                endpoint_key=request.endpoint_key,
                idempotency_key=request.idempotency_key,
                request_fingerprint=request.request_fingerprint,
                status_code=response.status_code,
                body=response.body,
                headers=response.headers,
                expires_at=datetime.now(UTC) + timedelta(seconds=self._ttl_seconds),
            )
        )

    @staticmethod
    def create_from_env() -> "IdempotencyService":
        """Factory to create IdempotencyService from environment configuration.
        
        Uses in-memory store by default. For production, configure Redis-backed store.
        
        Returns:
            IdempotencyService instance
        """
        from .store import InMemoryIdempotencyStore
        
        store = InMemoryIdempotencyStore()
        return IdempotencyService(store=store)
