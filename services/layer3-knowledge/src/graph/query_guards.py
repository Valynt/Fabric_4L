"""Centralized guardrails for graph query depth and timeout handling."""

from __future__ import annotations

DEFAULT_MAX_QUERY_DEPTH = 10
DEFAULT_QUERY_TIMEOUT_SECONDS = 30.0
MIN_QUERY_DEPTH = 1
MIN_QUERY_TIMEOUT_SECONDS = 0.1
MAX_QUERY_TIMEOUT_SECONDS = 120.0


def sanitize_query_depth(
    requested_depth: int | None,
    *,
    default_depth: int = 2,
    clamp: bool = True,
) -> int:
    """Return a safe traversal depth for graph query paths.

    Missing/invalid values fail closed to ``default_depth``. If ``clamp`` is True,
    out-of-policy values are clamped into the safe range.
    """
    safe_default = max(MIN_QUERY_DEPTH, min(default_depth, DEFAULT_MAX_QUERY_DEPTH))
    if not isinstance(requested_depth, int):
        return safe_default
    if clamp:
        return max(MIN_QUERY_DEPTH, min(requested_depth, DEFAULT_MAX_QUERY_DEPTH))
    if requested_depth < MIN_QUERY_DEPTH or requested_depth > DEFAULT_MAX_QUERY_DEPTH:
        raise ValueError(
            f"Traversal depth must be between {MIN_QUERY_DEPTH} and {DEFAULT_MAX_QUERY_DEPTH}"
        )
    return requested_depth


def sanitize_query_timeout_seconds(
    requested_timeout_seconds: float | int | None,
    *,
    default_timeout_seconds: float = DEFAULT_QUERY_TIMEOUT_SECONDS,
) -> float:
    """Return safe timeout for graph query execution."""
    safe_default = max(
        MIN_QUERY_TIMEOUT_SECONDS,
        min(float(default_timeout_seconds), MAX_QUERY_TIMEOUT_SECONDS),
    )
    if requested_timeout_seconds is None:
        return safe_default

    try:
        timeout = float(requested_timeout_seconds)
    except (TypeError, ValueError):
        return safe_default

    if timeout <= 0:
        return safe_default
    return max(MIN_QUERY_TIMEOUT_SECONDS, min(timeout, MAX_QUERY_TIMEOUT_SECONDS))
