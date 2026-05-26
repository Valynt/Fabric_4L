from __future__ import annotations

import time

import pytest

from app.repositories.session_store import ImpersonationSessionRepository, ShareLinkRepository


class InMemoryTTLStore:
    def __init__(self):
        self.values: dict[str, tuple[dict[str, object], float]] = {}

    def set_json(self, key: str, value: dict[str, object], ttl_seconds: int) -> None:
        self.values[key] = (value, time.time() + ttl_seconds)

    def get_json(self, key: str):
        item = self.values.get(key)
        if item is None:
            return None
        payload, expires = item
        if time.time() >= expires:
            self.values.pop(key, None)
            return None
        return payload

    def delete(self, key: str) -> bool:
        return self.values.pop(key, None) is not None


def test_tenant_isolation_in_key_schema() -> None:
    store = InMemoryTTLStore()
    repo = ShareLinkRepository(store)  # type: ignore[arg-type]
    repo.create(tenant_id="t1", account_id="a1", fingerprint_hash="h1", expires_at_ts=1)
    repo.create(tenant_id="t2", account_id="a1", fingerprint_hash="h2", expires_at_ts=2)
    assert len(store.values) == 2
    assert any("tenant:t1" in key for key in store.values)
    assert any("tenant:t2" in key for key in store.values)


def test_impersonation_pop_behaves_cross_process() -> None:
    store = InMemoryTTLStore()
    writer = ImpersonationSessionRepository(store)  # type: ignore[arg-type]
    reader = ImpersonationSessionRepository(store)  # type: ignore[arg-type]
    writer.create(tenant_id="t1", session_id="s1", target_user_id="u1", impersonated_by="admin", reason="support", notify_email=True, notify_webhook=False)
    session = reader.pop(tenant_id="t1", session_id="s1")
    assert session is not None
    assert session["target_user_id"] == "u1"
    assert reader.pop(tenant_id="t1", session_id="s1") is None


def test_ttl_expiry() -> None:
    store = InMemoryTTLStore()
    store.set_json("k", {"a": 1}, ttl_seconds=1)
    time.sleep(1.1)
    assert store.get_json("k") is None


def test_restart_durability_assumption_for_distributed_store() -> None:
    store = InMemoryTTLStore()
    repo = ShareLinkRepository(store)  # type: ignore[arg-type]
    repo.create(tenant_id="t1", account_id="a1", fingerprint_hash="h1", expires_at_ts=10)
    restarted_process_repo = ShareLinkRepository(store)  # type: ignore[arg-type]
    assert len(store.values) == 1
    assert restarted_process_repo.revoke(tenant_id="t1", account_id="a1") is True
