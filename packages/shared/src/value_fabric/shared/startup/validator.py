"""Startup validation helpers shared across services."""

from __future__ import annotations

import os
from typing import Any

from value_fabric.shared.security import is_production_like_environment

_TRUE_VALUES = {"true", "1", "yes", "on", "i_understand_risk"}
_BYPASS_ENV_FLAGS = (
    "ALLOW_INSECURE_DEV_AUTH_BYPASS",
    "DEV_AUTH_BYPASS",
    "AUTH_BYPASS_ENABLED",
    "ALLOW_DEV_AUTH_BYPASS",
)
_BYPASS_SETTINGS_FIELDS = (
    "allow_insecure_dev_auth_bypass",
    "dev_auth_bypass",
    "auth_bypass_enabled",
    "allow_dev_auth_bypass",
)


def _flag_is_truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in _TRUE_VALUES


def reject_insecure_bypass_in_production(*, service_name: str, settings: Any | None = None) -> None:
    """Fail closed when production-like runtimes enable auth bypass toggles."""
    if not is_production_like_environment():
        return

    active_flags: list[str] = []
    for env_name in _BYPASS_ENV_FLAGS:
        if _flag_is_truthy(os.getenv(env_name, "")):
            active_flags.append(env_name)

    if settings is not None:
        for field_name in _BYPASS_SETTINGS_FIELDS:
            if hasattr(settings, field_name) and _flag_is_truthy(getattr(settings, field_name)):
                canonical = field_name.upper()
                if canonical not in active_flags:
                    active_flags.append(canonical)

    if active_flags:
        joined = ", ".join(sorted(set(active_flags)))
        raise RuntimeError(
            f"{service_name} startup rejected: production-like environment cannot enable auth bypass flags: {joined}."
        )
