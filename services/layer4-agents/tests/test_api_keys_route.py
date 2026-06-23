from __future__ import annotations

"""Integration tests for the API key management routes.

These tests exercise the full Layer 4 API key lifecycle through the FastAPI
router with a real async SQLite database. They verify:

- raw keys are returned only once at creation time
- the database stores a hash, never the plaintext key
- list endpoints never expose secrets
- tenant isolation on create/list/revoke
- role constraints (low-priv users cannot mint admin keys)
- expiry and revocation block authentication
- audit events are emitted for create/revoke/use
"""

import os
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from uuid import UUID

os.environ.setdefault("API_KEY_HMAC_SECRET", "test-api-key-secret")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret")
os.environ.setdefault("SERVICE_AUTH_SECRET", "test-service-auth-secret")
os.environ.setdefault("CREDENTIALS_MASTER_KEY", "test-credentials-master-key")

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from value_fabric.shared.error_handling import register_exception_handlers
from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.dependencies import require_tenant_admin
from value_fabric.shared.identity.hashing import verify_api_key
from value_fabric.shared.identity.models import APIKeyCreateRequest
from value_fabric.shared.identity.permissions import Role

from layer4_agents.database import Base, _mark_session_tenant_context, get_db_from_context
from layer4_agents.tenants.api.routes import api_keys as api_keys_router
from layer4_agents.tenants.models.api_key import APIKey
from layer4_agents.tenants.models.tenant import Tenant, TenantStatus
from layer4_agents.tenants.models.user import User
from layer4_agents.tenants.service import (
    create_api_key,
    lookup_api_key_by_hash,
)

TENANT_A = UUID("12345678-1234-1234-1234-123456789abc")
TENANT_B = UUID("abcdefab-1234-1234-1234-abcdefabcdef")
USER_A = UUID("11111111-1111-1111-1111-111111111111")
USER_B = UUID("22222222-2222-2222-2222-222222222222")

# These are API route integration tests that require a PostgreSQL testcontainer.
pytestmark = [
    pytest.mark.integration,
    pytest.mark.postgres,
]


@pytest.fixture(name="engine")
async def _engine(postgres_container):
    """Create an async engine pointing at the shared PostgreSQL test container."""
    url = postgres_container.get_connection_url().replace("+psycopg2", "+asyncpg")
    engine = create_async_engine(
        url,
        future=True,
        poolclass=NullPool,
    )
    # Import tenant models so their tables register with Base.metadata.
    from layer4_agents.tenants import models as _tenant_models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture(name="session_factory")
async def _session_factory(engine):
    """Session factory bound to the test engine."""
    factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )
    yield factory


@pytest.fixture(autouse=True)
async def _clean_api_key_tables(session_factory):
    """Truncate the tables touched by these tests between test cases."""
    yield
    async with session_factory() as session:
        _mark_session_tenant_context(session, "00000000-0000-0000-0000-000000000000")
        await session.execute(
            APIKey.__table__.delete()
        )
        await session.execute(
            User.__table__.delete()
        )
        await session.execute(
            Tenant.__table__.delete()
        )
        await session.commit()


@asynccontextmanager
async def scoped_session(session_factory, tenant_id: UUID):
    """Open a session and mark it with the requested tenant context."""
    async with session_factory() as session:
        _mark_session_tenant_context(session, str(tenant_id))
        yield session
        await session.commit()


def make_db_override(session_factory, tenant_id: UUID):
    """Build a dependency override for ``get_db_from_context``."""

    async def _override():
        async with session_factory() as session:
            _mark_session_tenant_context(session, str(tenant_id))
            yield session
            await session.commit()

    return _override


def build_app(
    tenant_id: UUID = TENANT_A,
    user_id: UUID = USER_A,
    roles: list[Role] | None = None,
) -> FastAPI:
    """Build a test FastAPI app with the API key router and injected context."""
    if roles is None:
        roles = [Role.TENANT_ADMIN]

    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(api_keys_router.router, prefix="/v1")

    app.dependency_overrides[require_tenant_admin] = lambda: RequestContext(
        tenant_id=str(tenant_id),
        user_id=str(user_id),
        roles=[r.value for r in roles],
    )

    return app


async def seed_tenant_and_user(
    session: AsyncSession,
    tenant_id: UUID,
    user_id: UUID,
    email: str = "admin@tenant-a.test",
    role: Role = Role.TENANT_ADMIN,
) -> None:
    """Create a tenant and a user belonging to it."""
    tenant = Tenant(
        id=tenant_id,
        name=f"Tenant {tenant_id}",
        slug=f"tenant-{tenant_id.hex[:8]}",
        status=TenantStatus.ACTIVE.value,
        settings={},
    )
    user = User(
        id=user_id,
        tenant_id=tenant_id,
        email=email,
        role=role.value,
        status="active",
    )
    session.add_all([tenant, user])
    await session.flush()


class TestCreateApiKey:
    async def test_create_returns_raw_key_once_and_stores_hash(
        self, session_factory
    ):
        async with scoped_session(session_factory, TENANT_A) as session:
            await seed_tenant_and_user(session, TENANT_A, USER_A)

        app = build_app()
        app.dependency_overrides[get_db_from_context] = make_db_override(
            session_factory, TENANT_A
        )

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/v1/api-keys",
                json={"name": "Production CI", "role": "analyst"},
            )

        assert response.status_code == 201
        body = response.json()
        assert body["name"] == "Production CI"
        assert body["role"] == "analyst"
        raw_key = body["api_key"]
        assert raw_key.startswith("vf_")
        assert body["prefix"] == raw_key[:12]

        # Verify the database stores a hash, not the raw key.
        async with scoped_session(session_factory, TENANT_A) as session:
            result = await session.execute(
                APIKey.__table__.select().where(APIKey.key_id == body["key_id"])
            )
            row = result.mappings().one()
            assert row["key_hash"] != raw_key
            assert verify_api_key(raw_key, row["key_hash"])
            assert row["creator_user_id"] == USER_A
            assert row["tenant_id"] == TENANT_A

        # List endpoint must never expose the raw secret.
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            listed = await client.get("/v1/api-keys")

        assert listed.status_code == 200
        items = listed.json()
        assert len(items) == 1
        assert "api_key" not in items[0]
        assert items[0]["prefix"] == raw_key[:12]

    async def test_create_emits_audit_event(self, session_factory):
        async with scoped_session(session_factory, TENANT_A) as session:
            await seed_tenant_and_user(session, TENANT_A, USER_A)

        app = build_app()
        app.dependency_overrides[get_db_from_context] = make_db_override(
            session_factory, TENANT_A
        )

        with patch.object(
            api_keys_router, "emit_audit_event", new_callable=AsyncMock
        ) as mock_emit:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/v1/api-keys",
                    json={"name": "Audited Key", "role": "analyst"},
                )

        assert response.status_code == 201
        mock_emit.assert_awaited_once()
        call_kwargs = mock_emit.await_args.kwargs
        assert call_kwargs["action"].value == "api_key.created"
        assert call_kwargs["tenant_id"] == str(TENANT_A)
        assert call_kwargs["resource_id"] == response.json()["key_id"]


class TestTenantIsolation:
    async def test_list_is_tenant_scoped(self, session_factory):
        async with scoped_session(session_factory, TENANT_A) as session:
            await seed_tenant_and_user(session, TENANT_A, USER_A)
            await seed_tenant_and_user(
                session, TENANT_B, USER_B, email="admin@tenant-b.test"
            )
            key = await create_api_key(
                session,
                TENANT_A,
                APIKeyCreateRequest(name="Tenant A Key", role=Role.ANALYST),
                user_id=USER_A,
            )
            await session.commit()

        tenant_a_app = build_app(TENANT_A, USER_A)
        tenant_a_app.dependency_overrides[get_db_from_context] = make_db_override(
            session_factory, TENANT_A
        )
        tenant_b_app = build_app(TENANT_B, USER_B)
        tenant_b_app.dependency_overrides[get_db_from_context] = make_db_override(
            session_factory, TENANT_B
        )

        async with AsyncClient(
            transport=ASGITransport(app=tenant_a_app), base_url="http://test"
        ) as client_a:
            a_list = await client_a.get("/v1/api-keys")

        async with AsyncClient(
            transport=ASGITransport(app=tenant_b_app), base_url="http://test"
        ) as client_b:
            b_list = await client_b.get("/v1/api-keys")

        assert a_list.status_code == 200
        assert len(a_list.json()) == 1
        assert a_list.json()[0]["key_id"] == key.key_id

        assert b_list.status_code == 200
        assert b_list.json() == []

    async def test_revoke_is_tenant_scoped(self, session_factory):
        async with scoped_session(session_factory, TENANT_A) as session:
            await seed_tenant_and_user(session, TENANT_A, USER_A)
            await seed_tenant_and_user(
                session, TENANT_B, USER_B, email="admin@tenant-b.test"
            )
            key = await create_api_key(
                session,
                TENANT_A,
                APIKeyCreateRequest(name="Tenant A Key", role=Role.ANALYST),
                user_id=USER_A,
            )
            await session.commit()

        tenant_b_app = build_app(TENANT_B, USER_B)
        tenant_b_app.dependency_overrides[get_db_from_context] = make_db_override(
            session_factory, TENANT_B
        )

        async with AsyncClient(
            transport=ASGITransport(app=tenant_b_app), base_url="http://test"
        ) as client_b:
            revoke_resp = await client_b.delete(f"/v1/api-keys/{key.key_id}")

        assert revoke_resp.status_code == 404


class TestRoleEnforcement:
    async def test_low_privilege_user_cannot_create_admin_key(
        self, session_factory
    ):
        async with scoped_session(session_factory, TENANT_A) as session:
            await seed_tenant_and_user(
                session, TENANT_A, USER_A, role=Role.ANALYST
            )

        app = build_app(roles=[Role.ANALYST])
        app.dependency_overrides[get_db_from_context] = make_db_override(
            session_factory, TENANT_A
        )

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/v1/api-keys",
                json={"name": "Escalation Attempt", "role": "tenant_admin"},
            )

        assert response.status_code == 403
        error = response.json()["error"]
        message = error["message"].lower()
        assert "role" in message or "authorize" in message or "permission" in message


class TestRevocationAndExpiry:
    async def test_revoked_key_cannot_authenticate(
        self, session_factory
    ):
        async with scoped_session(session_factory, TENANT_A) as session:
            await seed_tenant_and_user(session, TENANT_A, USER_A)
            created = await create_api_key(
                session,
                TENANT_A,
                APIKeyCreateRequest(name="To Revoke", role=Role.ANALYST),
                user_id=USER_A,
            )
            await session.commit()

        app = build_app()
        app.dependency_overrides[get_db_from_context] = make_db_override(
            session_factory, TENANT_A
        )

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            revoke_resp = await client.delete(f"/v1/api-keys/{created.key_id}")
            assert revoke_resp.status_code == 204

            active_list = await client.get("/v1/api-keys?active_only=true")
            all_list = await client.get("/v1/api-keys?active_only=false")

        assert active_list.status_code == 200
        assert active_list.json() == []
        assert len(all_list.json()) == 1
        assert all_list.json()[0]["enabled"] is False
        assert all_list.json()[0]["revoked_at"] is not None

        async with scoped_session(session_factory, TENANT_A) as session:
            assert await lookup_api_key_by_hash(session, created.api_key) is None

    async def test_expired_key_cannot_authenticate(
        self, session_factory
    ):
        async with scoped_session(session_factory, TENANT_A) as session:
            await seed_tenant_and_user(session, TENANT_A, USER_A)
            created = await create_api_key(
                session,
                TENANT_A,
                APIKeyCreateRequest(
                    name="Expired",
                    role=Role.ANALYST,
                    expires_at=datetime.now(UTC) - timedelta(minutes=1),
                ),
                user_id=USER_A,
            )
            await session.commit()

        app = build_app()
        app.dependency_overrides[get_db_from_context] = make_db_override(
            session_factory, TENANT_A
        )

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            active_list = await client.get("/v1/api-keys?active_only=true")
            all_list = await client.get("/v1/api-keys?active_only=false")

        assert active_list.status_code == 200
        assert active_list.json() == []
        assert len(all_list.json()) == 1
        assert all_list.json()[0]["expires_at"] is not None

        async with scoped_session(session_factory, TENANT_A) as session:
            assert await lookup_api_key_by_hash(session, created.api_key) is None

    async def test_revoke_emits_audit_event(self, session_factory):
        async with scoped_session(session_factory, TENANT_A) as session:
            await seed_tenant_and_user(session, TENANT_A, USER_A)
            created = await create_api_key(
                session,
                TENANT_A,
                APIKeyCreateRequest(name="Revoke Audit", role=Role.ANALYST),
                user_id=USER_A,
            )
            await session.commit()

        app = build_app()
        app.dependency_overrides[get_db_from_context] = make_db_override(
            session_factory, TENANT_A
        )

        with patch.object(
            api_keys_router, "emit_audit_event", new_callable=AsyncMock
        ) as mock_emit:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                revoke_resp = await client.delete(f"/v1/api-keys/{created.key_id}")

        assert revoke_resp.status_code == 204
        mock_emit.assert_awaited_once()
        call_kwargs = mock_emit.await_args.kwargs
        assert call_kwargs["action"].value == "api_key.revoked"
        assert call_kwargs["tenant_id"] == str(TENANT_A)


class TestLookupAndUsage:
    async def test_lookup_updates_last_used_at_and_emits_used_audit(
        self, session_factory
    ):
        async with scoped_session(session_factory, TENANT_A) as session:
            await seed_tenant_and_user(session, TENANT_A, USER_A)
            created = await create_api_key(
                session,
                TENANT_A,
                APIKeyCreateRequest(name="Usage Key", role=Role.ANALYST),
                user_id=USER_A,
            )
            await session.commit()

        with patch.object(
            __import__("layer4_agents.tenants.service", fromlist=["emit_audit_event"]),
            "emit_audit_event",
            new_callable=AsyncMock,
        ) as mock_emit:
            async with scoped_session(session_factory, TENANT_A) as session:
                resolved = await lookup_api_key_by_hash(session, created.api_key)
                await session.commit()

        assert resolved is not None
        assert resolved["tenant_id"] == str(TENANT_A)
        assert resolved["role"] == Role.ANALYST.value

        async with scoped_session(session_factory, TENANT_A) as session:
            result = await session.execute(
                APIKey.__table__.select().where(APIKey.key_id == created.key_id)
            )
            row = result.mappings().one()
            assert row["last_used_at"] is not None

        mock_emit.assert_awaited_once()
        call_kwargs = mock_emit.await_args.kwargs
        assert call_kwargs["action"].value == "api_key.used"
        assert call_kwargs["tenant_id"] == str(TENANT_A)
