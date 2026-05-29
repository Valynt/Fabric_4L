from __future__ import annotations

"""OIDC state store implementations (migrated from monolithic oidc.py)."""


import logging
from datetime import UTC, datetime, timedelta
from threading import Lock
from typing import Any, Protocol

logger = logging.getLogger(__name__)


class OIDCStateStoreProtocol(Protocol):
    """Protocol for storing and consuming OIDC state and PKCE verifiers."""

    def store(self, state: str, code_verifier: str) -> None:
        """Store the verifier with strict TTL semantics."""

    def validate_and_consume(self, state: str) -> str | None:
        """Atomically validate and consume state for single-use semantics."""


class InMemoryOIDCStateStore(OIDCStateStoreProtocol):
    """In-memory store for tests/development only.

    This store is explicitly non-production and guarded by ``allow_non_production``.
    """

    def __init__(self, ttl_seconds: int = 300, *, allow_non_production: bool = False) -> None:
        if not allow_non_production:
            raise RuntimeError(
                "InMemoryOIDCStateStore is for tests/development only. "
                "Use RedisOIDCStateStore in production."
            )
        self._store: dict[str, tuple[str, datetime]] = {}
        self._ttl = ttl_seconds
        self._lock = Lock()

    def store(self, state: str, code_verifier: str) -> None:
        expiry = datetime.now(UTC) + timedelta(seconds=self._ttl)
        with self._lock:
            self._store[state] = (code_verifier, expiry)
        logger.debug("oidc_state_stored_memory state_prefix=%s ttl=%d", state[:8], self._ttl)

    def validate_and_consume(self, state: str) -> str | None:
        now = datetime.now(UTC)
        with self._lock:
            record = self._store.get(state)
            if record is None:
                logger.warning("oidc_state_not_found_memory state_prefix=%s", state[:8])
                return None
            code_verifier, expiry = record
            if now > expiry:
                del self._store[state]
                logger.warning("oidc_state_expired_memory state_prefix=%s", state[:8])
                return None
            del self._store[state]
        logger.debug("oidc_state_consumed_memory state_prefix=%s", state[:8])
        return code_verifier


class RedisOIDCStateStore(OIDCStateStoreProtocol):
    """Redis-backed OIDC state store with atomic consume semantics."""

    def __init__(self, redis_client: Any, ttl_seconds: int = 300, *, key_prefix: str = "oidc:state") -> None:
        self._redis = redis_client
        self._ttl = ttl_seconds
        self._key_prefix = key_prefix

    def _key(self, state: str) -> str:
        return f"{self._key_prefix}:{state}"

    def store(self, state: str, code_verifier: str) -> None:
        self._redis.set(self._key(state), code_verifier, ex=self._ttl)
        logger.debug("oidc_state_stored_redis state_prefix=%s ttl=%d", state[:8], self._ttl)

    def validate_and_consume(self, state: str) -> str | None:
        key = self._key(state)
        try:
            verifier = self._redis.getdel(key)
        except AttributeError:
            verifier = self._redis.eval(
                "local v = redis.call('GET', KEYS[1]); if v then redis.call('DEL', KEYS[1]); end; return v",
                1,
                key,
            )

        if verifier is None:
            logger.warning("oidc_state_not_found_or_expired_redis state_prefix=%s", state[:8])
            return None

        if isinstance(verifier, bytes):
            verifier = verifier.decode("utf-8")

        logger.debug("oidc_state_consumed_redis state_prefix=%s", state[:8])
        return str(verifier)


class OIDCStateStore(RedisOIDCStateStore):
    """Default production OIDC state store implementation (Redis-backed)."""


def create_oidc_state_store(
    *,
    redis_client: Any | None,
    ttl_seconds: int = 300,
    backend: str = "redis",
    allow_non_production_memory: bool = False,
) -> OIDCStateStoreProtocol:
    """Create OIDC state store using configured backend.

    Redis is the production default. In-memory backend requires explicit non-prod guard.
    """

    normalized = backend.strip().lower()
    if normalized == "memory":
        return InMemoryOIDCStateStore(
            ttl_seconds=ttl_seconds,
            allow_non_production=allow_non_production_memory,
        )

    if redis_client is None:
        raise RuntimeError("OIDC state store requires Redis client when backend=redis")

    return RedisOIDCStateStore(redis_client=redis_client, ttl_seconds=ttl_seconds)
