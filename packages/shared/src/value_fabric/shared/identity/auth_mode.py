"""Authentication mode inspection — dev auth bypass permanently removed.

All dev auth bypass functionality (F-23) has been removed from the platform.
This module is retained as a compatibility stub so that existing import
statements in main.py files do not break immediately, but all bypass
functions are no-ops that warn if legacy flags are still present.
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

_BYPASS_FLAGS = (
    "DEV_AUTH_BYPASS",
    "ALLOW_INSECURE_DEV_AUTH_BYPASS",
    "ALLOW_DEV_AUTH_BYPASS",
    "AUTH_BYPASS_ENABLED",
)

_TRUE_VALUES = frozenset({"true", "1", "yes", "on", "i_understand_risk"})
_EXPLICIT_LOCAL_ENVIRONMENTS = frozenset({"local", "development", "dev", "test", "testing", "ci"})


def _flag_value_is_truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in _TRUE_VALUES


def _bypass_flags_are_set() -> set[str]:
    active: set[str] = set()
    for flag in _BYPASS_FLAGS:
        if _flag_value_is_truthy(os.getenv(flag)):
            active.add(flag)
    return active


def _raise_if_bypass_in_nonlocal_env(service_name: str) -> None:
    env = (
        os.getenv("ENVIRONMENT")
        or os.getenv("ENV")
        or os.getenv("APP_ENV")
        or "development"
    ).strip().lower()

    active_flags = _bypass_flags_are_set()
    if env in _EXPLICIT_LOCAL_ENVIRONMENTS:
        if active_flags:
            logger.warning(
                "%s: auth bypass flag(s) %s are set in %s environment. "
                "These flags are permitted only in local/test environments.",
                service_name,
                ", ".join(sorted(active_flags)),
                env,
            )
        return

    if active_flags:
        joined = ", ".join(sorted(active_flags))
        raise RuntimeError(
            f"{service_name} startup rejected: production-like environment cannot enable auth bypass flags: {joined}."
        )


def _warn_if_legacy_flags() -> None:
    for flag in _BYPASS_FLAGS:
        val = os.getenv(flag, "").strip()
        if val and val.lower() not in ("", "false", "0", "no", "off"):
            logger.warning(
                "Legacy auth bypass flag %s is set (%r) but dev auth bypass has been "
                "permanently removed from the platform. Remove this flag from your environment.",
                flag,
                val,
            )


def is_dev_bypass_enabled() -> bool:
    """Always returns False — dev auth bypass has been permanently removed."""
    _warn_if_legacy_flags()
    return False


def is_dev_bypass_acknowledged() -> bool:
    """Always returns False — dev auth bypass has been permanently removed."""
    _warn_if_legacy_flags()
    return False


def validate_dev_bypass_configuration() -> None:
    """No-op — dev auth bypass has been permanently removed."""
    _warn_if_legacy_flags()


def assert_safe_jwt_and_bypass_configuration() -> None:
    """No-op — dev auth bypass has been permanently removed."""
    _warn_if_legacy_flags()


def log_auth_mode_report() -> None:
    """Log active auth sources. Dev bypass is always reported as removed."""
    _warn_if_legacy_flags()
    logger.info(
        "Auth mode report: dev_auth_bypass=removed active_sources=jwt_middleware,governance_middleware"
    )
