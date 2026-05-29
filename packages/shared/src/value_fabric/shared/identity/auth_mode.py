"""Authentication mode inspection — dev auth bypass permanently removed.

All dev auth bypass functionality (F-23) has been removed from the platform.
This module is retained as a compatibility stub so that existing import
statements in main.py files do not break immediately, but all bypass
functions are no-ops that warn if legacy flags are still present.
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

_BYPASS_FLAGS = (
    "DEV_AUTH_BYPASS",
    "ALLOW_INSECURE_DEV_AUTH_BYPASS",
    "ALLOW_DEV_AUTH_BYPASS",
    "AUTH_BYPASS_ENABLED",
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
