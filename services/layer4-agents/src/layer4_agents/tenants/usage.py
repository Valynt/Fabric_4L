from __future__ import annotations

"""Tenant usage tracking for metrics and billing preparation."""
import asyncio
import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from value_fabric.shared.models.typed_dict import TypedDictModel


class UsageTrackingService_get_current_month_usageResult(TypedDictModel):
    agent_executions: Any
    api_calls: Any
    llm_tokens: Any
    period: str

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


@dataclass
class UsageMetrics:
    """Aggregated usage metrics for a tenant."""

    tenant_id: UUID
    period_start: datetime
    period_end: datetime

    # API usage
    api_calls_total: int
    api_calls_by_endpoint: dict[str, int]

    # Agent usage
    agent_executions: int
    agent_execution_time_ms: int

    # LLM usage
    llm_tokens_input: int
    llm_tokens_output: int
    llm_requests: int

    # Storage
    storage_bytes: int
    neo4j_nodes: int
    postgres_rows: int

    # Compute
    compute_seconds: int


class UsageTrackingService:
    """Service for tracking and querying tenant usage."""

    def __init__(self, db: AsyncSession | None = None) -> None:
        self.db = db
        self._external_db = db is not None

    async def __aenter__(self):
        if not self._external_db:
            # Import here to avoid circular imports
            from ..database import get_db_from_context as get_db_session

            self.db = await get_db_session().__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if not self._external_db and self.db:
            await self.db.__aexit__(exc_type, exc_val, exc_tb)

    async def record_api_call(
        self,
        tenant_id: UUID,
        endpoint: str,
        status_code: int,
        duration_ms: int,
    ) -> None:
        """Record an API call for usage tracking.

        Implementation: Write to audit log for aggregation.
        """
        try:
            from value_fabric.shared.audit import emit_audit_event
            from value_fabric.shared.audit.models import AuditAction, AuditOutcome

            await emit_audit_event(
                action=AuditAction.API_CALL,
                outcome=AuditOutcome.SUCCESS,
                actor_type="system",
                tenant_id=tenant_id,
                resource_type="api",
                resource_id=endpoint,
                details={
                    "endpoint": endpoint,
                    "status_code": status_code,
                    "duration_ms": duration_ms,
                },
            )
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.warning(f"Failed to record API call usage: {e}")

    async def record_llm_usage(
        self,
        tenant_id: UUID,
        model: str,
        tokens_input: int,
        tokens_output: int,
        duration_ms: int,
    ) -> None:
        """Record LLM token usage."""
        try:
            from value_fabric.shared.audit import emit_audit_event
            from value_fabric.shared.audit.models import AuditAction, AuditOutcome

            await emit_audit_event(
                action=AuditAction.LLM_USAGE,
                outcome=AuditOutcome.SUCCESS,
                actor_type="system",
                tenant_id=tenant_id,
                resource_type="llm",
                resource_id=model,
                details={
                    "model": model,
                    "tokens_input": tokens_input,
                    "tokens_output": tokens_output,
                    "duration_ms": duration_ms,
                },
            )
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.warning(f"Failed to record LLM usage: {e}")

    async def record_agent_execution(
        self,
        tenant_id: UUID,
        agent_type: str,
        duration_ms: int,
        success: bool,
    ) -> None:
        """Record agent execution."""
        try:
            from value_fabric.shared.audit import emit_audit_event
            from value_fabric.shared.audit.models import AuditAction, AuditOutcome

            await emit_audit_event(
                action=AuditAction.AGENT_EXECUTION,
                outcome=AuditOutcome.SUCCESS if success else AuditOutcome.FAILURE,
                actor_type="system",
                tenant_id=tenant_id,
                resource_type="agent",
                resource_id=agent_type,
                details={
                    "agent_type": agent_type,
                    "duration_ms": duration_ms,
                    "success": success,
                },
            )
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.warning(f"Failed to record agent execution: {e}")

    async def get_usage_summary(
        self,
        tenant_id: UUID,
        days: int = 30,
    ) -> UsageMetrics:
        """Get usage summary for a tenant."""
        if days < 1 or days > 365:
            raise ValueError("days must be between 1 and 365")

        end = datetime.now(UTC)
        start = end - timedelta(days=days)

        # Query all audit event counts in a single query
        api_calls, agent_executions, llm_requests = await self._query_audit_counts(
            tenant_id, start, end
        )

        return UsageMetrics(
            tenant_id=tenant_id,
            period_start=start,
            period_end=end,
            api_calls_total=api_calls,
            api_calls_by_endpoint={},  # Would need endpoint breakdown
            agent_executions=agent_executions,
            agent_execution_time_ms=0,  # Would aggregate from audit details
            llm_tokens_input=0,  # Aggregate from LLM usage events
            llm_tokens_output=0,
            llm_requests=llm_requests,
            storage_bytes=0,  # Would query storage directly
            neo4j_nodes=0,
            postgres_rows=0,
            compute_seconds=0,
        )

    async def _query_audit_counts(
        self,
        tenant_id: UUID,
        start: datetime,
        end: datetime,
    ) -> tuple[int, int, int]:
        """Query audit event counts for all action types in a single query."""
        try:
            from value_fabric.shared.audit.models import AuditAction, AuditEvent

            result = await self.db.execute(
                select(
                    AuditEvent.action,
                    func.count().label("count"),
                )
                .where(AuditEvent.tenant_id == tenant_id)
                .where(AuditEvent.timestamp >= start)
                .where(AuditEvent.timestamp <= end)
                .where(
                    AuditEvent.action.in_([
                        AuditAction.API_CALL,
                        AuditAction.AGENT_EXECUTION,
                        AuditAction.LLM_USAGE,
                    ])
                )
                .group_by(AuditEvent.action)
            )

            counts = {row.action: row.count for row in result.all()}
            return (
                counts.get(AuditAction.API_CALL, 0),
                counts.get(AuditAction.AGENT_EXECUTION, 0),
                counts.get(AuditAction.LLM_USAGE, 0),
            )

        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.warning(f"Failed to query usage from audit log: {e}")
            return 0, 0, 0

    async def get_current_month_usage(
        self,
        tenant_id: UUID,
    ) -> dict[str, Any]:
        """Get current month usage for limit checking."""
        today = datetime.now(UTC)
        start_of_month = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        summary = await self.get_usage_summary(
            tenant_id,
            days=(today - start_of_month).days + 1,
        )

        return UsageTrackingService_get_current_month_usageResult.model_validate({
            "api_calls": summary.api_calls_total,
            "llm_tokens": summary.llm_tokens_input + summary.llm_tokens_output,
            "agent_executions": summary.agent_executions,
            "period": "current_month",
        })


# Convenience functions for one-off usage tracking


async def record_api_call(
    tenant_id: UUID,
    endpoint: str,
    status_code: int,
    duration_ms: int,
) -> None:
    """Record an API call for usage tracking.

    Args:
        tenant_id: The tenant making the API call
        endpoint: The API endpoint path
        status_code: HTTP response status code
        duration_ms: Request duration in milliseconds
    """
    async with UsageTrackingService() as service:
        await service.record_api_call(tenant_id, endpoint, status_code, duration_ms)


async def record_llm_usage(
    tenant_id: UUID,
    model: str,
    tokens_input: int,
    tokens_output: int,
    duration_ms: int,
) -> None:
    """Record LLM token usage.

    Args:
        tenant_id: The tenant making the LLM request
        model: The LLM model name (e.g., "gpt-4")
        tokens_input: Number of input tokens
        tokens_output: Number of output tokens
        duration_ms: Request duration in milliseconds
    """
    async with UsageTrackingService() as service:
        await service.record_llm_usage(
            tenant_id, model, tokens_input, tokens_output, duration_ms
        )


async def record_agent_execution(
    tenant_id: UUID,
    agent_type: str,
    duration_ms: int,
    success: bool,
) -> None:
    """Record agent execution for usage tracking.

    Args:
        tenant_id: The tenant running the agent
        agent_type: The type of agent executed
        duration_ms: Execution duration in milliseconds
        success: Whether the execution succeeded
    """
    async with UsageTrackingService() as service:
        await service.record_agent_execution(tenant_id, agent_type, duration_ms, success)
