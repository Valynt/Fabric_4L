"""Startup validation helpers shared across services."""

from __future__ import annotations

from typing import Any

from value_fabric.shared.identity.auth_mode import _raise_if_bypass_in_nonlocal_env
from value_fabric.shared.security import detect_environment

_TRUE_VALUES = {"true", "1", "yes", "on", "i_understand_risk"}
_EXPLICIT_LOCAL_TEST_ENVIRONMENTS = frozenset(
    {"local", "development", "dev", "test", "testing", "ci"}
)


def _is_explicit_local_or_test_environment() -> bool:
    env = detect_environment().strip().lower()
    return env in _EXPLICIT_LOCAL_TEST_ENVIRONMENTS


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


def reject_insecure_bypass_in_production(
    *, service_name: str, settings: Any | None = None
) -> None:
    """Fail closed when production-like runtimes enable auth bypass toggles."""
    if settings is not None and hasattr(settings, "is_production_like"):
        if not bool(getattr(settings, "is_production_like")):
            return
    elif settings is not None and hasattr(settings, "effective_environment"):
        env = str(getattr(settings, "effective_environment")).strip().lower()
        if env in _EXPLICIT_LOCAL_TEST_ENVIRONMENTS:
            return
    elif settings is not None and hasattr(settings, "environment"):
        env = str(getattr(settings, "environment")).strip().lower()
        if env in _EXPLICIT_LOCAL_TEST_ENVIRONMENTS:
            return
    elif _is_explicit_local_or_test_environment():
        # No explicit production-like signal from settings, but the runtime
        # environment is local/test. Skip the bypass check without weakening
        # the production fail-closed behavior.
        return

    # Canonical env-var check.
    _raise_if_bypass_in_nonlocal_env(service_name=service_name)

    # Backwards-compatible settings-field check (kept for callers that pass
    # pydantic-style settings objects with bypass fields).
    active_settings: list[str] = []
    if settings is not None:
        for field_name in _BYPASS_SETTINGS_FIELDS:
            if hasattr(settings, field_name) and _flag_is_truthy(
                getattr(settings, field_name)
            ):
                active_settings.append(field_name.upper())

    if active_settings:
        joined = ", ".join(sorted(set(active_settings)))
        raise RuntimeError(
            f"{service_name} startup rejected: production-like environment cannot enable auth bypass flags: {joined}."
        )
