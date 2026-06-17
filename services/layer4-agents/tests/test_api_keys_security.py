from __future__ import annotations

"""Security regression tests for API key lifecycle.

Covers the invariants flagged in the settings-area hardening review:
- Raw keys are returned once and never stored in plain text
- Keys are tenant-scoped and cannot be managed across tenants
- Role escalation is blocked at the service and route layers
- Expiry timestamps are persisted
- Create/revoke operations emit audit events
"""

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.postgres,
]

from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from value_fabric.shared.audit.models import AuditAction
from value_fabric.shared.error_handling import register_exception_handlers
from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.dependencies import (
    require_authenticated,
    require_tenant_admin,
)
from value_fabric.shared.identity.hashing import (
    extract_key_prefix,
    verify_api_key,
)
from value_fabric.shared.identity.models import APIKeyCreateRequest
from value_fabric.shared.identity.permissions import Permission, Role

from layer4_agents.database import Base, _mark_session_tenant_context, get_db_from_context
from layer4_agents.tenants.api.routes.api_keys import router as api_keys_router
from layer4_agents.tenants.models.api_key import APIKey
from layer4_agents.tenants.models.tenant import Tenant
from layer4_agents.tenants.models.user import User
from layer4_agents.tenants.service import create_api_key, lookup_api_key_by_hash

_test_app = FastAPI()
register_exception_handlers(_test_app)
_test_app.include_router(api_keys_router, prefix="/v1", tags=["API Keys"])

TEST_TENANT_ID = "11111111-1111-1111-1111-111111111111"
TEST_TENANT_B_ID = "22222222-2222-2222-2222-222222222222"
TEST_ADMIN_ID = "00000000-0000-0000-0000-000000000001"
TEST_ANALYST_ID = "00000000-0000-0000-0000-000000000002"


def _admin_context(tenant_id: str = TEST_TENANT_ID) -> RequestContext:
    return RequestContext(
        tenant_id=tenant_id,
        user_id=TEST_ADMIN_ID,
        roles=[Role.TENANT_ADMIN.value],
        permissions=frozenset({Permission.ADMIN_API_KEYS.value}),
        source="jwt",
    )


def _analyst_context(tenant_id: str = TEST_TENANT_ID) -> RequestContext:
    return RequestContext(
        tenant_id=tenant_id,
        user_id=TEST_ANALYST_ID,
        roles=[Role.ANALYST.value],
        permissions=frozenset({Permission.READ_AGENTS.value}),
        source="jwt",
    )


@pytest_asyncio.fixture(scope="function")
async def test_db(postgres_container) -> AsyncGenerator[AsyncSession, None]:
    host = postgres_container.get_container_host_ip()
    port = postgres_container.get_exposed_port(5432)
    url = (
        f"postgresql+asyncpg://{postgres_container.username}:"
        f"{postgres_container.password}@{host}:{port}/{postgres_container.dbname}"
    )
    engine = create_async_engine(url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        _mark_session_tenant_context(session, TEST_TENANT_ID)
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def seeded_tenants(test_db: AsyncSession) -> tuple[Tenant, Tenant]:
    tenant_a = Tenant(
        id=UUID(TEST_TENANT_ID),
        name="Tenant A",
        slug="tenant-a",
        status="active",
    )
    tenant_b = Tenant(
        id=UUID(TEST_TENANT_B_ID),
        name="Tenant B",
        slug="tenant-b",
        status="active",
    )
    test_db.add(tenant_a)
    test_db.add(tenant_b)
    await test_db.commit()
    return tenant_a, tenant_b


@pytest_asyncio.fixture
async def seeded_admin(test_db: AsyncSession, seeded_tenants: tuple[Tenant, Tenant]) -> User:
    user = User(
        id=UUID(TEST_ADMIN_ID),
        tenant_id=UUID(TEST_TENANT_ID),
        email="admin@example.com",
        email_hash="admin-hash",
        display_name="Admin User",
        role=Role.TENANT_ADMIN.value,
        status="active",
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest_asyncio.fixture
async def seeded_analyst(test_db: AsyncSession, seeded_tenants: tuple[Tenant, Tenant]) -> User:
    user = User(
        id=UUID(TEST_ANALYST_ID),
        tenant_id=UUID(TEST_TENANT_ID),
        email="analyst@example.com",
        email_hash="analyst-hash",
        display_name="Analyst User",
        role=Role.ANALYST.value,
        status="active",
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest_asyncio.fixture
async def admin_client(
    test_db: AsyncSession, seeded_admin: User
) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield test_db

    _test_app.dependency_overrides[get_db_from_context] = override_get_db
    _test_app.dependency_overrides[require_tenant_admin] = lambda: _admin_context()

    try:
        async with AsyncClient(
            transport=ASGITransport(app=_test_app), base_url="http://test"
        ) as ac:
            yield ac
    finally:
        _test_app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def analyst_client(
    test_db: AsyncSession, seeded_analyst: User
) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield test_db

    _test_app.dependency_overrides[get_db_from_context] = override_get_db
    _test_app.dependency_overrides[require_authenticated] = lambda: _analyst_context()

    try:
        async with AsyncClient(
            transport=ASGITransport(app=_test_app), base_url="http://test"
        ) as ac:
            yield ac
    finally:
        _test_app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Service-layer security invariants
# ---------------------------------------------------------------------------


async def test_create_api_key_service_stores_hash_not_raw(
    test_db: AsyncSession, seeded_admin: User
) -> None:
    request = APIKeyCreateRequest(name="Test Key", role=Role.ANALYST)
    response = await create_api_key(
        test_db,
        UUID(TEST_TENANT_ID),
        request,
        user_id=UUID(TEST_ADMIN_ID),
        creator_role=Role.TENANT_ADMIN,
    )

    raw_key = response.api_key
    assert raw_key.startswith("vf_")
    assert len(raw_key) > len("vf_")

    result = await test_db.execute(select(APIKey).where(APIKey.key_id == response.key_id))
    row = result.scalar_one()

    # The raw key must never be persisted.
    assert row.key_hash != raw_key
    assert raw_key not in (row.name, row.prefix or "")
    assert verify_api_key(raw_key, row.key_hash)
    assert row.prefix == extract_key_prefix(raw_key)
    assert row.tenant_id == UUID(TEST_TENANT_ID)
    assert row.creator_user_id == UUID(TEST_ADMIN_ID)


async def test_create_api_key_service_rejects_role_escalation(
    test_db: AsyncSession, seeded_admin: User
) -> None:
    from value_fabric.shared.error_handling.exceptions import AuthorizationError

    # tenant_admin cannot mint another tenant_admin key.
    with pytest.raises(AuthorizationError):
        await create_api_key(
            test_db,
            UUID(TEST_TENANT_ID),
            APIKeyCreateRequest(name="Escalation", role=Role.TENANT_ADMIN),
            user_id=UUID(TEST_ADMIN_ID),
            creator_role=Role.TENANT_ADMIN,
        )

    # analyst cannot mint a content_admin key.
    with pytest.raises(AuthorizationError):
        await create_api_key(
            test_db,
            UUID(TEST_TENANT_ID),
            APIKeyCreateRequest(name="Escalation", role=Role.CONTENT_ADMIN),
            user_id=UUID(TEST_ANALYST_ID),
            creator_role=Role.ANALYST,
        )


async def test_create_api_key_service_persists_expiry(
    test_db: AsyncSession, seeded_admin: User
) -> None:
    expires = datetime.now(UTC) + timedelta(days=30)
    request = APIKeyCreateRequest(name="Expiring Key", role=Role.ANALYST, expires_at=expires)
    response = await create_api_key(
        test_db,
        UUID(TEST_TENANT_ID),
        request,
        user_id=UUID(TEST_ADMIN_ID),
        creator_role=Role.TENANT_ADMIN,
    )

    result = await test_db.execute(select(APIKey).where(APIKey.key_id == response.key_id))
    row = result.scalar_one()
    assert row.expires_at is not None
    assert abs((row.expires_at - expires).total_seconds()) < 1


async def test_lookup_api_key_by_hash_rejects_expired_keys(
    test_db: AsyncSession, seeded_admin: User
) -> None:
    expired = datetime.now(UTC) - timedelta(hours=1)
    response = await create_api_key(
        test_db,
        UUID(TEST_TENANT_ID),
        APIKeyCreateRequest(name="Expired", role=Role.ANALYST, expires_at=expired),
        user_id=UUID(TEST_ADMIN_ID),
        creator_role=Role.TENANT_ADMIN,
    )

    found = await lookup_api_key_by_hash(test_db, response.api_key)
    assert found is None


async def test_create_api_key_service_rejects_cross_tenant_creator(
    test_db: AsyncSession, seeded_tenants: tuple[Tenant, Tenant]
) -> None:
    from value_fabric.shared.error_handling.exceptions import TenantIsolationError

    other_user = User(
        id=uuid4(),
        tenant_id=UUID(TEST_TENANT_B_ID),
        email="other@example.com",
        email_hash="other-hash",
        role=Role.TENANT_ADMIN.value,
        status="active",
    )
    test_db.add(other_user)
    await test_db.commit()

    with pytest.raises(TenantIsolationError):
        await create_api_key(
            test_db,
            UUID(TEST_TENANT_ID),
            APIKeyCreateRequest(name="Cross-tenant Key", role=Role.ANALYST),
            user_id=other_user.id,
            creator_role=Role.TENANT_ADMIN,
        )


# ---------------------------------------------------------------------------
# Route-layer security invariants
# ---------------------------------------------------------------------------


async def test_create_api_key_route_emits_audit_event(
    admin_client: AsyncClient, test_db: AsyncSession
) -> None:
    with patch(
        "layer4_agents.tenants.api.routes.api_keys.emit_audit_event",
        new_callable=AsyncMock,
    ) as emit_mock:
        response = await admin_client.post(
            "/v1/api-keys", json={"name": "Audit Key", "role": "analyst"}
        )

    assert response.status_code == 201
    data = response.json()
    emit_mock.assert_awaited_once()
    call_kwargs = emit_mock.await_args.kwargs
    assert call_kwargs["action"] == AuditAction.API_KEY_CREATED
    assert call_kwargs["actor_id"] == TEST_ADMIN_ID
    assert str(call_kwargs["tenant_id"]) == TEST_TENANT_ID
    assert call_kwargs["resource_type"] == "api_key"
    assert call_kwargs["resource_id"] == data["key_id"]


async def test_revoke_api_key_route_emits_audit_event(
    admin_client: AsyncClient, test_db: AsyncSession
) -> None:
    create_resp = await admin_client.post(
        "/v1/api-keys", json={"name": "Revoke Me", "role": "analyst"}
    )
    assert create_resp.status_code == 201
    key_id = create_resp.json()["key_id"]

    with patch(
        "layer4_agents.tenants.api.routes.api_keys.emit_audit_event",
        new_callable=AsyncMock,
    ) as emit_mock:
        revoke_resp = await admin_client.delete(f"/v1/api-keys/{key_id}")

    assert revoke_resp.status_code == 204
    emit_mock.assert_awaited_once()
    call_kwargs = emit_mock.await_args.kwargs
    assert call_kwargs["action"] == AuditAction.API_KEY_REVOKED
    assert call_kwargs["resource_id"] == key_id


async def test_api_keys_are_tenant_isolated(
    admin_client: AsyncClient,
    test_db: AsyncSession,
    seeded_tenants: tuple[Tenant, Tenant],
) -> None:
    # Create a key in tenant A via the service directly.
    key = await create_api_key(
        test_db,
        UUID(TEST_TENANT_ID),
        APIKeyCreateRequest(name="Tenant A Key", role=Role.ANALYST),
        user_id=UUID(TEST_ADMIN_ID),
        creator_role=Role.TENANT_ADMIN,
    )

    # Listing from tenant A returns the key.
    list_a = await admin_client.get("/v1/api-keys")
    assert list_a.status_code == 200
    assert any(k["key_id"] == key.key_id for k in list_a.json())

    # Listing from tenant B returns nothing.
    _test_app.dependency_overrides[require_tenant_admin] = lambda: _admin_context(TEST_TENANT_B_ID)
    try:
        list_b = await admin_client.get("/v1/api-keys")
        assert list_b.status_code == 200
        assert not any(k["key_id"] == key.key_id for k in list_b.json())

        # Revoking the other tenant's key from tenant B fails closed.
        revoke_resp = await admin_client.delete(f"/v1/api-keys/{key.key_id}")
        assert revoke_resp.status_code == 404
    finally:
        _test_app.dependency_overrides[require_tenant_admin] = lambda: _admin_context()


async def test_analyst_cannot_create_api_key(
    analyst_client: AsyncClient,
) -> None:
    response = await analyst_client.post(
        "/v1/api-keys", json={"name": "Analyst Key", "role": "analyst"}
    )
    assert response.status_code == 403


async def test_list_api_keys_never_returns_raw_secret(
    admin_client: AsyncClient,
) -> None:
    create_resp = await admin_client.post(
        "/v1/api-keys", json={"name": "List Check", "role": "analyst"}
    )
    assert create_resp.status_code == 201
    raw_key = create_resp.json()["api_key"]

    list_resp = await admin_client.get("/v1/api-keys")
    assert list_resp.status_code == 200
    for key in list_resp.json():
        assert "api_key" not in key
        assert raw_key not in str(key.values())
