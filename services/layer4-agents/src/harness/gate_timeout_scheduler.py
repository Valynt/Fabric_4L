"""Gate timeout scheduler — automatically expires pending human gates.

Runs as a background asyncio task within the Layer 4 FastAPI lifespan.
Queries for gates in PENDING status whose created_at exceeds the timeout
and transitions them to EXPIRED.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)

# Default gate timeout: 60 seconds (P0 requirement)
DEFAULT_GATE_TIMEOUT_SECONDS = 60


class GateTimeoutScheduler:
    """Background scheduler that expires overdue pending gates.

    Uses the SQL-backed HumanGateRepository so state survives restarts.
    """

    def __init__(self, session_factory, timeout_seconds: int = DEFAULT_GATE_TIMEOUT_SECONDS):
        self._session_factory = session_factory
        self._timeout_seconds = timeout_seconds
        self._task: asyncio.Task | None = None
        self._shutdown = False

    async def start(self) -> None:
        """Start the background expiration loop."""
        if self._task is None:
            self._task = asyncio.create_task(self._run_loop())
            logger.info(
                "Gate timeout scheduler started (timeout=%ss)", self._timeout_seconds
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
            except Exception as exc:
                logger.error("Gate expiration error: %s", exc)
            await asyncio.sleep(10)

    async def _expire_overdue_gates(self) -> None:
        """Find and expire all pending gates past their deadline."""
        from sqlalchemy import select
        from sqlalchemy.ext.asyncio import AsyncSession

        deadline = datetime.now(UTC) - timedelta(seconds=self._timeout_seconds)

        async with self._session_factory() as session:
            from harness.db_models import HumanGateRow
            from harness.models import GateStatus

            stmt = (
                select(HumanGateRow)
                .where(
                    HumanGateRow.status == "pending",
                    HumanGateRow.created_at < deadline,
                )
            )
            result = await session.execute(stmt)
            overdue_gates = result.scalars().all()

            expired_count = 0
            for row in overdue_gates:
                row.status = "expired"
                row.decision_by = "system"
                row.decision_reason = f"Gate expired after {self._timeout_seconds}s timeout"
                row.decided_at = datetime.now(UTC)
                expired_count += 1

            if expired_count:
                await session.commit()
                logger.info("Expired %d overdue gate(s)", expired_count)


def create_gate_timeout_scheduler(session_factory) -> GateTimeoutScheduler:
    """Factory for the gate timeout scheduler."""
    return GateTimeoutScheduler(session_factory)
