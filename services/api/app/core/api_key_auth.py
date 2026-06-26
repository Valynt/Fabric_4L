from __future__ import annotations

from app.core.api_key_hash import hash_api_key
from app.repositories.api_key_repository import APIKeyRepository


async def resolve_api_key(raw_key: str) -> dict | None:
    """Resolver passed to ``GovernanceMiddleware`` for API-key auth.

    Returns a dict matching the middleware contract:
    ``tenant_id``, ``user_id``, ``role``, ``permissions``, ``key_id``, ``enabled``.
    """
    if not raw_key or not raw_key.startswith("vf_"):
        return None

    repo = APIKeyRepository()
    record = repo.get_by_hash(hash_api_key(raw_key))
    if record is None:
        return None

    return {
        "tenant_id": record.tenant_id,
        "user_id": None,
        "role": record.role,
        "permissions": record.permissions or [],
        "key_id": record.key_id,
        "enabled": record.enabled,
    }
