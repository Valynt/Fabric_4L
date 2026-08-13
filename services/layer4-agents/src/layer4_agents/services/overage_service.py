from __future__ import annotations

"""Overage detection service for usage limits and quota enforcement.

Checks current usage against plan limits and returns warnings/errors.
Supports both soft limits (warnings) and hard limits (rejections).
"""


import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from value_fabric.shared.models.typed_dict import TypedDictModel

from ..config.plans import Plan, get_plan
from ..models.billing import BillingSubscription, BillingUsageEvent, UsageEventStatus
from .plan_version_service import PlanVersionService


class OverageService_validate_requestResult(TypedDictModel):
    allowed: bool
    current_usage: Any
    error: str
    limit: Any
    overage: Any
    upgrade_required: bool

class OverageService_get_plan_limitsResult(TypedDictModel):
    pass

logger = logging.getLogger(__name__)


@dataclass
class UsageCheckResult:
    """Result of a usage limit check."""

    metric_name: str
    current_usage: float
    limit: float
    percentage_used: float
    remaining: float
    overage: float  # Amount over limit (0 if under)
    warning_triggered: bool  # Above warning threshold
    limit_exceeded: bool  # Above hard limit
    overage_cost: float  # Estimated cost of overage
    period_start: datetime
    period_end: datetime


@dataclass
class QuotaCheckResponse:
    """Full quota check response for a customer."""

    customer_id: str
    plan_id: str
    checks: list[UsageCheckResult]
    all_limits_ok: bool  # False if any hard limit exceeded
    warnings: list[str]  # Warning messages
    total_overage_cost: float


class OverageService:
    """Service for checking usage against plan limits."""

    def __init__(self, db: AsyncSession, tenant_id: str | None = None):
        self.db = db
        # RequestContext.tenant_id may arrive as a UUID object; billing
        # columns are String, and asyncpg refuses varchar = uuid binds.
        # Normalize once at the boundary (observed via the Meridian
        # certification journey: POST /v1/billing/events 500,
        # "operator does not exist: character varying = uuid").
        self.tenant_id = str(tenant_id) if tenant_id is not None else None
        self.plan_versions = PlanVersionService(db, tenant_id=self.tenant_id)

    def _get_period_dates(self, period: str) -> tuple[datetime, datetime]:
        """Get start and end dates for a billing period.

        Args:
            period: 'monthly' or 'yearly'

        Returns:
            Tuple of (period_start, period_end)
        """
        now = datetime.now(UTC)

        if period == "monthly":
            # Start of current month
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            # End of month calculation
            if start.month == 12:
                end = start.replace(year=start.year + 1, month=1, day=1)
            else:
                end = start.replace(month=start.month + 1, day=1)
        elif period == "yearly":
            # Start of current year
            start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            end = start.replace(year=start.year + 1)
        else:
            # Default to monthly
            start = now - timedelta(days=30)
            end = now

        return start, end

    async def _get_current_usage(
        self,
        customer_id: str,
        metric_name: str,
        period_start: datetime,
        period_end: datetime,
    ) -> float:
        """Get current usage for a customer and metric in the period.

        Args:
            customer_id: Customer to check
            metric_name: Metric to aggregate
            period_start: Start of period
            period_end: End of period

        Returns:
            Total quantity used in period
        """
        if not self.tenant_id:
            return 0.0

        query = select(
            func.sum(BillingUsageEvent.quantity).label("total")
        ).where(
            BillingUsageEvent.tenant_id == self.tenant_id,
            BillingUsageEvent.customer_id == customer_id,
            BillingUsageEvent.metric_name == metric_name,
            BillingUsageEvent.timestamp >= period_start,
            BillingUsageEvent.timestamp <= period_end,
            BillingUsageEvent.status != UsageEventStatus.IGNORED,
        )

        result = await self.db.execute(query)
        row = result.one()
        return float(row.total or 0.0)

    async def _get_customer_plan(self, customer_id: str) -> Plan | None:
        """Get the plan for a customer.

        Args:
            customer_id: Customer to look up

        Returns:
            Plan or None if not found
        """
        # Get active subscription
        query = select(BillingSubscription).where(
            BillingSubscription.tenant_id == self.tenant_id,
            BillingSubscription.customer_id == customer_id,
            BillingSubscription.status.in_(["active", "trialing"]),
        ).order_by(BillingSubscription.created_at.desc())

        result = await self.db.execute(query)
        subscription = result.scalar_one_or_none()

        if not subscription:
            # Default to free plan
            return get_plan("free")

        return get_plan(subscription.plan_id)

    async def check_metric_usage(
        self,
        customer_id: str,
        metric_name: str,
        additional_usage: float = 0.0,
    ) -> UsageCheckResult:
        """Check usage for a single metric.

        Args:
            customer_id: Customer to check
            metric_name: Metric to check
            additional_usage: Additional usage to simulate (for pre-check)

        Returns:
            Usage check result
        """
        plan = await self._get_customer_plan(customer_id)
        if not plan:
            # No plan = no limits
            return UsageCheckResult(
                metric_name=metric_name,
                current_usage=0.0,
                limit=float("inf"),
                percentage_used=0.0,
                remaining=float("inf"),
                overage=0.0,
                warning_triggered=False,
                limit_exceeded=False,
                overage_cost=0.0,
                period_start=datetime.now(UTC),
                period_end=datetime.now(UTC),
            )

        # Prefer persisted, effective plan version limits for billing reproducibility
        subscription_query = select(BillingSubscription).where(
            BillingSubscription.tenant_id == self.tenant_id,
            BillingSubscription.customer_id == customer_id,
            BillingSubscription.status.in_(["active", "trialing"]),
        ).order_by(BillingSubscription.created_at.desc())
        subscription = (await self.db.execute(subscription_query)).scalar_one_or_none()
        effective_plan_version = await self.plan_versions.get_subscription_plan_version(subscription, datetime.now(UTC))
        if effective_plan_version:
            serialized = (effective_plan_version.usage_limits or {}).get(metric_name)
            if serialized:
                class _Limit:
                    period: str
                    included_amount: float
                    warning_threshold: float
                    hard_limit: bool
                    overage_rate: float
                limit = _Limit()
                limit.period = serialized.get("period", "monthly")
                limit.included_amount = float(serialized.get("included_amount", 0.0))
                limit.warning_threshold = float(serialized.get("warning_threshold", 80.0))
                limit.hard_limit = bool(serialized.get("hard_limit", False))
                limit.overage_rate = float(serialized.get("overage_rate", 0.0))
            else:
                limit = None
        else:
            limit = plan.get_usage_limit(metric_name)  # type: ignore[assignment]
        if not limit:
            # No limit configured for this metric
            return UsageCheckResult(
                metric_name=metric_name,
                current_usage=0.0,
                limit=float("inf"),
                percentage_used=0.0,
                remaining=float("inf"),
                overage=0.0,
                warning_triggered=False,
                limit_exceeded=False,
                overage_cost=0.0,
                period_start=datetime.now(UTC),
                period_end=datetime.now(UTC),
            )

        # Get period dates
        period_start, period_end = self._get_period_dates(limit.period)

        # Get current usage
        current_usage = await self._get_current_usage(
            customer_id, metric_name, period_start, period_end
        )

        # Add simulated additional usage
        total_usage = current_usage + additional_usage

        # Calculate metrics
        limit_amount = limit.included_amount
        if limit_amount == float("inf"):
            percentage_used = 0.0
            remaining = float("inf")
            overage = 0.0
            warning_triggered = False
            limit_exceeded = False
            overage_cost = 0.0
        else:
            percentage_used = (total_usage / limit_amount) * 100 if limit_amount > 0 else 0.0
            remaining = max(0.0, limit_amount - total_usage)
            overage = max(0.0, total_usage - limit_amount)
            warning_threshold = limit.warning_threshold
            warning_triggered = percentage_used >= warning_threshold
            limit_exceeded = limit.hard_limit and overage > 0
            overage_cost = overage * limit.overage_rate

        return UsageCheckResult(
            metric_name=metric_name,
            current_usage=current_usage,
            limit=limit_amount,
            percentage_used=percentage_used,
            remaining=remaining,
            overage=overage,
            warning_triggered=warning_triggered,
            limit_exceeded=limit_exceeded,
            overage_cost=overage_cost,
            period_start=period_start,
            period_end=period_end,
        )

    async def check_all_limits(
        self,
        customer_id: str,
    ) -> QuotaCheckResponse:
        """Check all usage limits for a customer.

        Args:
            customer_id: Customer to check

        Returns:
            Full quota check response
        """
        plan = await self._get_customer_plan(customer_id)
        plan_id = plan.id if plan else "free"

        if not plan or not plan.usage_limits:
            # No limits configured
            return QuotaCheckResponse(
                customer_id=customer_id,
                plan_id=plan_id,
                checks=[],
                all_limits_ok=True,
                warnings=[],
                total_overage_cost=0.0,
            )

        checks = []
        warnings = []
        all_limits_ok = True
        total_overage_cost = 0.0

        for metric_name in plan.usage_limits:
            check = await self.check_metric_usage(customer_id, metric_name)
            checks.append(check)

            if check.limit_exceeded:
                all_limits_ok = False
                warnings.append(
                    f"Hard limit exceeded for {metric_name}: "
                    f"{check.current_usage:.0f} / {check.limit:.0f} "
                    f"({check.percentage_used:.1f}%)"
                )
            elif check.warning_triggered:
                warnings.append(
                    f"Warning: {metric_name} at {check.percentage_used:.1f}% of limit "
                    f"({check.remaining:.0f} remaining)"
                )

            total_overage_cost += check.overage_cost

        return QuotaCheckResponse(
            customer_id=customer_id,
            plan_id=plan_id,
            checks=checks,
            all_limits_ok=all_limits_ok,
            warnings=warnings,
            total_overage_cost=total_overage_cost,
        )

    async def validate_request(
        self,
        customer_id: str,
        metric_name: str,
        requested_quantity: float = 1.0,
    ) -> dict[str, Any]:
        """Validate if a request should be allowed based on usage limits.

        Args:
            customer_id: Customer making request
            metric_name: Metric being consumed
            requested_quantity: Quantity to be consumed

        Returns:
            Validation result with allow/deny and warnings
        """
        check = await self.check_metric_usage(
            customer_id, metric_name, additional_usage=requested_quantity
        )

        if check.limit_exceeded:
            return OverageService_validate_requestResult.model_validate({  # type: ignore[no-any-return]
                "allowed": False,
                "error": f"Usage limit exceeded for {metric_name}",
                "limit": check.limit,
                "current_usage": check.current_usage,
                "overage": check.overage,
                "upgrade_required": True,
            })


        result = {
            "allowed": True,
            "metric": metric_name,
            "requested": requested_quantity,
            "limit": check.limit if check.limit != float("inf") else None,
            "current_usage": check.current_usage,
            "remaining": check.remaining,
            "percentage_used": check.percentage_used,
        }

        if check.warning_triggered:
            result["warning"] = (
                f"Approaching limit: {check.percentage_used:.1f}% used, "
                f"{check.remaining:.0f} remaining"
            )

        return result

    def get_plan_limits(self, plan_id: str) -> dict[str, Any]:
        """Get the configured limits for a plan.

        Args:
            plan_id: Plan identifier

        Returns:
            Dict of metric_name -> limit details
        """
        plan = get_plan(plan_id)
        if not plan or not plan.usage_limits:
            return OverageService_get_plan_limitsResult.model_validate({})  # type: ignore[no-any-return]

        return OverageService_get_plan_limitsResult.model_validate({  # type: ignore[no-any-return]
            metric_name: {
                "included_amount": limit.included_amount,
                "period": limit.period,
                "overage_rate": limit.overage_rate,
                "hard_limit": limit.hard_limit,
                "warning_threshold": limit.warning_threshold,
            }
            for metric_name, limit in plan.usage_limits.items()
        })

