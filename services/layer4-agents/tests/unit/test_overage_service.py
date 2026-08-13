from __future__ import annotations

"""
Unit tests for OverageService.

Tests the pure-Python helpers and the plan-limits query
without requiring a live database.
"""


from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from layer4_agents.services.overage_service import OverageService, UsageCheckResult

# ──────────────────────────────────────────────────────────────────────────────
# _get_period_dates
# ──────────────────────────────────────────────────────────────────────────────

class TestGetPeriodDates:
    """Tests for the period date calculation helper."""

    def _svc(self) -> OverageService:
        db = MagicMock()
        return OverageService(db=db, tenant_id="tenant-123")

    @pytest.mark.unit
    def test_monthly_period_starts_first_of_month(self):
        svc = self._svc()
        start, end = svc._get_period_dates("monthly")
        now = datetime.now(UTC)
        assert start.day == 1
        assert start.month == now.month
        assert start.hour == 0 and start.minute == 0 and start.second == 0

    @pytest.mark.unit
    def test_monthly_period_end_is_start_of_next_month(self):
        svc = self._svc()
        start, end = svc._get_period_dates("monthly")
        # end must be after start and at the next month boundary
        assert end > start
        assert end.day == 1
        if start.month == 12:
            assert end.year == start.year + 1
            assert end.month == 1
        else:
            assert end.month == start.month + 1

    @pytest.mark.unit
    def test_yearly_period_starts_jan_first(self):
        svc = self._svc()
        start, end = svc._get_period_dates("yearly")
        now = datetime.now(UTC)
        assert start.year == now.year
        assert start.month == 1
        assert start.day == 1

    @pytest.mark.unit
    def test_yearly_period_end_is_start_of_next_year(self):
        svc = self._svc()
        start, end = svc._get_period_dates("yearly")
        assert end.year == start.year + 1
        assert end.month == 1
        assert end.day == 1

    @pytest.mark.unit
    def test_default_period_is_last_30_days(self):
        svc = self._svc()
        start, end = svc._get_period_dates("unknown_period")
        diff = end - start
        # Should be approximately 30 days
        assert 29 <= diff.days <= 30

    @pytest.mark.unit
    def test_december_monthly_wraps_to_january(self):
        """December edge case: end month rolls to January of next year."""
        svc = self._svc()
        # Simulate December by patching datetime.now
        fixed_now = datetime(2025, 12, 15, 10, 30, 0, tzinfo=UTC)
        with patch(
            "layer4_agents.services.overage_service.datetime"
        ) as mock_dt:
            mock_dt.now.return_value = fixed_now
            # Replicate the replace calls to make datetime.now().replace work
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
            start, end = svc._get_period_dates("monthly")

        # Verify December -> January rollover
        assert start.month == 12
        assert end.year == 2026
        assert end.month == 1


# ──────────────────────────────────────────────────────────────────────────────
# get_plan_limits
# ──────────────────────────────────────────────────────────────────────────────

class TestGetPlanLimits:
    """Tests for get_plan_limits (synchronous)."""

    def _svc(self) -> OverageService:
        db = MagicMock()
        return OverageService(db=db, tenant_id="tenant-abc")

    @pytest.mark.unit
    def test_free_plan_has_limits(self):
        svc = self._svc()
        limits = svc.get_plan_limits("free")
        # Returns a TypedDictModel; verify it is non-empty by checking dict representation
        assert len(limits.model_dump()) > 0

    @pytest.mark.unit
    def test_unknown_plan_returns_empty(self):
        svc = self._svc()
        limits = svc.get_plan_limits("nonexistent-plan-xyz")
        # Returns a TypedDictModel with no fields set
        assert limits.model_dump() == {}

    @pytest.mark.unit
    def test_plan_limits_contain_expected_fields(self):
        """Each limit entry should have the standard fields."""
        svc = self._svc()
        limits_model = svc.get_plan_limits("free")
        for _metric, limit_data in limits_model.model_dump().items():
            assert "included_amount" in limit_data
            assert "period" in limit_data
            assert "overage_rate" in limit_data
            assert "hard_limit" in limit_data
            assert "warning_threshold" in limit_data


# ──────────────────────────────────────────────────────────────────────────────
# check_metric_usage — no plan configured
# ──────────────────────────────────────────────────────────────────────────────

class TestCheckMetricUsageNoPlan:
    """Tests for check_metric_usage when no plan / limit is found."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_no_plan_returns_unlimited_result(self):
        svc = OverageService(db=MagicMock(), tenant_id="t1")

        with patch.object(svc, "_get_customer_plan", new=AsyncMock(return_value=None)):
            result = await svc.check_metric_usage("cust-1", "api_calls")

        assert result.limit == float("inf")
        assert result.limit_exceeded is False
        assert result.warning_triggered is False
        assert result.overage_cost == 0.0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_plan_without_metric_limit_returns_unlimited(self):
        """Plan exists but has no limit for the requested metric."""
        from layer4_agents.config.plans import Plan

        plan = Plan(id="pro", name="Pro", description="Pro plan", usage_limits={})
        db = MagicMock()
        db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))
        svc = OverageService(db=db, tenant_id="t1")
        svc.plan_versions.get_subscription_plan_version = AsyncMock(return_value=None)

        with patch.object(svc, "_get_customer_plan", new=AsyncMock(return_value=plan)):
            result = await svc.check_metric_usage("cust-1", "some_metric")

        assert result.limit == float("inf")
        assert result.limit_exceeded is False


# ──────────────────────────────────────────────────────────────────────────────
# validate_request
# ──────────────────────────────────────────────────────────────────────────────

class TestValidateRequest:
    """Tests for the validate_request method."""

    def _svc(self) -> OverageService:
        return OverageService(db=MagicMock(), tenant_id="t1")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_allowed_when_under_limit(self):
        svc = self._svc()
        under_limit_result = UsageCheckResult(
            metric_name="api_calls",
            current_usage=50.0,
            limit=100.0,
            percentage_used=50.0,
            remaining=50.0,
            overage=0.0,
            warning_triggered=False,
            limit_exceeded=False,
            overage_cost=0.0,
            period_start=datetime.now(UTC),
            period_end=datetime.now(UTC),
        )

        with patch.object(svc, "check_metric_usage", new=AsyncMock(return_value=under_limit_result)):
            result = await svc.validate_request("cust-1", "api_calls", 1.0)

        assert result["allowed"] is True
        assert "error" not in result

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_denied_when_limit_exceeded(self):
        svc = self._svc()
        over_limit_result = UsageCheckResult(
            metric_name="api_calls",
            current_usage=100.0,
            limit=100.0,
            percentage_used=105.0,
            remaining=0.0,
            overage=5.0,
            warning_triggered=True,
            limit_exceeded=True,
            overage_cost=0.5,
            period_start=datetime.now(UTC),
            period_end=datetime.now(UTC),
        )

        with patch.object(svc, "check_metric_usage", new=AsyncMock(return_value=over_limit_result)):
            result = await svc.validate_request("cust-1", "api_calls", 1.0)

        assert result["allowed"] is False
        assert result["upgrade_required"] is True
        assert "api_calls" in result["error"]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_warning_present_near_limit(self):
        svc = self._svc()
        near_limit_result = UsageCheckResult(
            metric_name="api_calls",
            current_usage=85.0,
            limit=100.0,
            percentage_used=85.0,
            remaining=15.0,
            overage=0.0,
            warning_triggered=True,
            limit_exceeded=False,
            overage_cost=0.0,
            period_start=datetime.now(UTC),
            period_end=datetime.now(UTC),
        )

        with patch.object(svc, "check_metric_usage", new=AsyncMock(return_value=near_limit_result)):
            result = await svc.validate_request("cust-1", "api_calls", 1.0)

        assert result["allowed"] is True
        assert "warning" in result


# ──────────────────────────────────────────────────────────────────────────────
# check_all_limits
# ──────────────────────────────────────────────────────────────────────────────

class TestCheckAllLimits:
    """Tests for the check_all_limits method."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_no_plan_returns_ok_response(self):
        svc = OverageService(db=MagicMock(), tenant_id="t1")

        with patch.object(svc, "_get_customer_plan", new=AsyncMock(return_value=None)):
            response = await svc.check_all_limits("cust-1")

        assert response.all_limits_ok is True
        assert response.checks == []
        assert response.total_overage_cost == 0.0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_all_limits_ok_when_no_exceedance(self):
        from layer4_agents.config.plans import Plan, UsageLimit

        plan = Plan(
            id="free",
            name="Free",
            description="Free",
            usage_limits={
                "api_calls": UsageLimit(
                    metric_name="api_calls",
                    included_amount=1000,
                    period="monthly",
                    overage_rate=0.01,
                    hard_limit=True,
                    warning_threshold=80.0,
                )
            },
        )
        svc = OverageService(db=MagicMock(), tenant_id="t1")

        ok_check = UsageCheckResult(
            metric_name="api_calls",
            current_usage=100.0,
            limit=1000.0,
            percentage_used=10.0,
            remaining=900.0,
            overage=0.0,
            warning_triggered=False,
            limit_exceeded=False,
            overage_cost=0.0,
            period_start=datetime.now(UTC),
            period_end=datetime.now(UTC),
        )

        with (
            patch.object(svc, "_get_customer_plan", new=AsyncMock(return_value=plan)),
            patch.object(svc, "check_metric_usage", new=AsyncMock(return_value=ok_check)),
        ):
            response = await svc.check_all_limits("cust-1")

        assert response.all_limits_ok is True
        assert response.total_overage_cost == 0.0
        assert response.warnings == []


def test_overage_service_normalizes_uuid_tenant_id():
    """Regression: RequestContext.tenant_id may be a UUID object; billing
    columns are String, and asyncpg refuses varchar = uuid binds (observed
    via the Meridian certification journey: POST /v1/billing/events 500,
    'operator does not exist: character varying = uuid')."""
    import uuid

    from layer4_agents.services.overage_service import OverageService
    from layer4_agents.services.plan_version_service import PlanVersionService
    from layer4_agents.services.usage_service import UsageService

    tid = uuid.UUID("11111111-1111-4111-8111-111111111111")
    for cls in (OverageService, UsageService, PlanVersionService):
        svc = cls(db=None, tenant_id=tid)
        assert svc.tenant_id == str(tid)
        assert isinstance(svc.tenant_id, str)
