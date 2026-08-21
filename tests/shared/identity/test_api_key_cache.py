from uuid import UUID

import pytest
from value_fabric.shared.identity.api_key_cache import _build_api_key_cache_key


@pytest.fixture
def tenant_id() -> UUID:
    return UUID("11111111-1111-1111-1111-111111111111")


def test_build_api_key_cache_key_is_deterministic(monkeypatch: pytest.MonkeyPatch, tenant_id: UUID) -> None:
    monkeypatch.setenv("API_KEY_FINGERPRINT_SECRET", "unit-test-secret")
    monkeypatch.setenv("ENVIRONMENT", "production")

    key1 = _build_api_key_cache_key("sk_test_dummy_abc123", tenant_id)
    key2 = _build_api_key_cache_key("sk_test_dummy_abc123", tenant_id)

    assert key1 == key2
    assert key1.startswith("apikey:v2:tenant:")


def test_build_api_key_cache_key_is_tenant_isolated(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("API_KEY_FINGERPRINT_SECRET", "unit-test-secret")

    key = "sk_test_dummy_same"
    tenant_a = UUID("11111111-1111-1111-1111-111111111111")
    tenant_b = UUID("22222222-2222-2222-2222-222222222222")

    cache_key_a = _build_api_key_cache_key(key, tenant_a)
    cache_key_b = _build_api_key_cache_key(key, tenant_b)

    assert cache_key_a != cache_key_b
    assert f"tenant:{tenant_a}" in cache_key_a
    assert f"tenant:{tenant_b}" in cache_key_b


def test_build_api_key_cache_key_collision_resistance(monkeypatch: pytest.MonkeyPatch, tenant_id: UUID) -> None:
    monkeypatch.setenv("API_KEY_FINGERPRINT_SECRET", "unit-test-secret")

    k1 = _build_api_key_cache_key("sk_test_dummy_abc123", tenant_id)
    k2 = _build_api_key_cache_key("sk_test_dummy_abc124", tenant_id)

    assert k1 != k2


def test_build_api_key_cache_key_fails_closed_without_secret_in_production(monkeypatch: pytest.MonkeyPatch, tenant_id: UUID) -> None:
    monkeypatch.delenv("API_KEY_FINGERPRINT_SECRET", raising=False)
    monkeypatch.setenv("ENVIRONMENT", "production")

    with pytest.raises(RuntimeError, match="API_KEY_FINGERPRINT_SECRET"):
        _build_api_key_cache_key("sk_test_dummy_missing", tenant_id)
