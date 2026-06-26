"""Repository for gateway API-key records.

API keys are stored in ``db.api_keys`` with ``tenant_field="key_id"`` so the
table does **not** auto-filter by tenant. Tenant isolation is enforced manually
in this repository.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from app.core.api_key_hash import hash_api_key
from app.core.database import db
from app.models.api_key import APIKeyCreateRequest, APIKeyListItem, APIKeyRecord

if TYPE_CHECKING:
    from app.core.database import InMemoryDatabase, PostgreSQLDatabase


class APIKeyRepository:
    """Persistence operations for tenant-scoped API keys."""

    def __init__(self, database: InMemoryDatabase | PostgreSQLDatabase = db):
        self._db = database

    def create_key(
        self,
        tenant_id: str,
        request: APIKeyCreateRequest,
        raw_key: str,
        key_id: str,
        prefix: str,
    ) -> APIKeyRecord:
        """Hash the raw key and persist a new API-key record."""
        record = APIKeyRecord(
            key_id=key_id,
            tenant_id=tenant_id,
            name=request.name,
            key_hash=hash_api_key(raw_key),
            prefix=prefix,
            role=request.role,
            permissions=list(request.permissions),
        )
        self._db.api_keys.insert(key_id, record)
        return record

    def get_by_hash(self, key_hash: str) -> APIKeyRecord | None:
        """Return the active, non-revoked key matching ``key_hash``.

        Because keys are looked up by secret hash, this scans the whole table
        using the system scope and filters for a match and active status.
        """
        for record in self._db.api_keys.list(allow_system_scope=True, tenant_id="system"):
            if record.key_hash != key_hash:
                continue
            if not record.enabled or record.revoked_at is not None:
                return None
            return record
        return None

    def list_for_tenant(self, tenant_id: str) -> list[APIKeyListItem]:
        """Return listable metadata for every key owned by ``tenant_id``."""
        records = self._db.api_keys.list(tenant_id=tenant_id)
        return [
            APIKeyListItem(
                key_id=record.key_id,
                name=record.name,
                prefix=record.prefix,
                role=record.role,
                permissions=record.permissions,
                enabled=record.enabled,
                created_at=record.created_at,
                last_used_at=record.last_used_at,
            )
            for record in records
            if record.tenant_id == tenant_id
        ]

    def revoke_key(self, tenant_id: str, key_id: str) -> bool:
        """Revoke the key if it belongs to ``tenant_id``.

        Returns ``True`` if the key existed and was revoked, ``False`` otherwise.
        """
        record = self._db.api_keys.get(key_id, tenant_id=tenant_id)
        if record is None or record.tenant_id != tenant_id:
            return False

        record.enabled = False
        record.revoked_at = datetime.now(UTC).isoformat()
        self._db.api_keys.insert(key_id, record)
        return True
