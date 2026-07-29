from __future__ import annotations

"""OIDC session cleanup service.

Provides background cleanup of expired OIDC sessions to prevent database bloat.
"""


import asyncio
import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import text

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

from ..database import _clear_local_tenant_context

logger = logging.getLogger(__name__)


async def cleanup_expired_oidc_sessions(db: AsyncSession) -> int:
    """Delete expired OIDC sessions from the database.

    Args:
        db: Database session for executing cleanup query.

    Returns:
        Number of deleted sessions.
    """
    try:
        result = await db.execute(
            text("""
                DELETE FROM oidc_sessions
                WHERE expires_at < NOW()
                RETURNING id
            """)
        )
        deleted_rows = result.fetchall()
        await db.commit()

        deleted_count = len(deleted_rows)
        if deleted_count > 0:
            logger.info(
                "oidc_sessions_cleaned_up",
                extra={
                    "deleted_count": deleted_count,
                    "timestamp": datetime.now(UTC).isoformat(),
                },
            )

        return deleted_count

    except asyncio.CancelledError:
        raise
    except Exception:
        logger.error(
            "oidc_cleanup_failed",
            extra={
                "error_code": "OIDC_CLEANUP_ERROR",
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )
        await db.rollback()
        raise


class OIDCCleanupTask:
    """Background task for periodic OIDC session cleanup.

    Runs cleanup every N seconds to remove expired sessions.
    """

    def __init__(
        self,
        db_session_factory: callable,
        interval_seconds: float = 300.0,  # 5 minutes default
    ) -> None:
        """Initialize cleanup task.

        Args:
            db_session_factory: Callable that returns an AsyncSession
            interval_seconds: Time between cleanup runs (default: 300s = 5min)
        """
        self._db_session_factory = db_session_factory
        self._interval_seconds = interval_seconds
        self._task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()

    async def start(self) -> None:
        """Start the background cleanup task."""
        if self._task is not None:
            logger.warning("oidc_cleanup_already_running")
            return

        self._stop_event.clear()
        self._task = asyncio.create_task(self._run_cleanup_loop())
        logger.info(
            "oidc_cleanup_started",
            extra={"interval_seconds": self._interval_seconds},
        )

    async def stop(self) -> None:
        """Stop the background cleanup task."""
        if self._task is None:
            return

        self._stop_event.set()
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass

        self._task = None
        logger.info("oidc_cleanup_stopped")

    async def _run_cleanup_loop(self) -> None:
        """Main cleanup loop that runs periodically."""
        while not self._stop_event.is_set():
            try:
                async with self._db_session_factory() as db:
                    await _clear_local_tenant_context(db)
                    deleted = await cleanup_expired_oidc_sessions(db)
                    if deleted > 0:
                        logger.info(
                            "oidc_cleanup_completed",
                            extra={"deleted_sessions": deleted},
                        )

                # Wait for next interval or until stopped
                try:
                    await asyncio.wait_for(
                        self._stop_event.wait(),
                        timeout=self._interval_seconds,
                    )
                except TimeoutError:
                    # Normal timeout - continue to next cleanup
                    pass

            except asyncio.CancelledError:
                logger.info("oidc_cleanup_cancelled")
                break
            except Exception as e:
                logger.error(
                    "oidc_cleanup_error",
                    extra={
                        "error_code": "OIDC_CLEANUP_ERROR",
                        "error_type": type(e).__name__,
                    },
                )
                # Wait before retrying to avoid tight error loops
                await asyncio.sleep(60)


async def create_oidc_cleanup_task(
    db_session_factory: callable,
    interval_seconds: float = 300.0,
) -> OIDCCleanupTask:
    """Factory function to create and start OIDC cleanup task.

    Args:
        db_session_factory: Callable that returns an AsyncSession
        interval_seconds: Time between cleanup runs (default: 300s = 5min)

    Returns:
        Started OIDCCleanupTask instance.
    """
    task = OIDCCleanupTask(
        db_session_factory=db_session_factory,
        interval_seconds=interval_seconds,
    )
    await task.start()
    return task
