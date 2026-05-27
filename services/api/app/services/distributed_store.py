from __future__ import annotations

import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from redis import Redis
from redis.exceptions import RedisError

from app.core.config import get_settings


class StoreUnavailableError(RuntimeError):
    """Raised when the distributed store cannot be reached."""


class StorePayloadError(RuntimeError):
    """Raised when a payload cannot be decoded to the expected contract."""


class DistributedStore(ABC):
    @abstractmethod
    def get_json(self, key: str) -> dict[str, object] | None: ...

    @abstractmethod
    def set_json(self, key: str, value: dict[str, object], ttl_seconds: int) -> None: ...

    @abstractmethod
    def delete(self, key: str) -> bool: ...

    @abstractmethod
    def validate_backend(self) -> None: ...


@dataclass
class RedisDistributedStore(DistributedStore):
    client: Redis
    max_retries: int = 2
    retry_backoff_seconds: float = 0.05
    circuit_breaker_failures: int = 3
    circuit_breaker_reset_seconds: float = 5.0
    _consecutive_failures: int = field(default=0, init=False)
    _circuit_opened_at: float | None = field(default=None, init=False)

    def _ensure_circuit_closed(self) -> None:
        if self._circuit_opened_at is None:
            return
        if time.monotonic() - self._circuit_opened_at >= self.circuit_breaker_reset_seconds:
            self._circuit_opened_at = None
            self._consecutive_failures = 0
            return
        raise StoreUnavailableError("Distributed store circuit is open")

    def _mark_failure(self, exc: Exception) -> "NoReturn":
        self._consecutive_failures += 1
        if self._consecutive_failures >= self.circuit_breaker_failures:
            self._circuit_opened_at = time.monotonic()
        raise StoreUnavailableError("Redis unavailable") from exc

    def _with_resilience(self, operation_name: str, fn):
        self._ensure_circuit_closed()
        last_exc: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                result = fn()
                self._consecutive_failures = 0
                self._circuit_opened_at = None
                return result
            except RedisError as exc:
                last_exc = exc
                if attempt < self.max_retries:
                    time.sleep(self.retry_backoff_seconds * (2**attempt))
                    continue
                self._mark_failure(exc)
        raise StoreUnavailableError(f"Redis unavailable during {operation_name}") from last_exc

    def get_json(self, key: str) -> dict[str, object] | None:
        payload = self._with_resilience("get", lambda: self.client.get(key))
        if payload is None:
            return None
        if isinstance(payload, bytes):
            payload = payload.decode("utf-8")
        try:
            obj = json.loads(payload)
        except (TypeError, json.JSONDecodeError) as exc:
            raise StorePayloadError("Invalid JSON payload in distributed store") from exc
        if not isinstance(obj, dict):
            raise StorePayloadError("Distributed store payload must be a JSON object")
        return obj

    def set_json(self, key: str, value: dict[str, object], ttl_seconds: int) -> None:
        try:
            payload = json.dumps(value)
        except (TypeError, ValueError) as exc:
            raise StorePayloadError("Payload cannot be serialized to JSON") from exc
        self._with_resilience("set", lambda: self.client.set(name=key, value=payload, ex=ttl_seconds))

    def delete(self, key: str) -> bool:
        deleted = self._with_resilience("delete", lambda: self.client.delete(key))
        return deleted > 0

    def validate_backend(self) -> None:
        probe_key = "vf:api:store:startup-probe"
        probe_payload = {"ok": True, "component": "fabric-api"}
        self._with_resilience("ping", lambda: self.client.ping())
        self.set_json(probe_key, probe_payload, ttl_seconds=30)
        try:
            loaded = self.get_json(probe_key)
        finally:
            self.delete(probe_key)
        if loaded != probe_payload:
            raise StorePayloadError("Distributed store serialization compatibility check failed")


_store_singleton: DistributedStore | None = None


def get_distributed_store() -> DistributedStore:
    global _store_singleton
    if _store_singleton is None:
        settings = get_settings()
        if not settings.redis_url:
            raise StoreUnavailableError("REDIS_URL not configured")
        client = Redis.from_url(settings.redis_url, decode_responses=False)
        _store_singleton = RedisDistributedStore(client=client)
    return _store_singleton
