"""
Configuration management for the AuditOrchestrator agent.

This module provides the :class:`ConfigManager` which loads configuration
from multiple sources with a defined precedence:

1. Environment variables (``AUDIT__*`` prefix, double-underscore for nesting)
2. YAML config file (``agents/skills/repo-audit/config.yaml``, legacy ``.agent/skills/repo-audit/config.yaml`` fallback)
3. Default values defined in the :class:`AuditConfig` Pydantic model

The configuration is validated using Pydantic v2 and provides helpers for
accessing nested values and checking feature flags.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from .models import (
    AuditArea,
    AuditConfig,
    Severity,
)

logger = logging.getLogger(__name__)

ENV_PREFIX: str = "AUDIT__"
DEFAULT_YAML_PATH: str = "agents/skills/repo-audit/config.yaml"
LEGACY_YAML_PATH: str = ".agent/skills/repo-audit/config.yaml"


def _convert_env_value(value: str) -> Any:
    """Convert an environment variable string to an appropriate Python type.

    Coercion order:

    1. ``null`` / ``none`` / empty → ``None``
    2. Integers (e.g., ``"1"``, ``"0"``, ``"42"``)
    3. Floats (e.g., ``"3.14"``)
    4. Explicit boolean words (``true``/``false``/``yes``/``no``/``on``/``off``);
       numeric ``"1"`` and ``"0"`` are treated as integers, not booleans.
    5. Comma-separated lists
    6. Plain strings

    Args:
        value: The raw environment variable string.

    Returns:
        The converted value with an appropriate Python type.
    """
    stripped = value.strip()
    lower = stripped.lower()

    # None / empty
    if lower in ("null", "none", ""):
        return None

    # Integer
    try:
        return int(stripped)
    except ValueError:
        pass

    # Float
    try:
        return float(stripped)
    except ValueError:
        pass

    # Boolean words only (not numeric "1"/"0")
    if lower in ("true", "yes", "on"):
        return True
    if lower in ("false", "no", "off"):
        return False

    # List (comma-separated)
    if "," in stripped:
        return [item.strip() for item in stripped.split(",") if item.strip()]

    # String (default)
    return stripped


def _parse_nested_env(env_vars: dict[str, str]) -> dict[str, Any]:
    """Parse environment variables with the AUDIT__ prefix into a nested dict.

    Uses double-underscore as a nesting delimiter, e.g.:
    ``AUDIT__REPO_URL=https://...`` → ``{"repo_url": "https://..."}``
    ``AUDIT__AREA_WEIGHTS__ARCHITECTURE=0.15`` → ``{"area_weights": {"architecture": 0.15}}``

    Args:
        env_vars: Dictionary of environment variable names to values.

    Returns:
        A nested dictionary representing the parsed configuration.
    """
    result: dict[str, Any] = {}

    for key, raw_value in env_vars.items():
        if not key.startswith(ENV_PREFIX):
            continue

        # Strip prefix and split by double underscore
        stripped = key[len(ENV_PREFIX):]
        parts = stripped.lower().split("__")
        value = _convert_env_value(raw_value)

        # Navigate/create nested dict structure
        current = result
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]

        current[parts[-1]] = value

    return result


def _try_load_yaml(path: str | Path) -> dict[str, Any] | None:
    """Attempt to load a YAML configuration file.

    Args:
        path: Filesystem path to the YAML file.

    Returns:
        Parsed YAML content as a dictionary, or ``None`` if the file
        does not exist or cannot be parsed.
    """
    file_path = Path(path)
    if not file_path.exists():
        logger.debug("YAML config not found at %s", file_path)
        return None

    try:
        import yaml
        with open(file_path, encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        if isinstance(data, dict):
            logger.debug("Loaded YAML config from %s", file_path)
            return data
        logger.warning("YAML config at %s is not a dict, ignoring", file_path)
        return None
    except ImportError:
        logger.warning(
            "PyYAML not installed, cannot load YAML config from %s", file_path
        )
        return None
    except Exception as exc:
        logger.warning("Failed to parse YAML config at %s: %s", file_path, exc)
        return None


def _coerce_area_weights(raw: dict[str, Any]) -> dict[AuditArea, float]:
    """Convert a raw dictionary of area weights to typed :class:`AuditArea` keys.

    Handles various key formats: the full enum value string, the short name,
    or the enum member name.

    Args:
        raw: Raw dictionary with string keys and float values.

    Returns:
        Dictionary with :class:`AuditArea` enum keys and float weights.
    """
    result: dict[AuditArea, float] = {}
    for key, value in raw.items():
        area = _resolve_audit_area(str(key))
        if area is not None:
            result[area] = float(value)
    return result


def _resolve_audit_area(key: str) -> AuditArea | None:
    """Resolve a string key to an :class:`AuditArea` enum member.

    Handles full value strings, short letter prefixes, and member names.

    Args:
        key: The string key to resolve.

    Returns:
        The matching :class:`AuditArea` member, or ``None`` if not found.
    """
    key_lower = key.lower().strip()

    # Try exact match on enum values
    for area in AuditArea:
        if area.value.lower() == key_lower:
            return area
        # Try short prefix match, e.g. "a: architecture..." matches "a" or "architecture"
        prefix = area.value.split(":")[0].lower().strip()
        if key_lower == prefix:
            return area
        # Try member name match, e.g. "ARCHITECTURE"
        if area.name.lower() == key_lower:
            return area
        # Try the part after the colon
        name_part = area.value.split(":")[-1].strip().lower()
        if key_lower == name_part:
            return area

    return None


class ConfigManager:
    """Configuration manager for the AuditOrchestrator agent.

    Loads and merges configuration from three sources with the following
    precedence (highest to lowest):

    1. **Environment variables** — Keys prefixed with ``AUDIT__`` using
       double-underscore as a nesting delimiter (e.g. ``AUDIT__REPO_URL``,
       ``AUDIT__AREA_WEIGHTS__ARCHITECTURE``).
    2. **YAML config file** — Located at ``agents/skills/repo-audit/config.yaml``
       by default (legacy ``.agent/skills/repo-audit/config.yaml`` fallback),
       customizable via the ``yaml_path`` parameter.
    3. **Pydantic defaults** — Defined in the :class:`AuditConfig` model.

    The manager handles type coercion, nested key resolution, and validation
    through Pydantic v2.

    Example:
        >>> from layer4_agents.agents.audit_orchestrator.config import ConfigManager
        >>> mgr = ConfigManager()
        >>> config = mgr.load()
        >>> config.repo_url
        'https://github.com/org/repo'
    """

    def __init__(
        self,
        yaml_path: str = DEFAULT_YAML_PATH,
        env_prefix: str = ENV_PREFIX,
    ) -> None:
        """Initialize the configuration manager.

        Args:
            yaml_path: Path to the YAML configuration file. If a relative
                path is given, it is resolved from the current working directory.
            env_prefix: Prefix for environment variables to read.
        """
        self.yaml_path = Path(yaml_path)
        self.env_prefix = env_prefix

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def load(self, overrides: dict[str, Any] | None = None) -> AuditConfig:
        """Load and merge configuration from all sources.

        Merges configuration in the following order (later sources override
        earlier ones):

        1. Pydantic model defaults
        2. YAML config file (if present)
        3. Environment variables with ``AUDIT__`` prefix
        4. Explicit ``overrides`` dictionary (if provided)

        Args:
            overrides: Optional dictionary of explicit config overrides
                with the highest precedence.

        Returns:
            A validated :class:`AuditConfig` instance.

        Raises:
            ValueError: If the merged configuration fails Pydantic validation.
        """
        # 1. Start with empty dict (Pydantic defaults will fill in)
        merged: dict[str, Any] = {}

        # 2. Apply YAML config (canonical path, then legacy fallback).
        # The legacy fallback only applies when the caller used the canonical
        # default path; a deliberately-supplied custom path that is absent
        # should yield defaults, not silently import the legacy file.
        yaml_data = _try_load_yaml(self.yaml_path)
        if (
            yaml_data is None
            and not self.yaml_path.exists()
            and self.yaml_path == Path(DEFAULT_YAML_PATH)
        ):
            yaml_data = _try_load_yaml(LEGACY_YAML_PATH)
        if yaml_data:
            merged = self._deep_merge(merged, yaml_data)

        # 3. Apply environment variables
        env_data = _parse_nested_env(dict(os.environ))
        if env_data:
            merged = self._deep_merge(merged, env_data)

        # 4. Apply explicit overrides
        if overrides:
            merged = self._deep_merge(merged, overrides)

        # Coerce area_weights if present as a plain dict
        if "area_weights" in merged and not isinstance(
            next(iter(merged["area_weights"].keys()), None), AuditArea
        ):
            merged["area_weights"] = _coerce_area_weights(merged["area_weights"])

        # Coerce areas_enabled if present as strings
        if "areas_enabled" in merged and merged["areas_enabled"]:
            raw = merged["areas_enabled"]
            if isinstance(raw, list) and raw and isinstance(raw[0], str):
                resolved = []
                for item in raw:
                    area = _resolve_audit_area(item)
                    if area:
                        resolved.append(area)
                merged["areas_enabled"] = resolved

        # Coerce severity_threshold if present as a string
        if "severity_threshold" in merged and isinstance(
            merged["severity_threshold"], str
        ):
            try:
                merged["severity_threshold"] = Severity(
                    merged["severity_threshold"].lower()
                )
            except ValueError:
                logger.warning(
                    "Invalid severity_threshold '%s', using default",
                    merged["severity_threshold"],
                )
                del merged["severity_threshold"]

        try:
            return AuditConfig(**merged)
        except Exception as exc:
            logger.error("Configuration validation failed: %s", exc)
            raise ValueError(f"Invalid audit configuration: {exc}") from exc

    def load_or_default(
        self,
        overrides: dict[str, Any] | None = None,
    ) -> AuditConfig:
        """Load configuration, falling back to defaults on any error.

        Unlike :meth:`load`, this method catches all exceptions and returns
        a configuration built from defaults and overrides only.

        Args:
            overrides: Optional dictionary of explicit config overrides.

        Returns:
            A validated :class:`AuditConfig` instance using defaults if
            other sources fail.
        """
        try:
            return self.load(overrides=overrides)
        except Exception as exc:
            logger.warning(
                "Config loading failed (%s), using defaults with overrides", exc
            )
            return AuditConfig(**(overrides or {}))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _deep_merge(
        base: dict[str, Any], override: dict[str, Any]
    ) -> dict[str, Any]:
        """Recursively merge ``override`` into ``base``.

        Nested dictionaries are merged recursively; all other values are
        replaced outright.

        Args:
            base: The base dictionary to merge into.
            override: Dictionary whose values take precedence.

        Returns:
            A new dictionary containing the merged result.
        """
        result = dict(base)
        for key, value in override.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = ConfigManager._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    def get_env_snapshot(self) -> dict[str, str]:
        """Return all environment variables matching the configured prefix.

        Returns:
            Dictionary of matching environment variable names to their
            raw string values.
        """
        return {
            k: v for k, v in os.environ.items()
            if k.startswith(self.env_prefix)
        }

    @property
    def has_yaml_config(self) -> bool:
        """Check whether the YAML configuration file exists.

        Returns:
            ``True`` if the YAML file exists and is readable.
        """
        return self.yaml_path.exists() and self.yaml_path.is_file()

    @property
    def has_env_overrides(self) -> bool:
        """Check whether any environment overrides are defined.

        Returns:
            ``True`` if at least one ``AUDIT__`` environment variable exists.
        """
        return any(k.startswith(self.env_prefix) for k in os.environ)


__all__ = [
    "ConfigManager",
    "ENV_PREFIX",
    "DEFAULT_YAML_PATH",
    "LEGACY_YAML_PATH",
]
