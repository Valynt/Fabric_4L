from __future__ import annotations

"""Dedicated runner for Layer 5 freshness reconciliation.

Use this module from cron, Kubernetes CronJob, or another scheduler instead of
starting per-process loops inside API workers.
"""


import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

from ..database import close_db, get_session_factory
from ..services.freshness_monitor import (
    FreshnessMonitor,
    run_freshness_check_with_leader_lock,
)

logger = logging.getLogger(__name__)


async def run_once(*, dry_run: bool = False) -> dict[str, Any]:
    """Run one guarded freshness reconciliation pass."""
    monitor = FreshnessMonitor()
    session_factory = get_session_factory()
    async with session_factory() as db:
        result = await run_freshness_check_with_leader_lock(db, monitor, dry_run=dry_run)
        if result is None:
            return {
                "checked": 0,
                "marked_stale": 0,
                "dry_run": dry_run,
                "skipped": True,
                "timestamp": datetime.now(UTC).isoformat(),
            }
        return {
            **result,
            "skipped": False,
        }


async def _async_main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    try:
        result = await run_once()
        if result.get("skipped"):
            logger.info("L5 freshness reconciliation skipped; leader lock held by another worker")
        else:
            logger.info(
                "L5 freshness reconciliation complete: checked=%d marked_stale=%d",
                result.get("checked", 0),
                result.get("marked_stale", 0),
            )
        return 0
    finally:
        await close_db()


def main() -> None:
    """CLI entrypoint for schedulers."""
    raise SystemExit(asyncio.run(_async_main()))
