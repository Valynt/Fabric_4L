from __future__ import annotations

"""Usage tracking service for tenant resource consumption.

Collects and aggregates usage metrics per tenant for:
- API call counts (monthly)
- LLM token consumption (input/output)
- Agent execution counts and duration
- Storage consumption

Metrics are derived from audit events and supplemented by direct
instrumentation. Results feed into the admin dashboard and tier
enforcement checks.

Design Principles:
- Read-only aggregation over existing audit_events table
- No separate usage tables (Phase 3) — avoids dual-write complexity
- Caching layer for dashboard performance
- Time-windowed queries (default 30 days)
"""


import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from value_fabric.shared.models.typed_dict import TypedDictModel


class UsageTrackingService__get_llm_usageResult(TypedDictModel):
    requests: int
    tokens_input: int
    tokens_output: int

class UsageTrackingService__count_events_by_fieldResult(TypedDictModel):
    pass

logger = logging.getLogger(__name__)


@dataclass
class UsageSummary:
    """Aggregated usage metrics for a tenant over a time period."""

    tenant_id: UUID
    period_start: datetime
    period_end: datetime

    # API calls
    api_calls_total: int = 0
    api_calls_by_endpoint: dict[str, int] = field(default_factory=dict)

    # Agent executions
    agent_executions: int = 0
    agent_execution_time_ms: int = 0
    agent_executions_by_type: dict[str, int] = field(default_factory=dict)

    # LLM usage
    llm_tokens_input: int = 0
    llm_tokens_output: int = 0
    llm_requests: int = 0
    llm_cost_estimate_usd: float = 0.0

    # Storage
    storage_used_mb: int = 0

    # Users
    active_users: int = 0
    total_users: int = 0


@dataclass
class DailyUsage:
    """Usage metrics for a single day."""

    date: str  # YYYY-MM-DD
    api_calls: int = 0
    agent_executions: int = 0
    llm_tokens: int = 0


class UsageTrackingService:
    """Service for querying and aggregating tenant usage metrics.

    All queries are read-only aggregations over the audit_events table.
    The audit_events table is expected to have:
        - id, timestamp, action, outcome, tenant_id, actor_id,
          resource_type, resource_id, details (JSONB)

    Usage:
        service = UsageTrackingService(db)
        summary = await service.get_usage_summary(tenant_id, days=30)
    """

    # Estimated cost per 1K tokens (configurable via env in future)
    DEFAULT_LLM_COST_PER_1K_INPUT = 0.0005
    DEFAULT_LLM_COST_PER_1K_OUTPUT = 0.0015

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_usage_summary(
        self,
        tenant_id: UUID,
        days: int = 30,
    ) -> UsageSummary:
        """Get aggregated usage summary for a tenant.

        Queries audit_events for the given time window and aggregates
        by action type.
        """
        now = datetime.now(UTC)
        period_start = now - timedelta(days=days)

        summary = UsageSummary(
            tenant_id=tenant_id,
            period_start=period_start,
            period_end=now,
        )

        # Run all aggregation queries
        summary.api_calls_total = await self._count_events(
            tenant_id, "api_call", period_start,
        )
        summary.api_calls_by_endpoint = await self._count_events_by_field(
            tenant_id, "api_call", "resource_type", period_start,
        )

        summary.agent_executions = await self._count_events(
            tenant_id, "agent_execution", period_start,
        )
        agent_details = await self._sum_detail_field(
            tenant_id, "agent_execution", "execution_time_ms", period_start,
        )
        summary.agent_execution_time_ms = agent_details

        llm_details = await self._get_llm_usage(tenant_id, period_start)
        summary.llm_tokens_input = llm_details["tokens_input"]
        summary.llm_tokens_output = llm_details["tokens_output"]
        summary.llm_requests = llm_details["requests"]
        summary.llm_cost_estimate_usd = (
            (summary.llm_tokens_input / 1000) * self.DEFAULT_LLM_COST_PER_1K_INPUT
            + (summary.llm_tokens_output / 1000) * self.DEFAULT_LLM_COST_PER_1K_OUTPUT
        )

        summary.active_users = await self._count_active_users(
            tenant_id, period_start,
        )

        return summary

    async def get_daily_usage(
        self,
        tenant_id: UUID,
        days: int = 30,
    ) -> list[DailyUsage]:
        """Get daily usage breakdown for charting.

        Returns one DailyUsage per day in the time window.
        """
        now = datetime.now(UTC)
        period_start = now - timedelta(days=days)

        query = text("""
            SELECT
                DATE(timestamp) as day,
                COUNT(*) FILTER (WHERE action = 'api_call') as api_calls,
                COUNT(*) FILTER (WHERE action = 'agent_execution') as agent_execs,
                COALESCE(
                    SUM(
                        CASE WHEN action = 'llm_usage'
                        THEN COALESCE((details->>'tokens_input')::int, 0)
                           + COALESCE((details->>'tokens_output')::int, 0)
                        ELSE 0 END
                    ), 0
                ) as llm_tokens
            FROM audit_events
            WHERE tenant_id = :tenant_id
              AND timestamp >= :period_start
            GROUP BY DATE(timestamp)
            ORDER BY day
        """)

        try:
            result = await self.db.execute(
                query,
                {"tenant_id": str(tenant_id), "period_start": period_start},
            )
            rows = result.fetchall()

            return [
                DailyUsage(
                    date=str(row[0]),
                    api_calls=row[1],
                    agent_executions=row[2],
                    llm_tokens=row[3],
                )
                for row in rows
            ]
        except Exception:
            logger.warning(
                "Failed to query daily usage — audit_events table may not exist",
                exc_info=True,
            )
            return []

    async def get_current_month_api_calls(
        self,
        tenant_id: UUID,
    ) -> int:
        """Get API call count for the current calendar month.

        Used by tier enforcement to check monthly limits.
        """
        now = datetime.now(UTC)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return await self._count_events(tenant_id, "api_call", month_start)

    async def get_current_month_llm_tokens(
        self,
        tenant_id: UUID,
    ) -> int:
        """Get total LLM tokens (input + output) for the current month.

        Used by tier enforcement to check monthly limits.
        """
        now = datetime.now(UTC)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        details = await self._get_llm_usage(tenant_id, month_start)
        return details["tokens_input"] + details["tokens_output"]

    async def get_top_endpoints(
        self,
        tenant_id: UUID,
        days: int = 30,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Get the most-called API endpoints for a tenant.

        Useful for dashboard analytics.
        """
        now = datetime.now(UTC)
        period_start = now - timedelta(days=days)

        query = text("""
            SELECT
                resource_type as endpoint,
                COUNT(*) as call_count,
                COUNT(DISTINCT actor_id) as unique_users
            FROM audit_events
            WHERE tenant_id = :tenant_id
              AND action = 'api_call'
              AND timestamp >= :period_start
            GROUP BY resource_type
            ORDER BY call_count DESC
            LIMIT :limit
        """)

        try:
            result = await self.db.execute(
                query,
                {
                    "tenant_id": str(tenant_id),
                    "period_start": period_start,
                    "limit": limit,
                },
            )
            rows = result.fetchall()

            return [
                {
                    "endpoint": row[0],
                    "call_count": row[1],
                    "unique_users": row[2],
                }
                for row in rows
            ]
        except Exception:
            logger.warning("Failed to query top endpoints", exc_info=True)
            return []

    # ── Internal query helpers ──────────────────────────────────────

    async def _count_events(
        self,
        tenant_id: UUID,
        action: str,
        since: datetime,
    ) -> int:
        """Count audit events of a given action type."""
        query = text("""
            SELECT COUNT(*)
            FROM audit_events
            WHERE tenant_id = :tenant_id
              AND action = :action
              AND timestamp >= :since
        """)
        try:
            result = await self.db.execute(
                query,
                {"tenant_id": str(tenant_id), "action": action, "since": since},
            )
            return result.scalar_one_or_none() or 0
        except Exception:
            logger.warning("Failed to count events for %s", action, exc_info=True)
            return 0

    # Allowlist of columns safe to use in GROUP BY queries
    _ALLOWED_GROUP_FIELDS = frozenset({"resource_type", "action", "outcome", "actor_id", "resource_id"})

    async def _count_events_by_field(
        self,
        tenant_id: UUID,
        action: str,
        group_field: str,
        since: datetime,
    ) -> dict[str, int]:
        """Count events grouped by a column value.

        Args:
            group_field: Must be one of _ALLOWED_GROUP_FIELDS to prevent SQL injection.
        """
        if group_field not in self._ALLOWED_GROUP_FIELDS:
            raise ValueError(
                f"Invalid group_field '{group_field}'. "
                f"Allowed: {sorted(self._ALLOWED_GROUP_FIELDS)}"
            )
        query = text(f"""
            SELECT {group_field}, COUNT(*)
            FROM audit_events
            WHERE tenant_id = :tenant_id
              AND action = :action
              AND timestamp >= :since
            GROUP BY {group_field}
            ORDER BY COUNT(*) DESC
        """)
        try:
            result = await self.db.execute(
                query,
                {"tenant_id": str(tenant_id), "action": action, "since": since},
            )
            return UsageTrackingService__count_events_by_fieldResult.model_validate({row[0]: row[1] for row in result.fetchall()})
        except Exception:
            logger.warning("Failed to count events by %s", group_field, exc_info=True)
            return UsageTrackingService__count_events_by_fieldResult.model_validate({})

    async def _sum_detail_field(
        self,
        tenant_id: UUID,
        action: str,
        detail_key: str,
        since: datetime,
    ) -> int:
        """Sum a numeric field from the JSONB details column."""
        query = text("""
            SELECT COALESCE(
                SUM((details->>:detail_key)::int), 0
            )
            FROM audit_events
            WHERE tenant_id = :tenant_id
              AND action = :action
              AND timestamp >= :since
              AND details->>:detail_key IS NOT NULL
        """)
        try:
            result = await self.db.execute(
                query,
                {
                    "tenant_id": str(tenant_id),
                    "action": action,
                    "detail_key": detail_key,
                    "since": since,
                },
            )
            return result.scalar_one_or_none() or 0
        except Exception:
            logger.warning(
                "Failed to sum detail field %s", detail_key, exc_info=True,
            )
            return 0

    async def _get_llm_usage(
        self,
        tenant_id: UUID,
        since: datetime,
    ) -> dict[str, int]:
        """Get aggregated LLM usage from audit events."""
        query = text("""
            SELECT
                COALESCE(SUM((details->>'tokens_input')::int), 0) as tokens_in,
                COALESCE(SUM((details->>'tokens_output')::int), 0) as tokens_out,
                COUNT(*) as requests
            FROM audit_events
            WHERE tenant_id = :tenant_id
              AND action = 'llm_usage'
              AND timestamp >= :since
        """)
        try:
            result = await self.db.execute(
                query,
                {"tenant_id": str(tenant_id), "since": since},
            )
            row = result.fetchone()
            if row:
                return UsageTrackingService__get_llm_usageResult.model_validate({
                    "tokens_input": row[0],
                    "tokens_output": row[1],
                    "requests": row[2],
                })


        except Exception:
            logger.warning("Failed to query LLM usage", exc_info=True)

        return UsageTrackingService__get_llm_usageResult.model_validate({"tokens_input": 0, "tokens_output": 0, "requests": 0})

    async def _count_active_users(
        self,
        tenant_id: UUID,
        since: datetime,
    ) -> int:
        """Count distinct users who performed any action."""
        query = text("""
            SELECT COUNT(DISTINCT actor_id)
            FROM audit_events
            WHERE tenant_id = :tenant_id
              AND actor_id IS NOT NULL
              AND timestamp >= :since
        """)
        try:
            result = await self.db.execute(
                query,
                {"tenant_id": str(tenant_id), "since": since},
            )
            return result.scalar_one_or_none() or 0
        except Exception:
            logger.warning("Failed to count active users", exc_info=True)
            return 0
