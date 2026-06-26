# API Monetization Gateway — Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add API-key authentication and usage metering to the `services/api/` gateway, expose `/v1/benchmarks` as the first metered public endpoint, and update the OpenAPI contract.

**Architecture:** Gateway-owned API keys (HMAC-SHA256 hashed, prefix `vf_`) are stored in the gateway's existing generic `db` table. A resolver plugs into the shared `GovernanceMiddleware` so `X-API-Key` / `Authorization: Bearer vf_...` requests resolve tenant context. A lightweight `UsageMeter` records per-request events to an append-only `usage_events` table. The new `/v1/benchmarks` router proxies to Layer 6 over HTTP with service-to-service auth headers.

**Tech Stack:** Python 3.11, FastAPI, Pydantic v2, httpx, pytest, value_fabric shared identity/middleware, gateway `db` persistence facade.

---

## File Structure

| File | Responsibility |
|---|---|
| `services/api/app/core/api_key_hash.py` | HMAC-SHA256 hashing of raw API keys; prefix extraction. |
| `services/api/app/models/api_key.py` | Pydantic schemas for API key records and create/list responses. |
| `services/api/app/repositories/api_key_repository.py` | Create, lookup-by-hash, list-for-tenant, revoke. |
| `services/api/app/core/api_key_auth.py` | Resolver callable consumed by `GovernanceMiddleware`. |
| `services/api/app/core/governance.py` | Gateway-specific middleware assembly with API-key resolver + route audit. |
| `services/api/app/core/usage_meter.py` | `UsageEventRecord` schema and `record_usage()` helper. |
| `services/api/app/routers/usage.py` | `GET /v1/usage` and `GET /v1/usage/quotas` (Phase 1 stubs). |
| `services/api/app/routers/api_keys.py` | `POST/GET/DELETE /v1/auth/api-keys` management. |
| `services/api/app/routers/benchmarks.py` | `GET/POST /v1/benchmarks` proxy to Layer 6 with metering. |
| `services/api/app/clients/layer6_client.py` | Typed httpx client for Layer 6. |
| `services/api/app/core/config.py` | New `layer6_api_base_url` setting. |
| `services/api/app/core/database.py` | Add `api_keys` and `usage_events` tables. |
| `services/api/app/main.py` | Mount new routers; wire gateway governance helper. |
| `.env.example` | Document new env vars. |
| `contracts/openapi/fabric-4l-api.json` | Add new paths/components. |
| `services/api/app/tests/...` | Unit and route tests. |

---

## Task 1: API-key hashing helper

**Files:**
- Create: `services/api/app/core/api_key_hash.py`
- Test: `services/api/app/tests/test_api_key_hash.py`

- [ ] **Step 1: Write the failing test**

```python
# services/api/app/tests/test_api_key_hash.py
import os

import pytest

from app.core.api_key_hash import hash_api_key, extract_key_prefix, generate_api_key


@pytest.fixture(autouse=True)
def _set_hmac_secret(monkeypatch):
    monkeypatch.setenv("API_KEY_HMAC_SECRET", "test-secret-for-hashing-only-32bytes")


def test_hash_api_key_is_deterministic():
    raw = "vf_testkey123456789"
    assert hash_api_key(raw) == hash_api_key(raw)


def test_hash_api_key_uses_hmac_sha256():
    os.environ["API_KEY_HMAC_SECRET"] = "a" * 32
    digest = hash_api_key("vf_raw")
    assert len(digest) == 64
    assert all(c in "0123456789abcdef" for c in digest)


def test_prefix_extracts_first_chars():
    assert extract_key_prefix("vf_abcdefghij") == "vf_abcdef"


def test_generate_api_key_has_expected_shape():
    raw, key_id, prefix = generate_api_key(name="test")
    assert raw.startswith("vf_")
    assert len(raw) == 64
    assert key_id.startswith("vf_key_")
    assert prefix == raw[:12]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest services/api/app/tests/test_api_key_hash.py -v`

Expected: `ModuleNotFoundError: No module named 'app.core.api_key_hash'`

- [ ] **Step 3: Write minimal implementation**

```python
# services/api/app/core/api_key_hash.py
"""API-key secret handling for the gateway.

Raw keys use the format ``vf_<random>`` and are hashed with HMAC-SHA256
using ``API_KEY_HMAC_SECRET``. Only the hash, prefix, and key_id are stored.
"""

from __future__ import annotations

import hmac
import os
import secrets


def _hmac_secret() -> str:
    return os.environ.get("API_KEY_HMAC_SECRET", "")


def hash_api_key(raw_key: str) -> str:
    """Return the 64-character hex HMAC-SHA256 digest of a raw API key."""
    secret = _hmac_secret().encode("utf-8")
    return hmac.new(secret, raw_key.encode("utf-8"), "sha256").hexdigest()


def extract_key_prefix(raw_key: str, length: int = 12) -> str:
    """Return a display-safe prefix of the raw key."""
    return raw_key[:length]


def generate_api_key(*, name: str) -> tuple[str, str, str]:
    """Generate a new raw API key, key_id, and prefix.

    Returns ``(raw_key, key_id, prefix)``. The raw key must be shown exactly once.
    """
    random_part = secrets.token_urlsafe(32)
    raw_key = f"vf_{random_part}"
    key_id = f"vf_key_{secrets.token_urlsafe(8)}"
    prefix = extract_key_prefix(raw_key)
    return raw_key, key_id, prefix
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest services/api/app/tests/test_api_key_hash.py -v`

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add services/api/app/core/api_key_hash.py services/api/app/tests/test_api_key_hash.py
git commit -m "feat(api): gateway API-key hashing helper"
```

---

## Task 2: API-key Pydantic schemas

**Files:**
- Create: `services/api/app/models/api_key.py`

- [ ] **Step 1: Write the schema file**

```python
# services/api/app/models/api_key.py
from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field


class APIKeyPermission(str):
    """Permission string allowed on an API key."""


class APIKeyCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    role: Literal["read_only", "analyst", "content_admin", "tenant_admin"] = "analyst"
    permissions: list[str] = Field(default_factory=list)


class APIKeyCreateResponse(BaseModel):
    key_id: str
    name: str
    api_key: str  # raw key shown exactly once
    prefix: str
    tenant_id: str
    role: str
    permissions: list[str]
    created_at: str


class APIKeyRecord(BaseModel):
    """Stored API key record (raw secret is never persisted)."""

    key_id: str
    tenant_id: str
    name: str
    key_hash: str
    prefix: str
    role: str
    permissions: list[str]
    enabled: bool = True
    revoked_at: str | None = None
    expires_at: str | None = None
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    last_used_at: str | None = None


class APIKeyListItem(BaseModel):
    key_id: str
    name: str
    prefix: str
    role: str
    permissions: list[str]
    enabled: bool
    created_at: str
    last_used_at: str | None


class APIKeyListResponse(BaseModel):
    items: list[APIKeyListItem]
```

- [ ] **Step 2: Add a smoke import test**

Add to `services/api/app/tests/test_api_key_hash.py` (or create `test_api_key_models.py`):

```python
def test_api_key_models_import():
    from app.models.api_key import APIKeyCreateRequest, APIKeyRecord

    record = APIKeyRecord(
        key_id="vf_key_abc",
        tenant_id="tenant-1",
        name="test",
        key_hash="a" * 64,
        prefix="vf_abc",
        role="analyst",
        permissions=["benchmarks:read"],
    )
    assert record.enabled is True
```

Run: `pytest services/api/app/tests/test_api_key_hash.py -v`

Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add services/api/app/models/api_key.py services/api/app/tests/test_api_key_hash.py
git commit -m "feat(api): gateway API-key models"
```

---

## Task 3: API-key repository

**Files:**
- Create: `services/api/app/repositories/api_key_repository.py`
- Test: `services/api/app/tests/test_api_key_repository.py`

- [ ] **Step 1: Write the failing test**

```python
# services/api/app/tests/test_api_key_repository.py
from uuid import uuid4

import pytest

from app.core.api_key_hash import generate_api_key
from app.models.api_key import APIKeyCreateRequest
from app.repositories.api_key_repository import APIKeyRepository


@pytest.fixture
def repo():
    return APIKeyRepository()


@pytest.fixture(autouse=True)
def _set_hmac_secret(monkeypatch):
    monkeypatch.setenv("API_KEY_HMAC_SECRET", "test-secret-for-hashing-only-32bytes")


def test_create_and_lookup_by_hash(repo):
    tenant_id = str(uuid4())
    raw, key_id, prefix = generate_api_key(name="test")
    record = repo.create_key(
        tenant_id=tenant_id,
        request=APIKeyCreateRequest(name="integration", role="analyst", permissions=["benchmarks:read"]),
        raw_key=raw,
        key_id=key_id,
        prefix=prefix,
    )
    assert record.key_id == key_id
    assert record.key_hash == repo._hash(raw)

    resolved = repo.get_by_hash(repo._hash(raw))
    assert resolved is not None
    assert resolved.tenant_id == tenant_id
    assert resolved.enabled is True


def test_lookup_missing_key_returns_none(repo):
    assert repo.get_by_hash("nonexistent") is None


def test_list_for_tenant(repo):
    tenant_id = str(uuid4())
    raw, key_id, prefix = generate_api_key(name="test")
    repo.create_key(
        tenant_id=tenant_id,
        request=APIKeyCreateRequest(name="a", role="read_only"),
        raw_key=raw,
        key_id=key_id,
        prefix=prefix,
    )
    items = repo.list_for_tenant(tenant_id)
    assert len(items) == 1
    assert items[0].name == "a"


def test_revoke_key(repo):
    tenant_id = str(uuid4())
    raw, key_id, prefix = generate_api_key(name="test")
    repo.create_key(
        tenant_id=tenant_id,
        request=APIKeyCreateRequest(name="revoke-me"),
        raw_key=raw,
        key_id=key_id,
        prefix=prefix,
    )
    assert repo.revoke_key(tenant_id, key_id) is True
    assert repo.get_by_hash(repo._hash(raw)) is None
```

Run: `pytest services/api/app/tests/test_api_key_repository.py -v`

Expected: `ModuleNotFoundError` for repository.

- [ ] **Step 2: Implement the repository**

```python
# services/api/app/repositories/api_key_repository.py
from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from app.core.api_key_hash import extract_key_prefix, generate_api_key, hash_api_key
from app.core.database import db
from app.models.api_key import APIKeyCreateRequest, APIKeyListItem, APIKeyRecord


class APIKeyRepository:
    """Gateway-local API key storage backed by the generic ``db`` facade.

    Records are keyed by ``key_id`` in the generic table; cross-tenant lookups
    by hash scan the (small) tenant-scoped set. A future optimization can add
    a Redis hash index keyed by key_hash.
    """

    def _hash(self, raw_key: str) -> str:
        return hash_api_key(raw_key)

    def _now(self) -> str:
        return datetime.now(UTC).isoformat()

    def create_key(
        self,
        *,
        tenant_id: str,
        request: APIKeyCreateRequest,
        raw_key: str | None = None,
        key_id: str | None = None,
        prefix: str | None = None,
        user_id: str | None = None,
    ) -> APIKeyRecord:
        if raw_key is None:
            raw_key, key_id, prefix = generate_api_key(name=request.name)
        record = APIKeyRecord(
            key_id=key_id or f"vf_key_{tenant_id[-8:]}",
            tenant_id=tenant_id,
            name=request.name,
            key_hash=self._hash(raw_key),
            prefix=prefix or extract_key_prefix(raw_key),
            role=request.role,
            permissions=request.permissions,
            created_at=self._now(),
        )
        db.api_keys.insert(record.key_id, record)
        return record

    def get_by_hash(self, key_hash: str) -> APIKeyRecord | None:
        """Lookup an active key by its HMAC hash.

        This is intentionally cross-tenant at the storage layer because the
        caller's tenant is not known until the key is resolved. Tenant isolation
        is enforced by returning only the record's own tenant scope to auth.
        """
        for record in db.api_keys.list(allow_system_scope=True, tenant_id="system"):
            if record.key_hash == key_hash:
                if not record.enabled or record.revoked_at:
                    return None
                return record
        return None

    def list_for_tenant(self, tenant_id: str) -> list[APIKeyListItem]:
        items = []
        for record in db.api_keys.list(tenant_id=tenant_id):
            items.append(
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
            )
        return items

    def revoke_key(self, tenant_id: str, key_id: str) -> bool:
        record = db.api_keys.get(key_id, tenant_id=tenant_id)
        if record is None:
            return False
        record.revoked_at = self._now()
        record.enabled = False
        db.api_keys.insert(record.key_id, record)
        return True
```

- [ ] **Step 3: Run tests**

Run: `pytest services/api/app/tests/test_api_key_repository.py -v`

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add services/api/app/repositories/api_key_repository.py services/api/app/tests/test_api_key_repository.py
git commit -m "feat(api): gateway API-key repository"
```

---

## Task 4: Add `api_keys` and `usage_events` tables to the gateway database

**Files:**
- Modify: `services/api/app/core/database.py`

- [ ] **Step 1: Modify `InMemoryDatabase.__init__`**

Add after the existing table initializations:

```python
self.api_keys = InMemoryTable("api_keys", tenant_field="key_id")
self.usage_events = AppendOnlyInMemoryTable("usage_events", tenant_field="tenant_id")
```

- [ ] **Step 2: Modify `PostgreSQLDatabase.__init__`**

Add after the existing table initializations:

```python
self.api_keys = PostgreSQLTable("api_keys", pool, tenant_field="key_id")
self.usage_events = AppendOnlyPostgreSQLTable("usage_events", pool, tenant_field="tenant_id")
```

- [ ] **Step 3: Write a smoke test**

```python
# services/api/app/tests/test_database_tables.py
from app.core.database import db


def test_api_keys_table_exists():
    assert hasattr(db, "api_keys")


def test_usage_events_table_exists():
    assert hasattr(db, "usage_events")
```

Run: `pytest services/api/app/tests/test_database_tables.py -v`

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add services/api/app/core/database.py services/api/app/tests/test_database_tables.py
git commit -m "feat(api): add api_keys and usage_events tables to gateway db"
```

---

## Task 5: API-key resolver for GovernanceMiddleware

**Files:**
- Create: `services/api/app/core/api_key_auth.py`
- Test: `services/api/app/tests/test_api_key_auth.py`

- [ ] **Step 1: Write the resolver and test**

```python
# services/api/app/core/api_key_auth.py
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
```

```python
# services/api/app/tests/test_api_key_auth.py
from uuid import uuid4

import pytest

from app.core.api_key_auth import resolve_api_key
from app.core.api_key_hash import generate_api_key
from app.models.api_key import APIKeyCreateRequest
from app.repositories.api_key_repository import APIKeyRepository


@pytest.fixture(autouse=True)
def _set_hmac_secret(monkeypatch):
    monkeypatch.setenv("API_KEY_HMAC_SECRET", "test-secret-for-hashing-only-32bytes")


@pytest.fixture
def repo():
    return APIKeyRepository()


async def test_resolve_api_key_returns_context(repo):
    tenant_id = str(uuid4())
    raw, key_id, prefix = generate_api_key(name="test")
    repo.create_key(
        tenant_id=tenant_id,
        request=APIKeyCreateRequest(name="resolver-test", role="analyst", permissions=["benchmarks:read"]),
        raw_key=raw,
        key_id=key_id,
        prefix=prefix,
    )
    ctx = await resolve_api_key(raw)
    assert ctx is not None
    assert ctx["tenant_id"] == tenant_id
    assert ctx["key_id"] == key_id
    assert "benchmarks:read" in ctx["permissions"]


async def test_resolve_invalid_key_returns_none():
    assert await resolve_api_key("not-a-key") is None


async def test_resolve_revoked_key_returns_none(repo):
    tenant_id = str(uuid4())
    raw, key_id, prefix = generate_api_key(name="test")
    repo.create_key(
        tenant_id=tenant_id,
        request=APIKeyCreateRequest(name="revoked"),
        raw_key=raw,
        key_id=key_id,
        prefix=prefix,
    )
    repo.revoke_key(tenant_id, key_id)
    assert await resolve_api_key(raw) is None
```

Run: `pytest services/api/app/tests/test_api_key_auth.py -v`

Expected: PASS.

- [ ] **Step 2: Commit**

```bash
git add services/api/app/core/api_key_auth.py services/api/app/tests/test_api_key_auth.py
git commit -m "feat(api): gateway API-key resolver"
```

---

## Task 6: Gateway governance helper that wires the resolver

**Files:**
- Create: `services/api/app/core/governance.py`
- Modify: `services/api/app/main.py` (replace `add_governance_middleware` call)
- Test: `services/api/app/tests/test_governance_api_key.py`

- [ ] **Step 1: Create gateway governance helper**

```python
# services/api/app/core/governance.py
from __future__ import annotations

from fastapi import FastAPI
from value_fabric.shared.identity.middleware import GovernanceMiddleware, audit_protected_routes

from app.core.api_key_auth import resolve_api_key


def add_gateway_governance_middleware(app: FastAPI, *, rate_limiter=None) -> None:
    """Install GovernanceMiddleware with gateway API-key resolution."""
    app.add_middleware(
        GovernanceMiddleware,
        api_key_resolver=resolve_api_key,
        rate_limiter=rate_limiter,
    )

    @app.on_event("startup")
    async def _audit_auth_routes() -> None:
        audit_protected_routes(app)
```

- [ ] **Step 2: Replace import and call in `main.py`**

Replace:

```python
from value_fabric.shared.fastapi_framework.middleware import add_governance_middleware
```

with:

```python
from app.core.governance import add_gateway_governance_middleware
```

Replace:

```python
add_governance_middleware(app, rate_limiter=None)
```

with:

```python
add_gateway_governance_middleware(app, rate_limiter=None)
```

- [ ] **Step 3: Write route-level API-key auth test**

```python
# services/api/app/tests/test_governance_api_key.py
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.api_key_hash import generate_api_key
from app.main import app
from app.models.api_key import APIKeyCreateRequest
from app.repositories.api_key_repository import APIKeyRepository


@pytest.fixture(autouse=True)
def _set_hmac_secret(monkeypatch):
    monkeypatch.setenv("API_KEY_HMAC_SECRET", "test-secret-for-hashing-only-32bytes")


@pytest.fixture
def api_key():
    tenant_id = str(uuid4())
    raw, key_id, prefix = generate_api_key(name="route-test")
    repo = APIKeyRepository()
    repo.create_key(
        tenant_id=tenant_id,
        request=APIKeyCreateRequest(name="route-test", role="analyst", permissions=["benchmarks:read"]),
        raw_key=raw,
        key_id=key_id,
        prefix=prefix,
    )
    return tenant_id, raw


def test_api_key_request_resolves_tenant(api_key):
    tenant_id, raw = api_key
    with TestClient(app) as client:
        response = client.get(
            "/v1/accounts",
            headers={"Authorization": f"Bearer {raw}", "X-Tenant-ID": tenant_id},
        )
    # 200 if the tenant has data; 404/empty list is also acceptable for this auth test.
    assert response.status_code in (200, 404)


def test_api_key_mismatched_tenant_header_is_blocked(api_key):
    tenant_id, raw = api_key
    with TestClient(app) as client:
        response = client.get(
            "/v1/accounts",
            headers={"Authorization": f"Bearer {raw}", "X-Tenant-ID": str(uuid4())},
        )
    assert response.status_code == 403


def test_missing_api_key_is_rejected():
    with TestClient(app) as client:
        response = client.get("/v1/accounts")
    assert response.status_code == 401
```

Run: `pytest services/api/app/tests/test_governance_api_key.py -v`

Expected: PASS (may need to exempt `/v1/accounts` from requiring data; the auth test only checks status codes).

- [ ] **Step 4: Commit**

```bash
git add services/api/app/core/governance.py services/api/app/main.py services/api/app/tests/test_governance_api_key.py
git commit -m "feat(api): wire API-key resolver into gateway governance middleware"
```

---

## Task 7: API-key management routes

**Files:**
- Create: `services/api/app/routers/api_keys.py`
- Modify: `services/api/app/main.py`
- Test: `services/api/app/tests/test_api_keys_routes.py`

- [ ] **Step 1: Implement management router**

```python
# services/api/app/routers/api_keys.py
from __future__ import annotations

from fastapi import APIRouter, Depends, status
from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.dependencies import require_authenticated, require_tenant_admin

from app.core.api_key_hash import generate_api_key
from app.models.api_key import (
    APIKeyCreateRequest,
    APIKeyCreateResponse,
    APIKeyListResponse,
)
from app.repositories.api_key_repository import APIKeyRepository

router = APIRouter(prefix="/auth/api-keys", tags=["API Keys"])


def _get_repo() -> APIKeyRepository:
    return APIKeyRepository()


@router.post("", response_model=APIKeyCreateResponse, status_code=status.HTTP_201_CREATED)
def create_api_key(
    request: APIKeyCreateRequest,
    ctx: RequestContext = Depends(require_tenant_admin),
    repo: APIKeyRepository = Depends(_get_repo),
) -> APIKeyCreateResponse:
    raw, key_id, prefix = generate_api_key(name=request.name)
    record = repo.create_key(
        tenant_id=str(ctx.tenant_id),
        request=request,
        raw_key=raw,
        key_id=key_id,
        prefix=prefix,
    )
    return APIKeyCreateResponse(
        key_id=record.key_id,
        name=record.name,
        api_key=raw,
        prefix=record.prefix,
        tenant_id=record.tenant_id,
        role=record.role,
        permissions=record.permissions,
        created_at=record.created_at,
    )


@router.get("", response_model=APIKeyListResponse)
def list_api_keys(
    ctx: RequestContext = Depends(require_authenticated),
    repo: APIKeyRepository = Depends(_get_repo),
) -> APIKeyListResponse:
    items = repo.list_for_tenant(str(ctx.tenant_id))
    return APIKeyListResponse(items=items)


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_api_key(
    key_id: str,
    ctx: RequestContext = Depends(require_tenant_admin),
    repo: APIKeyRepository = Depends(_get_repo),
) -> None:
    repo.revoke_key(str(ctx.tenant_id), key_id)
```

- [ ] **Step 2: Mount router in `main.py`**

Add after the auth router include:

```python
from app.routers import api_keys

app.include_router(auth.router, prefix="/v1")
app.include_router(api_keys.router, prefix="/v1")
```

- [ ] **Step 3: Write route tests**

```python
# services/api/app/tests/test_api_keys_routes.py
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.security import mint_token
from app.main import app


@pytest.fixture(autouse=True)
def _set_hmac_secret(monkeypatch):
    monkeypatch.setenv("API_KEY_HMAC_SECRET", "test-secret-for-hashing-only-32bytes")


def _admin_headers(tenant_id: str):
    token = mint_token(tenant_id=tenant_id, extra_claims={"roles": ["tenant_admin"]})
    return {"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id}


def test_create_api_key_returns_raw_key_once():
    tenant_id = str(uuid4())
    with TestClient(app) as client:
        response = client.post(
            "/v1/auth/api-keys",
            json={"name": "test-key", "role": "analyst", "permissions": ["benchmarks:read"]},
            headers=_admin_headers(tenant_id),
        )
    assert response.status_code == 201
    body = response.json()
    assert body["api_key"].startswith("vf_")
    assert body["tenant_id"] == tenant_id


def test_list_api_keys():
    tenant_id = str(uuid4())
    with TestClient(app) as client:
        client.post(
            "/v1/auth/api-keys",
            json={"name": "list-me"},
            headers=_admin_headers(tenant_id),
        )
        response = client.get("/v1/auth/api-keys", headers=_admin_headers(tenant_id))
    assert response.status_code == 200
    assert len(response.json()["items"]) == 1
```

Run: `pytest services/api/app/tests/test_api_keys_routes.py -v`

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add services/api/app/routers/api_keys.py services/api/app/main.py services/api/app/tests/test_api_keys_routes.py
git commit -m "feat(api): API-key management routes"
```

---

## Task 8: Usage metering

**Files:**
- Create: `services/api/app/core/usage_meter.py`
- Create: `services/api/app/models/usage_event.py`
- Modify: `services/api/app/core/database.py` (already done in Task 4)
- Test: `services/api/app/tests/test_usage_meter.py`

- [ ] **Step 1: Add usage event schema**

```python
# services/api/app/models/usage_event.py
from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field


class UsageEventRecord(BaseModel):
    event_id: str
    tenant_id: str
    api_key_id: str | None
    endpoint: str
    method: str
    product_code: str
    quantity: float = 1.0
    unit: str = "request"
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    metadata: dict | None = None
```

- [ ] **Step 2: Implement usage meter**

```python
# services/api/app/core/usage_meter.py
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from app.core.database import db
from app.models.usage_event import UsageEventRecord

if TYPE_CHECKING:
    from value_fabric.shared.identity.context import RequestContext


def record_usage(
    *,
    request,
    ctx: "RequestContext",
    product_code: str,
    quantity: float = 1.0,
    unit: str = "request",
    metadata: dict | None = None,
) -> UsageEventRecord:
    """Persist a usage event for the current request.

    Callers should invoke this after auth succeeds and before returning the
    response so the event carries accurate tenant/api-key context.
    """
    event = UsageEventRecord(
        event_id=str(uuid.uuid4()),
        tenant_id=str(ctx.tenant_id),
        api_key_id=str(ctx.api_key_id) if ctx.api_key_id else None,
        endpoint=request.url.path,
        method=request.method,
        product_code=product_code,
        quantity=quantity,
        unit=unit,
        metadata=metadata or {},
    )
    db.usage_events.insert(event.event_id, event)
    return event


def list_usage_events(tenant_id: str, *, limit: int = 100) -> list[UsageEventRecord]:
    return db.usage_events.list(tenant_id=tenant_id, limit=limit)
```

- [ ] **Step 3: Write test**

```python
# services/api/app/tests/test_usage_meter.py
from uuid import uuid4

from fastapi import Request
from starlette.datastructures import Headers

from app.core.usage_meter import record_usage
from app.models.usage_event import UsageEventRecord
from value_fabric.shared.identity.context import RequestContext


def _mock_request(path: str = "/v1/benchmarks", method: str = "GET") -> Request:
    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "headers": [],
        "query_string": b"",
    }
    return Request(scope)


def test_record_usage_persists_event():
    tenant_id = str(uuid4())
    ctx = RequestContext(tenant_id=tenant_id, source="api_key", api_key_id="vf_key_123")
    request = _mock_request()
    event = record_usage(request=request, ctx=ctx, product_code="benchmarks")
    assert event.tenant_id == tenant_id
    assert event.product_code == "benchmarks"
    assert event.quantity == 1.0
```

Run: `pytest services/api/app/tests/test_usage_meter.py -v`

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add services/api/app/models/usage_event.py services/api/app/core/usage_meter.py services/api/app/tests/test_usage_meter.py
git commit -m "feat(api): gateway usage metering"
```

---

## Task 9: Layer 6 client

**Files:**
- Create: `services/api/app/clients/layer6_client.py`
- Modify: `services/api/app/core/config.py`
- Test: `services/api/app/tests/test_layer6_client.py`

- [ ] **Step 1: Add Layer 6 base URL setting**

In `services/api/app/core/config.py`, add after `layer4_timeout_seconds`:

```python
layer6_api_base_url: str = "http://localhost:8006"
layer6_timeout_seconds: float = 10.0
```

Add to `.env.example`:

```bash
# Layer 6 Benchmarks Service
LAYER6_API_BASE_URL=http://localhost:8006
LAYER6_TIMEOUT_SECONDS=10.0
```

- [ ] **Step 2: Implement client**

```python
# services/api/app/clients/layer6_client.py
from __future__ import annotations

import os
from typing import Any

import httpx
from fastapi import HTTPException

from app.core.config import get_settings


class Layer6Client:
    """Internal client to the Layer 6 benchmarks service."""

    def __init__(self, base_url: str | None = None, timeout: float | None = None):
        settings = get_settings()
        self.base_url = (base_url or settings.layer6_api_base_url).rstrip("/")
        self.timeout = timeout or settings.layer6_timeout_seconds
        self.service_secret = os.environ.get("SERVICE_AUTH_SECRET", "")

    def _headers(self, tenant_id: str) -> dict[str, str]:
        return {
            "X-Tenant-ID": tenant_id,
            "X-Service-Auth": self.service_secret,
            "Content-Type": "application/json",
        }

    async def list_datasets(self, tenant_id: str) -> list[dict[str, Any]]:
        url = f"{self.base_url}/v1/benchmarks/datasets"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, headers=self._headers(tenant_id))
        if response.status_code != 200:
            raise HTTPException(status_code=502, detail="Layer 6 benchmarks unavailable")
        return response.json()

    async def compare(self, tenant_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.base_url}/v1/benchmarks/compare"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, json=payload, headers=self._headers(tenant_id))
        if response.status_code != 200:
            raise HTTPException(status_code=502, detail="Layer 6 comparison failed")
        return response.json()
```

- [ ] **Step 3: Write client unit test with `httpx.MockTransport`**

```python
# services/api/app/tests/test_layer6_client.py
import json

import httpx
import pytest

from app.clients.layer6_client import Layer6Client


@pytest.fixture
def mock_transport():
    def handler(request: httpx.Request):
        if request.url.path == "/v1/benchmarks/datasets":
            return httpx.Response(200, json=[{"dataset_id": "ds1"}])
        if request.url.path == "/v1/benchmarks/compare":
            return httpx.Response(200, json={"percentile": 50})
        return httpx.Response(404)

    return httpx.MockTransport(handler)


@pytest.mark.asyncio
async def test_list_datasets(mock_transport, monkeypatch):
    monkeypatch.setenv("SERVICE_AUTH_SECRET", "s" * 32)
    client = Layer6Client(base_url="http://layer6", timeout=1.0)
    result = await client.list_datasets("tenant-1")
    assert result == [{"dataset_id": "ds1"}]


@pytest.mark.asyncio
async def test_compare(mock_transport, monkeypatch):
    monkeypatch.setenv("SERVICE_AUTH_SECRET", "s" * 32)
    client = Layer6Client(base_url="http://layer6", timeout=1.0)
    result = await client.compare("tenant-1", {"dataset_id": "ds1", "metric": "revenue", "company_value": "100"})
    assert result["percentile"] == 50
```

Run: `pytest services/api/app/tests/test_layer6_client.py -v`

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add services/api/app/clients/layer6_client.py services/api/app/core/config.py .env.example services/api/app/tests/test_layer6_client.py
git commit -m "feat(api): Layer 6 benchmarks client"
```

---

## Task 10: `/v1/benchmarks` metered router

**Files:**
- Create: `services/api/app/routers/benchmarks.py`
- Modify: `services/api/app/main.py`
- Test: `services/api/app/tests/test_benchmarks_router.py`

- [ ] **Step 1: Implement router**

```python
# services/api/app/routers/benchmarks.py
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request
from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.dependencies import require_authenticated

from app.clients.layer6_client import Layer6Client
from app.core.usage_meter import record_usage
from app.models.schemas import PaginatedResponse

router = APIRouter(prefix="/benchmarks", tags=["Benchmarks"])


def _get_layer6_client() -> Layer6Client:
    return Layer6Client()


@router.get("", response_model=PaginatedResponse[dict[str, Any]])
async def list_benchmarks(
    request: Request,
    ctx: RequestContext = Depends(require_authenticated),
    client: Layer6Client = Depends(_get_layer6_client),
):
    datasets = await client.list_datasets(str(ctx.tenant_id))
    record_usage(request=request, ctx=ctx, product_code="benchmarks", quantity=1.0, unit="request")
    return PaginatedResponse(items=datasets, total=len(datasets), limit=100, offset=0)


@router.post("/compare")
async def compare_benchmarks(
    request: Request,
    payload: dict[str, Any],
    ctx: RequestContext = Depends(require_authenticated),
    client: Layer6Client = Depends(_get_layer6_client),
):
    result = await client.compare(str(ctx.tenant_id), payload)
    record_usage(request=request, ctx=ctx, product_code="benchmarks", quantity=1.0, unit="request")
    return result
```

- [ ] **Step 2: Mount router in `main.py`**

Add:

```python
from app.routers import benchmarks

app.include_router(benchmarks.router, prefix="/v1")
```

- [ ] **Step 3: Write route tests**

```python
# services/api/app/tests/test_benchmarks_router.py
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient

from app.core.api_key_hash import generate_api_key
from app.core.security import mint_token
from app.main import app
from app.models.api_key import APIKeyCreateRequest
from app.repositories.api_key_repository import APIKeyRepository


@pytest.fixture(autouse=True)
def _set_hmac_secret(monkeypatch):
    monkeypatch.setenv("API_KEY_HMAC_SECRET", "test-secret-for-hashing-only-32bytes")
    monkeypatch.setenv("SERVICE_AUTH_SECRET", "s" * 32)


@pytest.fixture
def api_key():
    tenant_id = str(uuid4())
    raw, key_id, prefix = generate_api_key(name="bench-test")
    repo = APIKeyRepository()
    repo.create_key(
        tenant_id=tenant_id,
        request=APIKeyCreateRequest(name="bench-test", role="analyst", permissions=["benchmarks:read"]),
        raw_key=raw,
        key_id=key_id,
        prefix=prefix,
    )
    return tenant_id, raw


def test_list_benchmarks_with_api_key(api_key, monkeypatch):
    tenant_id, raw = api_key

    def handler(request: httpx.Request):
        if request.url.path == "/v1/benchmarks/datasets":
            return httpx.Response(200, json=[{"dataset_id": "ds1"}])
        return httpx.Response(404)

    monkeypatch.setattr("httpx.AsyncClient", lambda *args, **kwargs: httpx.AsyncClient(transport=httpx.MockTransport(handler)))

    with TestClient(app) as client:
        response = client.get(
            "/v1/benchmarks",
            headers={"Authorization": f"Bearer {raw}", "X-Tenant-ID": tenant_id},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["items"]


def test_list_benchmarks_unauthenticated():
    with TestClient(app) as client:
        response = client.get("/v1/benchmarks")
    assert response.status_code == 401
```

Run: `pytest services/api/app/tests/test_benchmarks_router.py -v`

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add services/api/app/routers/benchmarks.py services/api/app/main.py services/api/app/tests/test_benchmarks_router.py
git commit -m "feat(api): metered /v1/benchmarks router proxying to Layer 6"
```

---

## Task 11: `/v1/usage` read-only routes

**Files:**
- Create: `services/api/app/routers/usage.py`
- Modify: `services/api/app/main.py`
- Test: `services/api/app/tests/test_usage_routes.py`

- [ ] **Step 1: Implement router**

```python
# services/api/app/routers/usage.py
from __future__ import annotations

from fastapi import APIRouter, Depends
from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.dependencies import require_authenticated

from app.core.usage_meter import list_usage_events

router = APIRouter(prefix="/usage", tags=["Usage"])


@router.get("")
def get_usage(
    ctx: RequestContext = Depends(require_authenticated),
    limit: int = 100,
):
    events = list_usage_events(str(ctx.tenant_id), limit=limit)
    return {
        "tenant_id": str(ctx.tenant_id),
        "events": [e.model_dump() for e in events],
        "total": len(events),
    }


@router.get("/quotas")
def get_quotas(ctx: RequestContext = Depends(require_authenticated)):
    # Phase 1: stub. Phase 3 will integrate BillingPlanVersion limits.
    return {
        "tenant_id": str(ctx.tenant_id),
        "quotas": {
            "benchmarks": {"limit": -1, "used": 0, "remaining": -1},
        },
    }
```

- [ ] **Step 2: Mount router in `main.py`**

```python
from app.routers import usage

app.include_router(usage.router, prefix="/v1")
```

- [ ] **Step 3: Write tests**

```python
# services/api/app/tests/test_usage_routes.py
from uuid import uuid4

from fastapi.testclient import TestClient

from app.core.security import mint_token
from app.main import app


def _headers(tenant_id: str):
    token = mint_token(tenant_id=tenant_id)
    return {"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id}


def test_get_usage_returns_events():
    tenant_id = str(uuid4())
    with TestClient(app) as client:
        response = client.get("/v1/usage", headers=_headers(tenant_id))
    assert response.status_code == 200
    assert response.json()["tenant_id"] == tenant_id


def test_get_quotas_stub():
    tenant_id = str(uuid4())
    with TestClient(app) as client:
        response = client.get("/v1/usage/quotas", headers=_headers(tenant_id))
    assert response.status_code == 200
    assert "benchmarks" in response.json()["quotas"]
```

Run: `pytest services/api/app/tests/test_usage_routes.py -v`

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add services/api/app/routers/usage.py services/api/app/main.py services/api/app/tests/test_usage_routes.py
git commit -m "feat(api): /v1/usage read-only routes"
```

---

## Task 12: Update OpenAPI contract

**Files:**
- Modify: `contracts/openapi/fabric-4l-api.json`

- [ ] **Step 1: Add new paths**

Add under `paths`:

```json
"/v1/auth/api-keys": {
  "post": {
    "tags": ["API Keys"],
    "summary": "Create an API key",
    "operationId": "createApiKey",
    "requestBody": {
      "required": true,
      "content": {
        "application/json": {
          "schema": { "$ref": "#/components/schemas/APIKeyCreateRequest" }
        }
      }
    },
    "responses": {
      "201": {
        "description": "API key created",
        "content": {
          "application/json": {
            "schema": { "$ref": "#/components/schemas/APIKeyCreateResponse" }
          }
        }
      }
    }
  },
  "get": {
    "tags": ["API Keys"],
    "summary": "List API keys",
    "operationId": "listApiKeys",
    "responses": {
      "200": {
        "description": "List of API keys",
        "content": {
          "application/json": {
            "schema": { "$ref": "#/components/schemas/APIKeyListResponse" }
          }
        }
      }
    }
  }
},
"/v1/benchmarks": {
  "get": {
    "tags": ["Benchmarks"],
    "summary": "List accessible benchmark datasets",
    "operationId": "listBenchmarks",
    "responses": {
      "200": {
        "description": "Paginated benchmark datasets",
        "content": {
          "application/json": {
            "schema": { "$ref": "#/components/schemas/PaginatedResponse" }
          }
        }
      }
    }
  }
},
"/v1/benchmarks/compare": {
  "post": {
    "tags": ["Benchmarks"],
    "summary": "Compare a company value against a benchmark dataset",
    "operationId": "compareBenchmarks",
    "requestBody": {
      "required": true,
      "content": {
        "application/json": {
          "schema": { "$ref": "#/components/schemas/BenchmarkComparisonRequest" }
        }
      }
    },
    "responses": {
      "200": {
        "description": "Comparison result",
        "content": {
          "application/json": {
            "schema": { "$ref": "#/components/schemas/BenchmarkComparisonResponse" }
          }
        }
      }
    }
  }
},
"/v1/usage": {
  "get": {
    "tags": ["Usage"],
    "summary": "Current-period usage events",
    "operationId": "getUsage",
    "responses": {
      "200": {
        "description": "Usage events",
        "content": {
          "application/json": {
            "schema": { "$ref": "#/components/schemas/UsageSummaryResponse" }
          }
        }
      }
    }
  }
}
```

- [ ] **Step 2: Add new components/schemas**

Add to `components/schemas`:

```json
"APIKeyCreateRequest": {
  "type": "object",
  "required": ["name"],
  "properties": {
    "name": { "type": "string", "minLength": 1, "maxLength": 100 },
    "role": { "type": "string", "enum": ["read_only", "analyst", "content_admin", "tenant_admin"] },
    "permissions": { "type": "array", "items": { "type": "string" } }
  }
},
"APIKeyCreateResponse": {
  "type": "object",
  "required": ["key_id", "name", "api_key", "prefix", "tenant_id", "role", "created_at"],
  "properties": {
    "key_id": { "type": "string" },
    "name": { "type": "string" },
    "api_key": { "type": "string" },
    "prefix": { "type": "string" },
    "tenant_id": { "type": "string" },
    "role": { "type": "string" },
    "permissions": { "type": "array", "items": { "type": "string" } },
    "created_at": { "type": "string", "format": "date-time" }
  }
},
"APIKeyListResponse": {
  "type": "object",
  "properties": {
    "items": { "type": "array", "items": { "$ref": "#/components/schemas/APIKeyListItem" } }
  }
},
"APIKeyListItem": {
  "type": "object",
  "properties": {
    "key_id": { "type": "string" },
    "name": { "type": "string" },
    "prefix": { "type": "string" },
    "role": { "type": "string" },
    "permissions": { "type": "array", "items": { "type": "string" } },
    "enabled": { "type": "boolean" },
    "created_at": { "type": "string", "format": "date-time" },
    "last_used_at": { "type": "string", "format": "date-time", "nullable": true }
  }
},
"BenchmarkComparisonRequest": {
  "type": "object",
  "required": ["dataset_id", "metric", "company_value", "industry"],
  "properties": {
    "dataset_id": { "type": "string" },
    "metric": { "type": "string" },
    "company_value": { "type": "string" },
    "industry": { "type": "string" },
    "segment": { "type": "string", "nullable": true }
  }
},
"BenchmarkComparisonResponse": {
  "type": "object",
  "properties": {
    "percentile": { "type": "integer" },
    "peer_median": { "type": "string" },
    "peer_range": { "type": "array", "items": { "type": "string" } },
    "sample_size": { "type": "integer" },
    "confidence": { "type": "string" },
    "assessment": { "type": "string" }
  }
},
"UsageSummaryResponse": {
  "type": "object",
  "properties": {
    "tenant_id": { "type": "string" },
    "events": { "type": "array", "items": { "type": "object" } },
    "total": { "type": "integer" }
  }
}
```

- [ ] **Step 3: Validate contract**

Run: `python scripts/ci/validate_openapi.py contracts/openapi/fabric-4l-api.json` (or the project's contract check command).

Expected: valid JSON and schema.

- [ ] **Step 4: Commit**

```bash
git add contracts/openapi/fabric-4l-api.json
git commit -m "docs(contract): add API keys, benchmarks, and usage paths to gateway OpenAPI"
```

---

## Task 13: Run the gateway test suite

- [ ] **Step 1: Run targeted tests**

```bash
cd services/api
pytest app/tests/test_api_key_hash.py app/tests/test_api_key_repository.py app/tests/test_api_key_auth.py app/tests/test_governance_api_key.py app/tests/test_api_keys_routes.py app/tests/test_usage_meter.py app/tests/test_usage_routes.py app/tests/test_layer6_client.py app/tests/test_benchmarks_router.py -v
```

Expected: all PASS.

- [ ] **Step 2: Run full gateway tests**

```bash
cd services/api
pytest app/tests -v
```

Expected: existing tests still PASS; new tests PASS.

- [ ] **Step 3: Commit any test/regression fixes**

```bash
git add -A
git commit -m "test(api): add Phase 1 monetization tests"
```

---

## Self-Review Checklist

- [ ] **Spec coverage:** Every Phase 1 requirement (API-key auth, usage metering, `/v1/benchmarks`, contract update, tests) has at least one task.
- [ ] **Placeholder scan:** No `TBD`, `TODO`, or vague steps remain.
- [ ] **Type consistency:** `APIKeyRecord`, `APIKeyCreateResponse`, resolver dict keys, and `UsageEventRecord` fields are consistent across tasks.
- [ ] **Security:** API-key hashing uses `API_KEY_HMAC_SECRET`; resolver rejects non-`vf_` keys; tenant header mismatch is blocked by existing middleware.
- [ ] **Testability:** Each task includes failing-test → implementation → passing-test steps.
