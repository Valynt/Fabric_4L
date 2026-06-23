from __future__ import annotations

from value_fabric.shared.redis_ha import (
    DEFAULT_SENTINEL_MASTER_NAME,
    get_celery_redis_broker_config,
    get_redis_ha_config,
)


def test_direct_redis_config_preserves_url(monkeypatch):
    monkeypatch.delenv("REDIS_SENTINEL_HOSTS", raising=False)
    monkeypatch.setenv("REDIS_URL", "rediss://:secret@redis.example:6379/2")

    config = get_redis_ha_config()

    assert config.redis_url == "rediss://:secret@redis.example:6379/2"
    assert config.sentinel_hosts == ()
    assert config.sentinel_db == 2
    assert config.sentinel_password == "secret"


def test_sentinel_config_uses_hosts_master_and_password(monkeypatch):
    monkeypatch.setenv("REDIS_URL", "rediss://:direct@redis.example:6379/3")
    monkeypatch.setenv("REDIS_SENTINEL_HOSTS", "redis-sentinel-a:26379, redis-sentinel-b:26380")
    monkeypatch.setenv("REDIS_SENTINEL_MASTER_NAME", "fabric4l-master")
    monkeypatch.setenv("REDIS_SENTINEL_PASSWORD", "sentinel-secret")

    config = get_redis_ha_config()

    assert config.sentinel_hosts == (("redis-sentinel-a", 26379), ("redis-sentinel-b", 26380))
    assert config.sentinel_master_name == "fabric4l-master"
    assert config.sentinel_password == "sentinel-secret"
    assert config.sentinel_db == 3
    assert config.sentinel_enabled is True


def test_celery_direct_redis_keeps_url(monkeypatch):
    monkeypatch.delenv("REDIS_SENTINEL_HOSTS", raising=False)
    monkeypatch.setenv("REDIS_URL", "redis://redis:6379/0")

    broker_url, transport_options = get_celery_redis_broker_config()

    assert broker_url == "redis://redis:6379/0"
    assert transport_options == {}


def test_celery_sentinel_builds_kombu_options(monkeypatch):
    monkeypatch.setenv("REDIS_URL", "rediss://:secret@redis.example:6379/4")
    monkeypatch.setenv("REDIS_SENTINEL_HOSTS", "redis-sentinel:26379")
    monkeypatch.delenv("REDIS_SENTINEL_MASTER_NAME", raising=False)

    broker_url, transport_options = get_celery_redis_broker_config()

    assert broker_url == "sentinel://redis-sentinel:26379/4"
    assert transport_options["master_name"] == DEFAULT_SENTINEL_MASTER_NAME
    assert transport_options["sentinel_kwargs"] == {"password": "secret"}
    assert transport_options["password"] == "secret"
