from __future__ import annotations

import pytest

from app.services.distributed_store import RedisDistributedStore, StorePayloadError, StoreUnavailableError


class FakeRedis:
    def __init__(self):
        self.values: dict[str, object] = {}
        self.fail = False
        self.ex = None

    def get(self, key: str):
        if self.fail:
            from redis.exceptions import RedisError

            raise RedisError("down")
        return self.values.get(key)

    def set(self, name: str, value: str, ex: int):
        if self.fail:
            from redis.exceptions import RedisError

            raise RedisError("down")
        self.values[name] = value
        self.ex = ex
        return True

    def delete(self, key: str):
        if self.fail:
            from redis.exceptions import RedisError

            raise RedisError("down")
        return 1 if self.values.pop(key, None) is not None else 0

    def ping(self):
        if self.fail:
            from redis.exceptions import RedisError

            raise RedisError("down")
        return True


def test_backend_unavailable_raises_contract_safe_error() -> None:
    fake = FakeRedis()
    fake.fail = True
    store = RedisDistributedStore(client=fake)  # type: ignore[arg-type]
    with pytest.raises(StoreUnavailableError):
        store.get_json("k")


def test_malformed_payload_raises_store_payload_error() -> None:
    fake = FakeRedis()
    fake.values["k"] = "not-json"
    store = RedisDistributedStore(client=fake)  # type: ignore[arg-type]
    with pytest.raises(StorePayloadError):
        store.get_json("k")


def test_ttl_is_sent_to_backend_on_set() -> None:
    fake = FakeRedis()
    store = RedisDistributedStore(client=fake)  # type: ignore[arg-type]
    store.set_json("k", {"a": 1}, ttl_seconds=42)
    assert fake.ex == 42


def test_delete_semantics_return_true_when_key_existed() -> None:
    fake = FakeRedis()
    store = RedisDistributedStore(client=fake)  # type: ignore[arg-type]
    store.set_json("k", {"a": 1}, ttl_seconds=42)
    assert store.delete("k") is True
    assert store.delete("k") is False


def test_startup_validation_checks_roundtrip_serialization() -> None:
    fake = FakeRedis()
    store = RedisDistributedStore(client=fake)  # type: ignore[arg-type]
    store.validate_backend()
