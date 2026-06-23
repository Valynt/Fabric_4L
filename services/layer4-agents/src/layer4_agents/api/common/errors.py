from __future__ import annotations

"""Shared error helpers for API routes."""


import logging
from typing import NoReturn

from fastapi import HTTPException
from value_fabric.shared.error_handling import build_error_detail


def normalize_exception(
    exc: Exception,
    *,
    status_code: int,
    message: str,
    error_code: str,
    request_id: str | None = None,
) -> HTTPException:
    """Preserve existing HTTP errors and normalize all other exceptions."""
    if isinstance(exc, HTTPException):
        return exc
    return HTTPException(
        status_code=status_code,
        detail=build_error_detail(
            message=message,
            error_code=error_code,
            request_id=request_id,
        ),
    )


def raise_normalized(exc: Exception, **kwargs) -> NoReturn:
    """Raise a normalized HTTPException while preserving existing HTTP payloads."""
    raise normalize_exception(exc, **kwargs)


def raise_normalized_with_log(
    exc: Exception,
    *,
    status_code: int,
    message: str,
    error_code: str,
    logger: logging.Logger,
    log_message: str,
    request_id: str | None = None,
    **log_extra,
) -> NoReturn:
    """Log unexpected exceptions and raise a normalized HTTPException."""
    if not isinstance(exc, HTTPException):
        extra = {
            "error_code": error_code,
            "request_id": request_id,
            "correlation_id": request_id,
            "exception_type": type(exc).__name__,
            **log_extra,
        }
        try:
            logger.exception(log_message, extra=extra)
        except TypeError:
            logger.exception(log_message)
    raise_normalized(
        exc,
        status_code=status_code,
        message=message,
        error_code=error_code,
        request_id=request_id,
    )
