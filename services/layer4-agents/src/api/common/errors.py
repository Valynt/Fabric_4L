"""Shared error helpers for API routes."""

from __future__ import annotations

import logging

from fastapi import HTTPException
from value_fabric.shared.error_handling.models import build_error_detail


def normalize_exception(exc: Exception, *, status_code: int, detail: str) -> HTTPException:
    """Preserve existing HTTP errors and normalize all other exceptions."""
    if isinstance(exc, HTTPException):
        return exc
    return HTTPException(
        status_code=status_code,
        detail=build_error_detail(
            message=detail,
            error_code="INTERNAL_ERROR",
            request_id=None,
            correlation_id=None,
        ),
    )


def raise_normalized(exc: Exception, *, status_code: int, detail: str) -> None:
    """Raise a normalized HTTPException while preserving existing HTTP payloads."""
    raise normalize_exception(exc, status_code=status_code, detail=detail)
def raise_normalized_with_log(
    exc: Exception,
    *,
    status_code: int,
    detail: str,
    logger: logging.Logger,
    log_message: str,
) -> None:
    """Log unexpected exceptions and raise a normalized HTTPException."""
    if not isinstance(exc, HTTPException):
        logger.exception(
            log_message,
            extra={
                "exception_type": type(exc).__name__,
                "exception_message": str(exc),
            },
        )
    raise_normalized(exc, status_code=status_code, detail=detail)
