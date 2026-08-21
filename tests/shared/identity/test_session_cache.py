"""Tests for session_cache with tenant isolation and error resilience."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch
from uuid import UUID

import pytest
from value_fabric.shared.identity import session_cache
from value_fabric.shared.identity.session_cache import (
    _build_session_key,
    delete_session,
    get_redis_client,
    get_session,
    set_session,
)


@pytest.fixture
def tenant_id() -> UUID:
    return UUID("11111111-1111-1111-1111-111111111111")


@pytest.fixture
def user_id() -> UUID:
    return UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")


@pytest.fixture(autouse=True)
def reset_session_cache_redis():
    """Reset the module-level Redis client singleton."""
    session_cache._redis_client = None
    yield
    session_cache._redis_client = None


def test_build_session_key_scoping(tenant_id: UUID, user_id: UUID) -> None:
    """Session keys must be strictly scoped by both tenant_id and user_id."""
    key = _build_session_key(tenant_id, user_id)
    assert key == f"session:tenant:{tenant_id}:user:{user_id}"


def test_build_session_key_tenant_isolation(user_id: UUID) -> None:
    """Two different tenants with the same user_id must produce distinct session keys."""
    tenant_a = UUID("11111111-1111-1111-1111-111111111111")
    tenant_b = UUID("22222222-2222-2222-2222-222222222222")

    key_a = _build_session_key(tenant_a, user_id)
    key_b = _build_session_key(tenant_b, user_id)

    assert key_a != key_b
    assert str(tenant_a) in key_a
    assert str(tenant_b) in key_b


def test_build_session_key_user_isolation(tenant_id: UUID) -> None:
    """Two different users within the same tenant must produce distinct session keys."""
    user_a = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    user_b = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")

    key_a = _build_session_key(tenant_id, user_a)
    key_b = _build_session_key(tenant_id, user_b)

    assert key_a != key_b


@pytest.mark.asyncio
async def test_get_redis_client_singleton(monkeypatch: pytest.MonkeyPatch) -> None:
    """get_redis_client should create and reuse a single Redis client instance."""
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")

    with patch("redis.asyncio.from_url") as mock_from_url:
        mock_client = AsyncMock()
        mock_from_url.return_value = mock_client

        client1 = await get_redis_client()
        client2 = await get_redis_client()

        assert client1 is mock_client
        assert client2 is mock_client
        mock_from_url.assert_called_once_with("redis://localhost:6379/0", decode_responses=True)


@pytest.mark.asyncio
async def test_set_session_and_get_session(tenant_id: UUID, user_id: UUID) -> None:
    """set_session should serialize session data and get_session should deserialize it."""
    mock_redis = AsyncMock()
    stored_data: dict[str, str] = {}

    async def mock_set(key: str, val: str, ex: int | None = None) -> None:
        stored_data[key] = val

    async def mock_get(key: str) -> str | None:
        return stored_data.get(key)

    mock_redis.set = AsyncMock(side_effect=mock_set)
    mock_redis.get = AsyncMock(side_effect=mock_get)

    with patch("value_fabric.shared.identity.session_cache.get_redis_client", return_value=mock_redis):
        session_payload = {"user_id": str(user_id), "role": "admin", "permissions": ["read", "write"]}

        cached = await set_session(tenant_id, user_id, session_payload, ttl_seconds=3600)
        assert cached == session_payload

        key = _build_session_key(tenant_id, user_id)
        mock_redis.set.assert_called_once_with(key, json.dumps(session_payload), ex=3600)

        retrieved = await get_session(tenant_id, user_id)
        assert retrieved == session_payload


@pytest.mark.asyncio
async def test_get_session_missing_returns_none(tenant_id: UUID, user_id: UUID) -> None:
    """get_session should return None when the session key does not exist."""
    mock_redis = AsyncMock()
    mock_redis.get.return_value = None

    with patch("value_fabric.shared.identity.session_cache.get_redis_client", return_value=mock_redis):
        retrieved = await get_session(tenant_id, user_id)
        assert retrieved is None


@pytest.mark.asyncio
async def test_delete_session(tenant_id: UUID, user_id: UUID) -> None:
    """delete_session should call redis delete on the scoped key and return True."""
    mock_redis = AsyncMock()
    mock_redis.delete = AsyncMock(return_value=1)

    with patch("value_fabric.shared.identity.session_cache.get_redis_client", return_value=mock_redis):
        success = await delete_session(tenant_id, user_id)
        assert success is True

        key = _build_session_key(tenant_id, user_id)
        mock_redis.delete.assert_called_once_with(key)


@pytest.mark.asyncio
async def test_session_cache_redis_exception_resilience(tenant_id: UUID, user_id: UUID) -> None:
    """Operations should fail gracefully and not crash if Redis raises an exception."""
    mock_redis = AsyncMock()
    mock_redis.get.side_effect = ConnectionError("Redis connection lost")
    mock_redis.set.side_effect = ConnectionError("Redis connection lost")
    mock_redis.delete.side_effect = ConnectionError("Redis connection lost")

    with patch("value_fabric.shared.identity.session_cache.get_redis_client", return_value=mock_redis):
        # get_session returns None on failure
        assert await get_session(tenant_id, user_id) is None

        # set_session returns original session data on failure without crashing
        data = {"user": "test"}
        assert await set_session(tenant_id, user_id, data) == data

        # delete_session returns False on failure
        assert await delete_session(tenant_id, user_id) is False
