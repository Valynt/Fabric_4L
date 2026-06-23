from __future__ import annotations

import pytest

from app.services.distributed_store import (
    ERR_CIRCUIT_OPEN,
    ERR_INVALID_JSON_PAYLOAD,
    ERR_REDIS_UNAVAILABLE,
    RedisDistributedStore,
    StorePayloadError,
    StoreUnavailableError,
)


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


def test_store_unavailable_error_preserves_operation() -> None:
    err = StoreUnavailableError(ERR_REDIS_UNAVAILABLE, operation="get_json")
    assert err.code == ERR_REDIS_UNAVAILABLE
    assert err.operation == "get_json"


def test_store_payload_error_preserves_operation() -> None:
    from app.services.distributed_store import StorePayloadError

    err = StorePayloadError(ERR_INVALID_JSON_PAYLOAD, operation="set_json")
    assert err.code == ERR_INVALID_JSON_PAYLOAD
    assert err.operation == "set_json"


def test_backend_unavailable_preserves_operation_name() -> None:
    """Verify _with_resilience threads operation name into the exception."""
    fake = FakeRedis()
    fake.fail = True
    store = RedisDistributedStore(client=fake, max_retries=0)  # type: ignore[arg-type]
    with pytest.raises(StoreUnavailableError) as exc_info:
        store.get_json("k")
    assert exc_info.value.operation == "get"


def test_circuit_open_error_has_no_operation() -> None:
    """Circuit-open errors don't have an operation since they pre-empt execution."""
    fake = FakeRedis()
    store = RedisDistributedStore(client=fake)  # type: ignore[arg-type]
    # Manually open the circuit
    store._circuit_opened_at = 9999999999.0  # far in the future so it stays open
    with pytest.raises(StoreUnavailableError) as exc_info:
        store.get_json("k")
    assert exc_info.value.code == ERR_CIRCUIT_OPEN
    assert exc_info.value.operation is None
