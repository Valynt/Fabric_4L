from __future__ import annotations

"""DB-backed integration tests for the current-user profile endpoints."""

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.postgres,
]

from collections.abc import AsyncGenerator
from uuid import UUID

import psycopg  # noqa: F401
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from value_fabric.shared.error_handling import register_exception_handlers
from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.dependencies import require_authenticated
from value_fabric.shared.identity.permissions import Permission, Role

from layer4_agents.database import Base, _mark_session_tenant_context, get_db_from_context
from layer4_agents.tenants.api.routes.users import router as users_router
from layer4_agents.tenants.models.tenant import Tenant
from layer4_agents.tenants.models.user import User

_test_app = FastAPI()
register_exception_handlers(_test_app)

from fastapi import Depends as ProbeDepends


@_test_app.get("/probe")
async def probe(
    db: AsyncSession = ProbeDepends(get_db_from_context),
    ctx: RequestContext = ProbeDepends(require_authenticated),
):
    return {"user_id": ctx.user_id, "tenant_id": ctx.tenant_id, "db_ok": db is not None}


_test_app.include_router(users_router, prefix="/v1", tags=["Users"])

TEST_TENANT_ID = "11111111-1111-1111-1111-111111111111"
TEST_USER_ID = "00000000-0000-0000-0000-000000000042"


@pytest_asyncio.fixture(scope="function")
async def test_db(postgres_container) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session with fresh tables."""
    host = postgres_container.get_container_host_ip()
    port = postgres_container.get_exposed_port(5432)
    username = postgres_container.username
    password = postgres_container.password
    dbname = postgres_container.dbname

    test_database_url = f"postgresql+asyncpg://{username}:{password}@{host}:{port}/{dbname}"

    engine = create_async_engine(test_database_url, echo=False)
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
async def seeded_user(test_db: AsyncSession) -> User:
    """Create a tenant and a user in the test database."""
    tenant = Tenant(
        id=UUID(TEST_TENANT_ID),
        name="Test Tenant",
        slug="test-tenant-users-me",
        status="active",
    )
    user = User(
        id=UUID(TEST_USER_ID),
        tenant_id=UUID(TEST_TENANT_ID),
        email="ada@example.com",
        email_hash="dummy-hash",
        display_name="Ada Lovelace",
        role=Role.ANALYST.value,
        status="active",
    )
    test_db.add(tenant)
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest_asyncio.fixture
async def client(test_db: AsyncSession, seeded_user: User) -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client with DB and auth overrides."""

    async def override_get_db():
        yield test_db

    async def override_auth():
        return RequestContext(
            tenant_id=TEST_TENANT_ID,
            user_id=TEST_USER_ID,
            roles=[Role.ANALYST.value],
            permissions=frozenset({Permission.READ_AGENTS.value}),
            source="jwt",
        )

    _test_app.dependency_overrides[get_db_from_context] = override_get_db
    _test_app.dependency_overrides[require_authenticated] = override_auth

    try:
        async with AsyncClient(
            transport=ASGITransport(app=_test_app), base_url="http://test"
        ) as ac:
            yield ac
    finally:
        _test_app.dependency_overrides.clear()


async def test_probe(client: AsyncClient) -> None:
    response = await client.get("/probe")
    print("PROBE response:", response.status_code, response.text)


async def test_service_get_current_user_direct(test_db: AsyncSession, seeded_user: User) -> None:
    from layer4_agents.tenants.service import get_user

    user = await get_user(test_db, UUID(TEST_TENANT_ID), UUID(TEST_USER_ID))
    assert user is not None
    assert user.display_name == "Ada Lovelace"


async def test_get_current_user_returns_authenticated_user(client: AsyncClient) -> None:
    response = await client.get("/v1/users/me")
    if response.status_code != 200:
        print("GET /me response:", response.status_code, response.text)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == TEST_USER_ID
    assert data["email"] == "ada@example.com"
    assert data["display_name"] == "Ada Lovelace"
    assert data["role"] == Role.ANALYST.value


async def test_patch_current_user_updates_display_name(
    client: AsyncClient, test_db: AsyncSession
) -> None:
    response = await client.patch("/v1/users/me", json={"display_name": "Grace Hopper"})
    assert response.status_code == 200
    data = response.json()
    assert data["display_name"] == "Grace Hopper"

    # Verify persistence with a fresh fetch
    get_response = await client.get("/v1/users/me")
    assert get_response.json()["display_name"] == "Grace Hopper"


async def test_patch_current_user_rejects_role_change(client: AsyncClient) -> None:
    response = await client.patch(
        "/v1/users/me", json={"display_name": "Ada", "role": "tenant_admin"}
    )
    assert response.status_code == 403


async def test_patch_current_user_rejects_status_change(client: AsyncClient) -> None:
    response = await client.patch(
        "/v1/users/me", json={"display_name": "Ada", "status": "deactivated"}
    )
    assert response.status_code == 403
