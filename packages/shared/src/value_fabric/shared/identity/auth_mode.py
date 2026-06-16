"""Authentication mode inspection — dev auth bypass detection helpers.

Dev auth bypass has been permanently removed from the platform. This module
retains canonical helper functions that detect legacy bypass environment
variables and act on them safely:

* ``_bypass_flags_are_set`` returns the set of active legacy flag names.
* ``_raise_if_bypass_in_nonlocal_env`` raises ``RuntimeError`` when any
  bypass flag is set outside an explicit local/test environment.
* Public functions remain no-ops for backward compatibility, but warn when
  legacy flags are present.

Bypass flags are permitted only in local, development, dev, test, testing,
and ci environments. In any non-local environment they are fatal at startup.
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

_FALSE_VALUES = frozenset({"false", "0"})
_EXPLICIT_LOCAL_ENVIRONMENTS = frozenset(
    {"local", "development", "dev", "test", "testing", "ci"}
)


def _flag_value_is_truthy(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized == "":
        return False
    return normalized not in _FALSE_VALUES


def _bypass_flags_are_set() -> set[str]:
    """Return the set of active legacy bypass flag names.

    A flag is considered active when its value is set to anything other than
    unset, ``false``, or ``0``. Empty strings and ``None`` are treated as unset.
    """
    active: set[str] = set()
    for flag in _BYPASS_FLAGS:
        if _flag_value_is_truthy(os.getenv(flag)):
            active.add(flag)
    return active


def _raise_if_bypass_in_nonlocal_env(
    service_name: str, environment: str | None = None
) -> None:
    if environment is not None:
        env = environment.strip().lower()
    else:
        env = (
            (
                os.getenv("ENVIRONMENT")
                or os.getenv("ENV")
                or os.getenv("APP_ENV")
                or "unknown"
            )
            .strip()
            .lower()
        )

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
        val = os.getenv(flag)
        if _flag_value_is_truthy(val):
            logger.warning(
                "Legacy auth bypass flag %s is set (%r) but dev auth bypass has been "
                "permanently removed from the platform. Remove this flag from your environment.",
                flag,
                val,
            )


def is_dev_bypass_enabled() -> bool:
    """Return False; legacy flags are detected by ``_bypass_flags_are_set``.

    Outside explicit local/test environments, ``_raise_if_bypass_in_nonlocal_env``
    treats those flags as fatal at startup.
    """
    _warn_if_legacy_flags()
    return False


def is_dev_bypass_acknowledged() -> bool:
    """Return False; legacy flags are detected by ``_bypass_flags_are_set``.

    Outside explicit local/test environments, ``_raise_if_bypass_in_nonlocal_env``
    treats those flags as fatal at startup.
    """
    _warn_if_legacy_flags()
    return False


def validate_dev_bypass_configuration() -> None:
    """No-op for backward compatibility; warns if legacy bypass flags are set.

    Legacy flags are detected by ``_bypass_flags_are_set`` and are fatal outside
    explicit local/test environments.
    """
    _warn_if_legacy_flags()


def assert_safe_jwt_and_bypass_configuration() -> None:
    """No-op for backward compatibility; warns if legacy bypass flags are set.

    Legacy flags are detected by ``_bypass_flags_are_set`` and are fatal outside
    explicit local/test environments.
    """
    _warn_if_legacy_flags()


def log_auth_mode_report() -> None:
    """Log active auth sources. Dev bypass is always reported as removed.

    Legacy flags are detected by ``_bypass_flags_are_set`` and are fatal outside
    explicit local/test environments.
    """
    _warn_if_legacy_flags()
    logger.info(
        "Auth mode report: dev_auth_bypass=removed active_sources=jwt_middleware,governance_middleware"
    )
