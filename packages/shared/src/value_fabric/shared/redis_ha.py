"""Redis HA helpers for direct Redis and Redis Sentinel deployments.

The default path remains ``REDIS_URL`` so local/dev and managed Redis clients
keep their existing behavior. Production-data overlays can opt into Sentinel
with ``REDIS_SENTINEL_HOSTS`` and ``REDIS_SENTINEL_MASTER_NAME``.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import urlparse

DEFAULT_SENTINEL_MASTER_NAME = "fabric4l-master"


@dataclass(frozen=True)
class RedisHAConfig:
    redis_url: str | None
    sentinel_hosts: tuple[tuple[str, int], ...]
    sentinel_master_name: str
    sentinel_password: str | None
    sentinel_db: int
    decode_responses: bool = True

    @property
    def sentinel_enabled(self) -> bool:
        return bool(self.sentinel_hosts)


def _parse_sentinel_hosts(raw_hosts: str | None) -> tuple[tuple[str, int], ...]:
    if not raw_hosts:
        return ()

    hosts: list[tuple[str, int]] = []
    for raw_host in raw_hosts.split(","):
        host_part = raw_host.strip()
        if not host_part:
            continue
        host, separator, port = host_part.rpartition(":")
        if not separator:
            host = host_part
            port = "26379"
        hosts.append((host.strip(), int(port)))
    return tuple(hosts)


def _database_from_url(redis_url: str | None) -> int:
    if not redis_url:
        return 0
    path = urlparse(redis_url).path.strip("/")
    if not path:
        return 0
    try:
        return int(path)
    except ValueError:
        return 0


def get_redis_ha_config(
    *,
    redis_url: str | None = None,
    decode_responses: bool = True,
) -> RedisHAConfig:
    """Build Redis HA config from explicit values plus process env."""
    effective_url = redis_url or os.getenv("REDIS_URL")
    sentinel_password = (
        os.getenv("REDIS_SENTINEL_PASSWORD")
        or os.getenv("REDIS_PASSWORD")
        or _password_from_url(effective_url)
    )
    sentinel_db = int(os.getenv("REDIS_SENTINEL_DB") or _database_from_url(effective_url))
    return RedisHAConfig(
        redis_url=effective_url,
        sentinel_hosts=_parse_sentinel_hosts(os.getenv("REDIS_SENTINEL_HOSTS")),
        sentinel_master_name=os.getenv("REDIS_SENTINEL_MASTER_NAME", DEFAULT_SENTINEL_MASTER_NAME),
        sentinel_password=sentinel_password,
        sentinel_db=sentinel_db,
        decode_responses=decode_responses,
    )


def _password_from_url(redis_url: str | None) -> str | None:
    if not redis_url:
        return None
    return urlparse(redis_url).password


def create_sync_redis_client(
    redis_url: str | None = None,
    *,
    decode_responses: bool = True,
    socket_connect_timeout: float | None = 5,
    socket_timeout: float | None = 5,
):
    """Create a redis-py sync client for direct Redis or Sentinel master."""
    config = get_redis_ha_config(redis_url=redis_url, decode_responses=decode_responses)
    if config.sentinel_enabled:
        from redis.sentinel import Sentinel

        sentinel = Sentinel(
            config.sentinel_hosts,
            password=config.sentinel_password,
            sentinel_kwargs={"password": config.sentinel_password} if config.sentinel_password else None,
            socket_connect_timeout=socket_connect_timeout,
            socket_timeout=socket_timeout,
            decode_responses=decode_responses,
        )
        return sentinel.master_for(
            config.sentinel_master_name,
            db=config.sentinel_db,
            password=config.sentinel_password,
            socket_connect_timeout=socket_connect_timeout,
            socket_timeout=socket_timeout,
            decode_responses=decode_responses,
        )

    if not config.redis_url:
        return None

    import redis

    return redis.Redis.from_url(
        config.redis_url,
        decode_responses=decode_responses,
        socket_connect_timeout=socket_connect_timeout,
        socket_timeout=socket_timeout,
    )


def create_async_redis_client(
    redis_url: str | None = None,
    *,
    decode_responses: bool = True,
    socket_connect_timeout: float | None = 5,
    socket_timeout: float | None = 5,
):
    """Create a redis-py asyncio client for direct Redis or Sentinel master."""
    config = get_redis_ha_config(redis_url=redis_url, decode_responses=decode_responses)
    if config.sentinel_enabled:
        from redis.asyncio.sentinel import Sentinel

        sentinel = Sentinel(
            config.sentinel_hosts,
            password=config.sentinel_password,
            sentinel_kwargs={"password": config.sentinel_password} if config.sentinel_password else None,
            socket_connect_timeout=socket_connect_timeout,
            socket_timeout=socket_timeout,
            decode_responses=decode_responses,
        )
        return sentinel.master_for(
            config.sentinel_master_name,
            db=config.sentinel_db,
            password=config.sentinel_password,
            socket_connect_timeout=socket_connect_timeout,
            socket_timeout=socket_timeout,
            decode_responses=decode_responses,
        )

    if not config.redis_url:
        return None

    import redis.asyncio as redis

    return redis.from_url(
        config.redis_url,
        decode_responses=decode_responses,
        socket_connect_timeout=socket_connect_timeout,
        socket_timeout=socket_timeout,
    )


def get_celery_redis_broker_config(redis_url: str | None = None) -> tuple[str | None, dict[str, object]]:
    """Return Celery broker URL and transport options for Redis HA.

    Celery/Kombu uses ``sentinel://`` URLs plus ``master_name`` transport
    options for Redis Sentinel. Direct Redis keeps the existing URL-only path.
    """
    config = get_redis_ha_config(redis_url=redis_url)
    if not config.sentinel_enabled:
        return config.redis_url, {}

    broker_url = ";".join(f"sentinel://{host}:{port}/{config.sentinel_db}" for host, port in config.sentinel_hosts)
    transport_options: dict[str, object] = {
        "master_name": config.sentinel_master_name,
    }
    if config.sentinel_password:
        transport_options["sentinel_kwargs"] = {"password": config.sentinel_password}
        transport_options["password"] = config.sentinel_password
    return broker_url, transport_options
