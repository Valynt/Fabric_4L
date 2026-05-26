from __future__ import annotations

import json
from dataclasses import dataclass

from redis import Redis
from redis.exceptions import RedisError

from app.core.config import get_settings


class StoreUnavailableError(RuntimeError):
    """Raised when the distributed store cannot be reached."""


class DistributedStore:
    def get_json(self, key: str) -> dict[str, object] | None:
        raise NotImplementedError

    def set_json(self, key: str, value: dict[str, object], ttl_seconds: int) -> None:
        raise NotImplementedError

    def delete(self, key: str) -> bool:
        raise NotImplementedError


@dataclass
class RedisDistributedStore(DistributedStore):
    client: Redis

    def get_json(self, key: str) -> dict[str, object] | None:
        try:
            payload = self.client.get(key)
        except RedisError as exc:
            raise StoreUnavailableError("Redis unavailable") from exc
        if payload is None:
            return None
        if isinstance(payload, bytes):
            payload = payload.decode("utf-8")
        return json.loads(payload)

    def set_json(self, key: str, value: dict[str, object], ttl_seconds: int) -> None:
        try:
            self.client.set(name=key, value=json.dumps(value), ex=ttl_seconds)
        except RedisError as exc:
            raise StoreUnavailableError("Redis unavailable") from exc

    def delete(self, key: str) -> bool:
        try:
            deleted = self.client.delete(key)
        except RedisError as exc:
            raise StoreUnavailableError("Redis unavailable") from exc
        return deleted > 0


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
