from __future__ import annotations

import json
import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import NoReturn, TypeVar

import structlog
from redis import Redis
from redis.exceptions import RedisError

from app.core.config import get_settings

logger = structlog.get_logger(__name__)

T = TypeVar("T")

# Error codes for distributed store operations
ERR_CIRCUIT_OPEN = "circuit_open"
ERR_REDIS_UNAVAILABLE = "redis_unavailable"
ERR_REDIS_URL_NOT_CONFIGURED = "redis_url_not_configured"
ERR_INVALID_JSON_PAYLOAD = "invalid_json_payload"
ERR_PAYLOAD_NOT_DICT = "payload_not_dict"
ERR_SERIALIZATION_FAILED = "serialization_failed"
ERR_SERIALIZATION_COMPATIBILITY_FAILED = "serialization_compatibility_failed"


class StoreUnavailableError(RuntimeError):
    """Raised when the distributed store cannot be reached."""

    def __init__(self, code: str, *, operation: str | None = None) -> None:
        super().__init__(code)
        self.code = code
        self.operation = operation


class StorePayloadError(RuntimeError):
    """Raised when a payload cannot be decoded to the expected contract."""

    def __init__(self, code: str, *, operation: str | None = None) -> None:
        super().__init__(code)
        self.code = code
        self.operation = operation


class DistributedStore(ABC):
    @abstractmethod
    def get_json(self, key: str) -> dict[str, object] | None: ...

    @abstractmethod
    def set_json(
        self, key: str, value: dict[str, object], ttl_seconds: int
    ) -> None: ...

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
        if (
            time.monotonic() - self._circuit_opened_at
            >= self.circuit_breaker_reset_seconds
        ):
            self._circuit_opened_at = None
            self._consecutive_failures = 0
            return
        raise StoreUnavailableError(ERR_CIRCUIT_OPEN)

    def _mark_failure(self, exc: Exception, operation: str | None = None) -> NoReturn:
        self._consecutive_failures += 1
        op_name = operation or "unknown"
        if self._consecutive_failures >= self.circuit_breaker_failures:
            self._circuit_opened_at = time.monotonic()
            logger.error(
                "Circuit breaker opened",
                operation=op_name,
                error=str(exc),
                circuit_state="open",
                consecutive_failures=self._consecutive_failures,
            )
        else:
            logger.warning(
                "Redis operation failed",
                operation=op_name,
                error=str(exc),
                circuit_state="closed",
                consecutive_failures=self._consecutive_failures,
                circuit_breaker_failures=self.circuit_breaker_failures,
            )
        raise StoreUnavailableError(ERR_REDIS_UNAVAILABLE, operation=operation) from exc

    def _with_resilience(self, operation_name: str, fn: Callable[[], T]) -> T:
        self._ensure_circuit_closed()
        last_exc: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                result = fn()
            except RedisError as exc:
                last_exc = exc
                if attempt < self.max_retries:
                    time.sleep(self.retry_backoff_seconds * (2**attempt))
                    continue
                self._mark_failure(exc, operation=operation_name)
            else:
                self._consecutive_failures = 0
                self._circuit_opened_at = None
                return result
        raise StoreUnavailableError(
            ERR_REDIS_UNAVAILABLE, operation=operation_name
        ) from last_exc

    def get_json(self, key: str) -> dict[str, object] | None:
        payload = self._with_resilience("get", lambda: self.client.get(key))
        if payload is None:
            return None
        if isinstance(payload, bytes):
            payload = payload.decode("utf-8")
        try:
            obj = json.loads(payload)
        except (TypeError, json.JSONDecodeError) as exc:
            raise StorePayloadError(ERR_INVALID_JSON_PAYLOAD) from exc
        if not isinstance(obj, dict):
            raise StorePayloadError(ERR_PAYLOAD_NOT_DICT)
        return obj

    def set_json(self, key: str, value: dict[str, object], ttl_seconds: int) -> None:
        try:
            payload = json.dumps(value)
        except (TypeError, ValueError) as exc:
            raise StorePayloadError(ERR_SERIALIZATION_FAILED) from exc
        self._with_resilience(
            "set", lambda: self.client.set(name=key, value=payload, ex=ttl_seconds)
        )

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
            raise StorePayloadError(ERR_SERIALIZATION_COMPATIBILITY_FAILED)


_store_singleton: DistributedStore | None = None


class InMemoryDistributedStore(DistributedStore):
    """Process-local distributed store for tests and local development.

    Mirrors the Redis-backed contract without external dependencies.  Data does
    not survive process restarts and is not shared across workers, so this must
    never be used in production-like deployments.
    """

    def __init__(self) -> None:
        self._data: dict[str, tuple[dict[str, object], float]] = {}

    def _expire(self, key: str) -> None:
        item = self._data.get(key)
        if item is None:
            return
        _, expires_at = item
        if time.monotonic() >= expires_at:
            self._data.pop(key, None)

    def get_json(self, key: str) -> dict[str, object] | None:
        self._expire(key)
        item = self._data.get(key)
        if item is None:
            return None
        value, _ = item
        return value

    def set_json(self, key: str, value: dict[str, object], ttl_seconds: int) -> None:
        expires_at = time.monotonic() + ttl_seconds
        self._data[key] = (value, expires_at)

    def delete(self, key: str) -> bool:
        return self._data.pop(key, None) is not None

    def validate_backend(self) -> None:
        """No-op: the in-memory backend is always available in this process."""
        return None


def get_distributed_store() -> DistributedStore:
    global _store_singleton
    if _store_singleton is None:
        settings = get_settings()
        if settings.mock_persistence:
            _store_singleton = InMemoryDistributedStore()
        elif not settings.redis_url:
            raise StoreUnavailableError(ERR_REDIS_URL_NOT_CONFIGURED)
        else:
            client = Redis.from_url(settings.redis_url, decode_responses=False)
            _store_singleton = RedisDistributedStore(client=client)
    return _store_singleton
