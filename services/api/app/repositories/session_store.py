from __future__ import annotations

from datetime import UTC, datetime

from app.services.distributed_store import DistributedStore

_SHARE_TTL_SECONDS = 7 * 24 * 60 * 60
_IMPERSONATION_TTL_SECONDS = 60 * 60


class ShareLinkRepository:
    def __init__(self, store: DistributedStore):
        self._store = store

    def _key(self, tenant_id: str, account_id: str) -> str:
        return f"vf:api:share_link:v1:tenant:{tenant_id}:account:{account_id}"

    def create(self, *, tenant_id: str, account_id: str, fingerprint_hash: str, expires_at_ts: int) -> None:
        self._store.set_json(
            self._key(tenant_id, account_id),
            {"fingerprint_hash": fingerprint_hash, "expires_at_ts": expires_at_ts},
            ttl_seconds=_SHARE_TTL_SECONDS,
        )

    def revoke(self, *, tenant_id: str, account_id: str) -> bool:
        return self._store.delete(self._key(tenant_id, account_id))


class ImpersonationSessionRepository:
    def __init__(self, store: DistributedStore):
        self._store = store

    def _key(self, tenant_id: str, session_id: str) -> str:
        return f"vf:api:impersonation:v1:tenant:{tenant_id}:session:{session_id}"

    def create(self, *, tenant_id: str, session_id: str, target_user_id: str, impersonated_by: str, reason: str, notify_email: bool, notify_webhook: bool) -> None:
        self._store.set_json(
            self._key(tenant_id, session_id),
            {
                "tenant_id": tenant_id,
                "target_user_id": target_user_id,
                "impersonated_by": impersonated_by,
                "reason": reason,
                "started_at": datetime.now(UTC).isoformat(),
                "notify_email": notify_email,
                "notify_webhook": notify_webhook,
            },
            ttl_seconds=_IMPERSONATION_TTL_SECONDS,
        )

    def pop(self, *, tenant_id: str, session_id: str) -> dict[str, object] | None:
        key = self._key(tenant_id, session_id)
        session = self._store.get_json(key)
        self._store.delete(key)
        return session
