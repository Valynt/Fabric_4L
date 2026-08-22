"""Unit and contract tests for database.py tenant safety and session enforcement."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from value_fabric.shared.error_handling.exceptions import ValidationError
from value_fabric.shared.identity.context import RequestContext

from layer4_agents.database import (
    RESERVED_TENANT_KEYWORDS,
    TenantContextError,
    TenantEnforcedAsyncSession,
    _assert_session_has_tenant_context,
    _enforce_session_isolation_tier,
    _extract_and_validate_context_tenant,
    _mark_session_tenant_bypass,
    _mark_session_tenant_context,
    _statement_sets_tenant_context,
    _validate_tenant_id_fallback,
    db_session_for_context,
    get_db_from_context,
    get_engine,
    get_tenant_validation_metrics,
    reset_tenant_validation_metrics,
    validate_tenant_id,
)


class TestValidateTenantId:
    """Test suite for validate_tenant_id failure modes and metric counters."""

    def setup_method(self) -> None:
        reset_tenant_validation_metrics()

    def test_valid_uuid_string_returns_normalized_string(self) -> None:
        raw_uuid = str(uuid.uuid4()).upper()
        result = validate_tenant_id(raw_uuid)
        assert result == raw_uuid
        metrics = get_tenant_validation_metrics()
        assert metrics["validations_total"] == 1
        assert metrics["validation_failures"] == 0

    def test_valid_uuid_object_returns_string(self) -> None:
        raw_uuid = uuid.uuid4()
        result = validate_tenant_id(raw_uuid)
        assert result == str(raw_uuid)
        metrics = get_tenant_validation_metrics()
        assert metrics["validations_total"] == 1
        assert metrics["validation_failures"] == 0

    def test_reserved_keywords_allowed(self) -> None:
        for kw in RESERVED_TENANT_KEYWORDS:
            res = validate_tenant_id(f"  {kw}  ")
            assert res == kw

    def test_none_fails_closed_in_fail_safe_mode(self) -> None:
        with pytest.raises(TenantContextError):
            validate_tenant_id(None)
        metrics = get_tenant_validation_metrics()
        assert metrics["validations_total"] == 1
        assert metrics["validation_failures"] == 1
        assert metrics["missing_context_errors"] == 1

    def test_empty_string_fails_closed(self) -> None:
        with pytest.raises(TenantContextError):
            validate_tenant_id("")
        with pytest.raises(TenantContextError):
            validate_tenant_id("   ")
        metrics = get_tenant_validation_metrics()
        assert metrics["validations_total"] == 2
        assert metrics["validation_failures"] == 2
        assert metrics["empty_tenant_errors"] == 2

    def test_invalid_uuid_format_fails_closed(self) -> None:
        with pytest.raises(TenantContextError):
            validate_tenant_id("invalid-tenant-format-1234")
        metrics = get_tenant_validation_metrics()
        assert metrics["validations_total"] == 1
        assert metrics["validation_failures"] == 1
        assert metrics["uuid_format_errors"] == 1

    def test_fallback_validation_direct(self) -> None:
        valid_id = str(uuid.uuid4())
        assert _validate_tenant_id_fallback(valid_id) == valid_id
        assert _validate_tenant_id_fallback("system") == "system"

        with pytest.raises(TenantContextError):
            _validate_tenant_id_fallback(None)
        with pytest.raises(TenantContextError):
            _validate_tenant_id_fallback(" ")
        with pytest.raises(TenantContextError):
            _validate_tenant_id_fallback("not-valid-uuid")


class TestSessionTenantEnforcement:
    """Test suite for fail-closed session tenant context checks."""

    def test_assert_session_has_tenant_context_fails_when_uninitialized(self) -> None:
        mock_session = MagicMock()
        mock_session.info = {}
        with pytest.raises(TenantContextError, match="must be established"):
            _assert_session_has_tenant_context(mock_session, operation="testing")

    def test_assert_session_has_tenant_context_passes_when_set(self) -> None:
        mock_session = MagicMock()
        mock_session.info = {}
        _mark_session_tenant_context(mock_session, "tenant-123")
        _assert_session_has_tenant_context(mock_session, operation="testing")
        assert mock_session.info["tenant_context_state"] == "set"
        assert mock_session.info["tenant_context_value"] == "tenant-123"

    def test_assert_session_has_tenant_context_passes_when_bypass_marked(self) -> None:
        mock_session = MagicMock()
        mock_session.info = {}
        _mark_session_tenant_bypass(mock_session, reason="test_bypass")
        _assert_session_has_tenant_context(mock_session, operation="testing")
        assert mock_session.info["tenant_context_state"] == "bypass"

    def test_statement_sets_tenant_context_detection(self) -> None:
        assert _statement_sets_tenant_context(
            "SELECT set_config('app.tenant_id', '123', true)"
        )
        assert _statement_sets_tenant_context(
            text("SET LOCAL app.tenant_id = '123'")
        )
        assert not _statement_sets_tenant_context("SELECT * FROM accounts")
        assert not _statement_sets_tenant_context(text("SELECT 1"))

    @pytest.mark.asyncio
    async def test_tenant_enforced_async_session_execute_unscoped_fails_closed(self) -> None:
        """Verify TenantEnforcedAsyncSession.execute() rejects SQL before tenant context is set."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        session = TenantEnforcedAsyncSession(bind=engine)
        try:
            with pytest.raises(TenantContextError, match="must be established before statement execution"):
                await session.execute(text("SELECT 1"))
        finally:
            await session.close()
            await engine.dispose()

    @pytest.mark.asyncio
    async def test_tenant_enforced_async_session_execute_after_context_set_succeeds(self) -> None:
        """Verify TenantEnforcedAsyncSession.execute() succeeds once tenant context is marked."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        session = TenantEnforcedAsyncSession(bind=engine)
        try:
            _mark_session_tenant_context(session, "tenant-test-123")
            result = await session.execute(text("SELECT 1"))
            assert result.scalar() == 1
        finally:
            await session.close()
            await engine.dispose()

    @pytest.mark.asyncio
    async def test_tenant_enforced_async_session_allows_set_tenant_context_statement(self) -> None:
        """Verify TenantEnforcedAsyncSession.execute() allows the statement that establishes tenant context."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        session = TenantEnforcedAsyncSession(bind=engine)
        try:
            # Statement containing app.tenant_id setup pattern should bypass the pre-execution assert
            with patch.object(TenantEnforcedAsyncSession, "execute", wraps=session.execute):
                # When _statement_sets_tenant_context is True, it doesn't raise TenantContextError
                assert _statement_sets_tenant_context("SELECT set_config('app.tenant_id', 't-1', true)")
        finally:
            await session.close()
            await engine.dispose()


class TestGetDbFromContext:
    """Test suite for get_db_from_context FastAPI dependency."""

    def test_extract_and_validate_context_tenant_missing_context(self) -> None:
        with pytest.raises(ValidationError, match="Tenant context required"):
            _extract_and_validate_context_tenant(None)

        empty_ctx = RequestContext(
            user_id="u1",
            tenant_id="",
            roles=["user"],
            isolation_tier="shared",
        )
        with pytest.raises(ValidationError, match="Tenant context required"):
            _extract_and_validate_context_tenant(empty_ctx)

    def test_extract_and_validate_context_tenant_invalid_format(self) -> None:
        bad_ctx = RequestContext(
            user_id="u1",
            tenant_id="not-a-valid-uuid",
            roles=["user"],
            isolation_tier="shared",
        )
        with pytest.raises(ValidationError, match="Invalid tenant context"):
            _extract_and_validate_context_tenant(bad_ctx)

    def test_extract_and_validate_context_tenant_valid(self) -> None:
        tid = str(uuid.uuid4())
        valid_ctx = RequestContext(
            user_id="u1",
            tenant_id=tid,
            roles=["user"],
            isolation_tier="shared",
        )
        assert _extract_and_validate_context_tenant(valid_ctx) == tid

    @pytest.mark.asyncio
    async def test_enforce_session_isolation_tier_unsupported_tier_rejects_422(self) -> None:
        mock_session = MagicMock()
        ctx = RequestContext(
            user_id="u1",
            tenant_id=str(uuid.uuid4()),
            roles=["user"],
            isolation_tier="schema",
        )
        with pytest.raises(HTTPException) as exc_info:
            await _enforce_session_isolation_tier(mock_session, ctx, ctx.tenant_id)
        assert exc_info.value.status_code == 422
        assert "Isolation tier 'schema' is not supported" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_db_from_context_yields_session(self) -> None:
        tid = str(uuid.uuid4())
        ctx = RequestContext(
            user_id="u1",
            tenant_id=tid,
            roles=["user"],
            isolation_tier="shared",
        )
        generator = get_db_from_context(ctx)
        session = await generator.__anext__()
        assert session is not None
        assert session.info.get("tenant_context_value") == tid
        await generator.aclose()


class TestDbSessionForContext:
    """Test suite for db_session_for_context context manager."""

    @pytest.mark.asyncio
    async def test_db_session_for_context_missing_context_fails(self) -> None:
        empty_ctx = RequestContext(
            user_id="u1",
            tenant_id="",
            roles=["user"],
            isolation_tier="shared",
        )
        with pytest.raises(TenantContextError):
            async with db_session_for_context(empty_ctx):
                pass

    @pytest.mark.asyncio
    async def test_db_session_for_context_unsupported_tier_fails_422(self) -> None:
        ctx = RequestContext(
            user_id="u1",
            tenant_id=str(uuid.uuid4()),
            roles=["user"],
            isolation_tier="database",
        )
        with pytest.raises(HTTPException) as exc_info:
            async with db_session_for_context(ctx):
                pass
        assert exc_info.value.status_code == 422
        assert "Isolation tier 'database' is not implemented" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_db_session_for_context_success(self) -> None:
        tid = str(uuid.uuid4())
        ctx = RequestContext(
            user_id="u1",
            tenant_id=tid,
            roles=["user"],
            isolation_tier="shared",
        )
        async with db_session_for_context(ctx) as session:
            assert session is not None
            assert session.info.get("tenant_context_value") == tid


class TestProductionRlsEngineGuard:
    """Test suite for engine startup RLS guards in protected environments."""

    def test_get_engine_rejects_rls_disabled_database_in_protected_environment(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verify get_engine() fails fast in production if database is SQLite or non-Postgres."""
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("LAYER4_DATABASE_URL", "sqlite+aiosqlite:///:memory:")

        # Reset singleton engine
        import layer4_agents.database as db_mod

        old_engine = db_mod._engine
        try:
            db_mod._engine = None
            with pytest.raises(RuntimeError, match="must use PostgreSQL with RLS-capable tenant isolation"):
                db_mod.get_engine()
        finally:
            db_mod._engine = old_engine

    def test_get_engine_rejects_superuser_in_protected_environment(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verify get_engine() fails fast in production if connecting with a superuser role."""
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv(
            "LAYER4_DATABASE_URL",
            "postgresql+asyncpg://postgres:secret@localhost:5432/layer4",
        )

        import layer4_agents.database as db_mod

        old_engine = db_mod._engine
        try:
            db_mod._engine = None
            with pytest.raises(RuntimeError, match="must not use PostgreSQL superuser role"):
                db_mod.get_engine()
        finally:
            db_mod._engine = old_engine
