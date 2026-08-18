"""Fail-closed task fallback for when Celery infrastructure is unavailable.

Extracted from main.py and target_handlers.py to eliminate duplication
and ensure consistent failure behavior across all API modules.
"""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import HTTPException

logger = structlog.get_logger()


def _build_task_unavailable_detail() -> dict[str, str]:
    """Standardized 503 payload when background tasks are unavailable."""
    return {
        "code": "SERVICE_UNAVAILABLE",
        "message": (
            "Background processing is temporarily unavailable. "
            "Please retry shortly or contact support if the issue persists."
        ),
    }


class UnavailableTask:
    """Fail closed when task infrastructure is unavailable.

    Provides both ``delay()`` (Celery-style) and ``apply_async()``
    signatures so downstream code can call either method uniformly.
    """

    def __init__(self, task_name: str, import_error: ImportError) -> None:
        self.task_name = task_name
        self.import_error = import_error

    def _log_and_raise(self, job_id: str | None = None) -> None:
        logger.error(
            "background_task_unavailable",
            task_name=self.task_name,
            job_id=job_id,
            correlation_id=job_id,
            error_type=type(self.import_error).__name__,
            error=str(self.import_error),
            exc_info=self.import_error,
        )
        raise HTTPException(status_code=503, detail=_build_task_unavailable_detail())

    def delay(self, *args: Any, **kwargs: Any) -> None:
        """Celery ``.delay()`` signature — logs and raises 503."""
        job_id = str(args[0]) if args else None
        self._log_and_raise(job_id)

    def apply_async(self, *args: Any, **kwargs: Any) -> None:
        """Celery ``.apply_async()`` signature — logs and raises 503."""
        self._log_and_raise()