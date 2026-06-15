from __future__ import annotations

"""Phase 3 tests: Tier enforcement, usage tracking, and admin dashboard.

Tests are organized into three groups:
1. TierEnforcement — limit checks, feature gates, usage summary
2. UsageTrackingService — aggregation queries, daily breakdown, monthly counters
3. AdminDashboard — authorization, settings CRUD, branding feature gate

All tests use mock DB sessions to avoid infrastructure dependencies.
Tests are designed to FAIL initially until the application code is
correctly wired — per Agent Workflow Testing Best Practices.
"""


import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

# ── Fixtures ────────────────────────────────────────────────────────


@pytest.fixture
def tenant_id() -> UUID:
    return uuid4()


@pytest.fixture
def free_tier_id() -> str:
    return "free"


@pytest.fixture
def pro_tier_id() -> str:
    return "pro"


@pytest.fixture
def enterprise_tier_id() -> str:
    return "enterprise"


@pytest.fixture
def mock_db() -> AsyncMock:
    """Create a mock async DB session."""
    db = AsyncMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    return db


@pytest.fixture
def mock_context_admin(tenant_id: UUID) -> MagicMock:
    """Mock RequestContext for a tenant admin."""
    ctx = MagicMock()
    ctx.tenant_id = str(tenant_id)
    ctx.user_id = str(uuid4())
    ctx.roles = ["tenant_admin"]
    ctx.is_super_admin = MagicMock(return_value=False)
    return ctx


@pytest.fixture
def mock_context_super_admin() -> MagicMock:
    """Mock RequestContext for a super admin."""
    ctx = MagicMock()
    ctx.tenant_id = str(uuid4())
    ctx.user_id = str(uuid4())
    ctx.roles = ["super_admin"]
    ctx.is_super_admin = MagicMock(return_value=True)
    return ctx


# ═══════════════════════════════════════════════════════════════════
# 1. TIER ENFORCEMENT TESTS
# ═══════════════════════════════════════════════════════════════════


class TestTierConfiguration:
    """Test tier configuration and lookup."""

    def test_get_tier_config_free(self) -> None:
        from src.tenants.tiers import get_tier_config

        config = get_tier_config("free")
        assert config.id == "free"
        assert config.limits.max_users == 3
        assert config.limits.max_agents == 2
        assert config.features.custom_branding is False

    def test_get_tier_config_pro(self) -> None:
        from src.tenants.tiers import get_tier_config

        config = get_tier_config("pro")
        assert config.id == "pro"
        assert config.limits.max_users == 100
        assert config.features.sso_integration is True

    def test_get_tier_config_enterprise_unlimited(self) -> None:
        from src.tenants.tiers import get_tier_config

        config = get_tier_config("enterprise")
        assert config.limits.max_users is None  # Unlimited
        assert config.limits.max_agents is None

    def test_get_tier_config_unknown_raises(self) -> None:
        from src.tenants.tiers import get_tier_config

        with pytest.raises(ValueError, match="Unknown tier"):
            get_tier_config("nonexistent")

    def test_get_public_tiers_excludes_enterprise(self) -> None:
        from src.tenants.tiers import get_public_tiers

        public = get_public_tiers()
        ids = [t.id for t in public]
        assert "free" in ids
        assert "basic" in ids
        assert "pro" in ids
        assert "enterprise" not in ids

    def test_check_limit_within(self) -> None:
        from src.tenants.tiers import check_limit

        assert check_limit("free", "max_users", 2) is True

    def test_check_limit_at_boundary(self) -> None:
        from src.tenants.tiers import check_limit

        assert check_limit("free", "max_users", 3) is True  # <= 3

    def test_check_limit_exceeded(self) -> None:
        from src.tenants.tiers import check_limit

        assert check_limit("free", "max_users", 4) is False

    def test_check_limit_unlimited(self) -> None:
        from src.tenants.tiers import check_limit

        assert check_limit("enterprise", "max_users", 999999) is True


class TestTierEnforcement:
    """Test TierEnforcement service limit checks."""

    @pytest.mark.asyncio
    async def test_check_user_limit_within(
        self, mock_db: AsyncMock, tenant_id: UUID, free_tier_id: str,
    ) -> None:
        from src.tenants.tier_enforcement import TierEnforcement

        # Mock: 2 users exist (limit is 3)
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 2
        mock_db.execute.return_value = mock_result

        enforcer = TierEnforcement(mock_db)
        # Should not raise
        await enforcer.check_user_limit(tenant_id, free_tier_id)

    @pytest.mark.asyncio
    async def test_check_user_limit_exceeded(
        self, mock_db: AsyncMock, tenant_id: UUID, free_tier_id: str,
    ) -> None:
        from src.tenants.tier_enforcement import TierEnforcement, TierLimitExceeded

        # Mock: 3 users exist (limit is 3, at boundary)
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 3
        mock_db.execute.return_value = mock_result

        enforcer = TierEnforcement(mock_db)
        with pytest.raises(TierLimitExceeded) as exc_info:
            await enforcer.check_user_limit(tenant_id, free_tier_id)

        assert exc_info.value.status_code == 403
        assert "max_users" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_check_user_limit_enterprise_unlimited(
        self, mock_db: AsyncMock, tenant_id: UUID, enterprise_tier_id: str,
    ) -> None:
        from src.tenants.tier_enforcement import TierEnforcement

        enforcer = TierEnforcement(mock_db)
        # Should not raise — enterprise has no user limit
        await enforcer.check_user_limit(tenant_id, enterprise_tier_id)
        # DB should not be queried for unlimited tiers
        mock_db.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_check_monthly_api_calls_exceeded(
        self, mock_db: AsyncMock, tenant_id: UUID, free_tier_id: str,
    ) -> None:
        from src.tenants.tier_enforcement import TierEnforcement, TierLimitExceeded

        enforcer = TierEnforcement(mock_db)
        with pytest.raises(TierLimitExceeded) as exc_info:
            await enforcer.check_monthly_api_calls(
                tenant_id, free_tier_id, current_month_calls=1001,
            )

        assert "monthly_api_calls" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_check_monthly_api_calls_within(
        self, mock_db: AsyncMock, tenant_id: UUID, free_tier_id: str,
    ) -> None:
        from src.tenants.tier_enforcement import TierEnforcement

        enforcer = TierEnforcement(mock_db)
        # Should not raise — 500 < 1000 limit
        await enforcer.check_monthly_api_calls(
            tenant_id, free_tier_id, current_month_calls=500,
        )

    def test_check_feature_enabled(self) -> None:
        from src.tenants.tier_enforcement import TierEnforcement

        enforcer = TierEnforcement(MagicMock())
        assert enforcer.check_feature("pro", "custom_branding") is True

    def test_check_feature_disabled(self) -> None:
        from src.tenants.tier_enforcement import TierEnforcement

        enforcer = TierEnforcement(MagicMock())
        assert enforcer.check_feature("free", "custom_branding") is False

    def test_require_feature_raises_when_disabled(self) -> None:
        from fastapi import HTTPException
        from src.tenants.tier_enforcement import TierEnforcement

        enforcer = TierEnforcement(MagicMock())
        with pytest.raises(HTTPException) as exc_info:
            enforcer.require_feature("free", "sso_integration")

        assert exc_info.value.status_code == 403
        assert "feature_not_available" in str(exc_info.value.detail)

    def test_require_feature_passes_when_enabled(self) -> None:
        from src.tenants.tier_enforcement import TierEnforcement

        enforcer = TierEnforcement(MagicMock())
        # Should not raise
        enforcer.require_feature("pro", "sso_integration")


class TestTierLimitExceeded:
    """Test the TierLimitExceeded exception structure."""

    def test_error_response_shape(self) -> None:
        from src.tenants.tier_enforcement import TierLimitExceeded

        exc = TierLimitExceeded(
            limit_name="max_users",
            current_value=3,
            max_value=3,
            tier_id="free",
        )
        assert exc.status_code == 403
        assert exc.detail["error"] == "tier_limit_exceeded"
        assert exc.detail["limit"] == "max_users"
        assert exc.detail["current"] == 3
        assert exc.detail["max"] == 3
        assert exc.detail["tier"] == "free"
        assert "Upgrade" in exc.detail["message"]


# ═══════════════════════════════════════════════════════════════════
# 2. USAGE TRACKING TESTS
# ═══════════════════════════════════════════════════════════════════


class TestUsageTrackingService:
    """Test UsageTrackingService aggregation methods."""

    @pytest.mark.asyncio
    async def test_get_usage_summary_returns_dataclass(
        self, mock_db: AsyncMock, tenant_id: UUID,
    ) -> None:
        from src.tenants.usage_tracking import UsageSummary, UsageTrackingService

        # Mock all queries to return 0
        mock_scalar = MagicMock()
        mock_scalar.scalar_one_or_none.return_value = 0
        mock_scalar.fetchone.return_value = (0, 0, 0)
        mock_db.execute.return_value = mock_scalar

        service = UsageTrackingService(mock_db)
        summary = await service.get_usage_summary(tenant_id, days=30)

        assert isinstance(summary, UsageSummary)
        assert summary.tenant_id == tenant_id
        assert summary.api_calls_total == 0
        assert summary.llm_tokens_input == 0

    @pytest.mark.asyncio
    async def test_get_current_month_api_calls(
        self, mock_db: AsyncMock, tenant_id: UUID,
    ) -> None:
        from src.tenants.usage_tracking import UsageTrackingService

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = 42
        mock_db.execute.return_value = mock_result

        service = UsageTrackingService(mock_db)
        count = await service.get_current_month_api_calls(tenant_id)
        assert count == 42

    @pytest.mark.asyncio
    async def test_get_daily_usage_returns_list(
        self, mock_db: AsyncMock, tenant_id: UUID,
    ) -> None:
        from src.tenants.usage_tracking import DailyUsage, UsageTrackingService

        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            ("2026-04-20", 10, 5, 1000),
            ("2026-04-21", 15, 3, 2000),
        ]
        mock_db.execute.return_value = mock_result

        service = UsageTrackingService(mock_db)
        daily = await service.get_daily_usage(tenant_id, days=7)

        assert len(daily) == 2
        assert isinstance(daily[0], DailyUsage)
        assert daily[0].api_calls == 10
        assert daily[1].llm_tokens == 2000

    @pytest.mark.asyncio
    async def test_get_top_endpoints(
        self, mock_db: AsyncMock, tenant_id: UUID,
    ) -> None:
        from src.tenants.usage_tracking import UsageTrackingService

        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            ("/api/v1/agents", 100, 5),
            ("/api/v1/entities", 50, 3),
        ]
        mock_db.execute.return_value = mock_result

        service = UsageTrackingService(mock_db)
        endpoints = await service.get_top_endpoints(tenant_id, days=30, limit=10)

        assert len(endpoints) == 2
        assert endpoints[0]["endpoint"] == "/api/v1/agents"
        assert endpoints[0]["call_count"] == 100

    @pytest.mark.asyncio
    async def test_graceful_degradation_on_missing_table(
        self, mock_db: AsyncMock, tenant_id: UUID,
    ) -> None:
        """Usage tracking should return zeros if audit_events table doesn't exist."""
        from src.tenants.usage_tracking import UsageTrackingService

        mock_db.execute.side_effect = Exception("relation 'audit_events' does not exist")

        service = UsageTrackingService(mock_db)
        daily = await service.get_daily_usage(tenant_id, days=7)
        assert daily == []

        endpoints = await service.get_top_endpoints(tenant_id)
        assert endpoints == []

    @pytest.mark.asyncio
    async def test_llm_cost_estimate(
        self, mock_db: AsyncMock, tenant_id: UUID,
    ) -> None:
        """Verify LLM cost estimate calculation."""
        from src.tenants.usage_tracking import UsageTrackingService

        # Mock: count events returns 0, LLM usage returns tokens
        call_count = 0
        call_idx = [0]

        async def mock_execute(query, params=None):
            result = MagicMock()
            call_idx[0] += 1
            # The _get_llm_usage call returns a row with tokens
            if "tokens_input" in str(query):
                result.fetchone.return_value = (10000, 5000, 50)
            else:
                result.scalar_one_or_none.return_value = 0
                result.fetchall.return_value = []
            return result

        mock_db.execute = mock_execute

        service = UsageTrackingService(mock_db)
        summary = await service.get_usage_summary(tenant_id, days=30)

        # Cost = (10000/1000 * 0.0005) + (5000/1000 * 0.0015) = 5.0 + 7.5 = 12.5
        assert summary.llm_tokens_input == 10000
        assert summary.llm_tokens_output == 5000
        expected_cost = (10000 / 1000) * 0.0005 + (5000 / 1000) * 0.0015
        assert abs(summary.llm_cost_estimate_usd - expected_cost) < 0.001


# ═══════════════════════════════════════════════════════════════════
# 3. ADMIN DASHBOARD AUTHORIZATION TESTS
# ═══════════════════════════════════════════════════════════════════


class TestAdminDashboardAuthorization:
    """Test authorization logic for admin dashboard endpoints."""

    def test_authorize_own_tenant(
        self, mock_context_admin: MagicMock, tenant_id: UUID,
    ) -> None:
        from layer4_agents.tenants.api.routes.admin_dashboard import _authorize_tenant_access

        # Should not raise — accessing own tenant
        _authorize_tenant_access(mock_context_admin, tenant_id)

    def test_authorize_other_tenant_denied(
        self, mock_context_admin: MagicMock,
    ) -> None:
        from fastapi import HTTPException
        from src.tenants.api.routes.admin_dashboard import _authorize_tenant_access

        other_tenant = uuid4()
        with pytest.raises(HTTPException) as exc_info:
            _authorize_tenant_access(mock_context_admin, other_tenant)

        assert exc_info.value.status_code == 403
        assert "access_denied" in str(exc_info.value.detail)

    def test_authorize_super_admin_any_tenant(
        self, mock_context_super_admin: MagicMock,
    ) -> None:
        from layer4_agents.tenants.api.routes.admin_dashboard import _authorize_tenant_access

        any_tenant = uuid4()
        # Should not raise — super admin can access any tenant
        _authorize_tenant_access(mock_context_super_admin, any_tenant)


class TestSettingsFeatureGate:
    """Test that branding updates require the custom_branding feature."""

    def test_branding_blocked_on_free_tier(self) -> None:
        from fastapi import HTTPException
        from src.tenants.tier_enforcement import TierEnforcement

        enforcer = TierEnforcement(MagicMock())
        with pytest.raises(HTTPException) as exc_info:
            enforcer.require_feature("free", "custom_branding")

        assert exc_info.value.details["error"] == "feature_not_available"
        assert exc_info.value.details["feature"] == "custom_branding"

    def test_branding_allowed_on_pro_tier(self) -> None:
        from src.tenants.tier_enforcement import TierEnforcement

        enforcer = TierEnforcement(MagicMock())
        # Should not raise
        enforcer.require_feature("pro", "custom_branding")

    def test_sso_blocked_on_basic_tier(self) -> None:
        from fastapi import HTTPException
        from src.tenants.tier_enforcement import TierEnforcement

        enforcer = TierEnforcement(MagicMock())
        with pytest.raises(HTTPException):
            enforcer.require_feature("basic", "sso_integration")
        assert exc_info.value.details["error"] == "feature_not_available"
        assert exc_info.value.details["feature"] == "sso_integration"

    def test_audit_export_allowed_on_basic_tier(self) -> None:
        from src.tenants.tier_enforcement import TierEnforcement

        enforcer = TierEnforcement(MagicMock())
        # audit_export is True for basic
        enforcer.require_feature("basic", "audit_export")


# ═══════════════════════════════════════════════════════════════════
# 4. TIER USAGE SUMMARY TESTS
# ═══════════════════════════════════════════════════════════════════


class TestTierUsageSummary:
    """Test the get_usage_summary method on TierEnforcement."""

    @pytest.mark.asyncio
    async def test_usage_summary_structure(
        self, mock_db: AsyncMock, tenant_id: UUID, free_tier_id: str,
    ) -> None:
        from src.tenants.tier_enforcement import TierEnforcement

        # Mock count queries to return 1
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 1
        mock_db.execute.return_value = mock_result

        enforcer = TierEnforcement(mock_db)
        summary = await enforcer.get_usage_summary(tenant_id, free_tier_id)

        assert summary["tier"] == "free"
        assert summary["tier_name"] == "Free"
        assert "limits" in summary
        assert "features" in summary
        assert summary["limits"]["users"]["max"] == 3
        assert summary["features"]["custom_branding"] is False

    @pytest.mark.asyncio
    async def test_usage_summary_enterprise_unlimited(
        self, mock_db: AsyncMock, tenant_id: UUID, enterprise_tier_id: str,
    ) -> None:
        from src.tenants.tier_enforcement import TierEnforcement

        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 50
        mock_db.execute.return_value = mock_result

        enforcer = TierEnforcement(mock_db)
        summary = await enforcer.get_usage_summary(tenant_id, enterprise_tier_id)

        assert summary["limits"]["users"]["unlimited"] is True
        assert summary["limits"]["users"]["max"] is None
        assert summary["features"]["sso_integration"] is True
