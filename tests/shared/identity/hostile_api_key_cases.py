"""Reusable hostile API-key resolver cases for migrated layer adapters."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

INVALID_API_KEY_CONTEXT_ERROR_CODE = "INVALID_API_KEY_CONTEXT"


def valid_api_key_record() -> dict[str, Any]:
    return {
        "tenant_id": str(uuid4()),
        "user_id": str(uuid4()),
        "key_id": "key-valid",
        "role": "tenant_admin",
        "request_id": "req-valid",
        "metadata": {"source": "test"},
    }


def hostile_api_key_records() -> list[dict[str, Any]]:
    base = valid_api_key_record()
    return [
        {**base, "metadata": {}},
        {k: v for k, v in base.items() if k != "metadata"},
        {k: v for k, v in base.items() if k != "tenant_id"},
        {**base, "tenant_id": ""},
    ]
