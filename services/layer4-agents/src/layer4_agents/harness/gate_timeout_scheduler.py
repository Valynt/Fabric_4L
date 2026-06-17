from __future__ import annotations

"""Gate timeout scheduler — automatically expires pending human gates.

Runs as a background asyncio task within the Layer 4 FastAPI lifespan.
Queries for gates in PENDING status whose created_at exceeds the timeout
and transitions them to EXPIRED.
"""


import asyncio
import logging
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta

logger = logging.getLogger(__name__)

SAFE_FALLBACK_GATE_TIMEOUT_SECONDS = 600
MIN_GATE_TIMEOUT_SECONDS = 60
MAX_GATE_TIMEOUT_SECONDS = 3600


class GateTimeoutScheduler:
    """Background scheduler that expires overdue pending gates.

    Uses the SQL-backed HumanGateRepository so state survives restarts.
    """

    def __init__(self, session_factory, timeout_seconds: int = SAFE_FALLBACK_GATE_TIMEOUT_SECONDS):
        self._session_factory = session_factory
        self._default_timeout_seconds = self._validate_timeout(timeout_seconds)
        self._task: asyncio.Task | None = None
        self._shutdown = False

    async def start(self) -> None:
        """Start the background expiration loop."""
        if self._task is None:
            self._task = asyncio.create_task(self._run_loop())
            logger.info(
                "Gate timeout scheduler started (default_timeout=%ss)", self._default_timeout_seconds
            )

    async def stop(self) -> None:
        """Stop the scheduler gracefully."""
        self._shutdown = True
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("Gate timeout scheduler stopped")

    async def _run_loop(self) -> None:
        """Main loop: check for expired gates every 10 seconds."""
        while not self._shutdown:
            try:
                await self._expire_overdue_gates()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.error("Gate expiration error: %s", exc)
            await asyncio.sleep(10)

    async def _expire_overdue_gates(self) -> None:
        """Find and expire all pending gates past their deadline."""
        from sqlalchemy import select

        now = datetime.now(UTC)

        async with self._session_factory() as session:
            from harness.db_models import HumanGateRow

            stmt = select(HumanGateRow).where(HumanGateRow.status == "pending")
            result = await session.execute(stmt)
            overdue_gates = result.scalars().all()

            expired_count = 0
            for row in overdue_gates:
                timeout_seconds, source = await self._resolve_timeout_for_tenant(
                    session, tenant_id=row.tenant_id
                )
                deadline = now - timedelta(seconds=timeout_seconds)
                if row.created_at >= deadline:
                    continue

                row.status = "expired"
                row.decision_by = "system"
                row.decision_reason = f"Gate expired after {timeout_seconds}s timeout"
                row.decided_at = now
                expired_count += 1

                logger.info(
                    "Gate timeout decision",
                    extra={
                        "tenant_id": row.tenant_id,
                        "effective_timeout_s": timeout_seconds,
                        "source": source,
                    },
                )

            if expired_count:
                await session.commit()
                logger.info("Expired %d overdue gate(s)", expired_count)

    @staticmethod
    def _validate_timeout(timeout_seconds: int) -> int:
        if MIN_GATE_TIMEOUT_SECONDS <= timeout_seconds <= MAX_GATE_TIMEOUT_SECONDS:
            return timeout_seconds
        raise ValueError(
            f"Timeout must be between {MIN_GATE_TIMEOUT_SECONDS} and {MAX_GATE_TIMEOUT_SECONDS} seconds"
        )

    async def _resolve_timeout_for_tenant(self, session, tenant_id: str) -> tuple[int, str]:
        tenant_timeout = await self._get_tenant_timeout_override(session, tenant_id)
        if tenant_timeout is not None:
            if MIN_GATE_TIMEOUT_SECONDS <= tenant_timeout <= MAX_GATE_TIMEOUT_SECONDS:
                return tenant_timeout, "tenant_override"
            logger.warning(
                "Rejected tenant gate timeout override outside bounds",
                extra={
                    "tenant_id": tenant_id,
                    "effective_timeout_s": self._default_timeout_seconds,
                    "source": "default",
                    "invalid_timeout_s": tenant_timeout,
                    "min_timeout_s": MIN_GATE_TIMEOUT_SECONDS,
                    "max_timeout_s": MAX_GATE_TIMEOUT_SECONDS,
                },
            )
        if MIN_GATE_TIMEOUT_SECONDS <= self._default_timeout_seconds <= MAX_GATE_TIMEOUT_SECONDS:
            return self._default_timeout_seconds, "default"
        return SAFE_FALLBACK_GATE_TIMEOUT_SECONDS, "fallback"

    async def _get_tenant_timeout_override(self, session, tenant_id: str) -> int | None:
        from sqlalchemy import select

        from layer4_agents.tenants.models.tenant import Tenant

        result = await session.execute(select(Tenant.settings).where(Tenant.id == tenant_id))
        settings = result.scalar_one_or_none()
        if not isinstance(settings, Mapping):
            return None

        gate_settings = settings.get("agent_gate")
        if not isinstance(gate_settings, Mapping):
            return None

        timeout = gate_settings.get("timeout_seconds")
        return timeout if isinstance(timeout, int) else None


def create_gate_timeout_scheduler(session_factory) -> GateTimeoutScheduler:
    """Factory for the gate timeout scheduler."""
    from ..config.settings import get_settings

    return GateTimeoutScheduler(
        session_factory,
        timeout_seconds=get_settings().agent_gate_timeout_seconds,
    )


DEFAULT_GATE_TIMEOUT_SECONDS = SAFE_FALLBACK_GATE_TIMEOUT_SECONDS
