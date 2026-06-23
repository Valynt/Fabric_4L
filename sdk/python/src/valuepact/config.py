"""Non-secret ValuePact CLI profile and context storage."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from valuefabric.errors import ConfigurationError

DEFAULT_PROFILE = "default"


def config_dir() -> Path:
    override = os.environ.get("VALUEPACT_CONFIG_DIR")
    if override:
        return Path(override)
    return Path.home() / ".config" / "valuepact"


def config_file() -> Path:
    return config_dir() / "config.toml"


def load_config() -> dict[str, Any]:
    path = config_file()
    if not path.exists():
        return {}
    try:
        data = _load_profile_toml(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise ConfigurationError(f"Config file is corrupted: {path}") from exc
    if not isinstance(data, dict):
        raise ConfigurationError(f"Config file is invalid: {path}")
    return data


def _parse_toml_value(raw: str) -> Any:
    value = raw.strip()
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1].replace('\\"', '"').replace("\\\\", "\\")
    if value == "true":
        return True
    if value == "false":
        return False
    if value.startswith("[") and value.endswith("]"):
        items = value[1:-1].strip()
        if not items:
            return []
        return [_parse_toml_value(item.strip()) for item in items.split(",")]
    try:
        return int(value)
    except ValueError:
        try:
            return float(value)
        except ValueError:
            return value


def _load_profile_toml(text: str) -> dict[str, Any]:
    data: dict[str, Any] = {}
    current_profile: dict[str, Any] | None = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[profiles.") and line.endswith("]"):
            profile_name = line[len("[profiles.") : -1].strip('"')
            profiles = data.setdefault("profiles", {})
            if not isinstance(profiles, dict):
                raise ValueError("profiles must be a table")
            current_profile = profiles.setdefault(profile_name, {})
            continue
        if "=" not in line:
            raise ValueError(f"invalid line: {line}")
        key, raw_value = line.split("=", 1)
        target = current_profile if current_profile is not None else data
        target[key.strip()] = _parse_toml_value(raw_value)
    return data


def save_config(config: dict[str, Any]) -> None:
    scrub_secrets(config)
    path = config_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_dump_toml(config), encoding="utf-8")


def _format_toml_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        return "[" + ", ".join(_format_toml_value(item) for item in value) + "]"
    escaped = str(value).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _dump_toml(config: dict[str, Any]) -> str:
    lines: list[str] = []
    active = config.get("active_profile")
    if active is not None:
        lines.append(f"active_profile = {_format_toml_value(active)}")
        lines.append("")
    profiles = config.get("profiles", {})
    if isinstance(profiles, dict):
        for profile_name, profile in profiles.items():
            escaped_name = str(profile_name).replace("\\", "\\\\").replace('"', '\\"')
            lines.append(f'[profiles."{escaped_name}"]')
            if isinstance(profile, dict):
                for key, value in profile.items():
                    lines.append(f"{key} = {_format_toml_value(value)}")
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def scrub_secrets(config: dict[str, Any]) -> None:
    profiles = config.get("profiles", {})
    if not isinstance(profiles, dict):
        return
    for profile in profiles.values():
        if isinstance(profile, dict):
            for key in ("token", "access_token", "refresh_token", "api_key", "authorization"):
                profile.pop(key, None)


def active_profile_name(explicit_profile: str | None = None) -> str:
    if explicit_profile:
        return explicit_profile
    env_profile = os.environ.get("VALUEPACT_PROFILE")
    if env_profile:
        return env_profile
    return str(load_config().get("active_profile", DEFAULT_PROFILE))


def get_profile(profile_name: str) -> dict[str, Any]:
    profiles = load_config().get("profiles", {})
    if not isinstance(profiles, dict):
        return {}
    profile = profiles.get(profile_name, {})
    return profile if isinstance(profile, dict) else {}


def upsert_profile(profile_name: str, values: dict[str, Any], *, make_active: bool = True) -> None:
    config = load_config()
    profiles = config.setdefault("profiles", {})
    if not isinstance(profiles, dict):
        raise ConfigurationError("Config 'profiles' must be a table.")
    profile = profiles.setdefault(profile_name, {})
    if not isinstance(profile, dict):
        raise ConfigurationError(f"Profile '{profile_name}' is invalid.")
    for key, value in values.items():
        if value is not None:
            profile[key] = value
    if make_active:
        config["active_profile"] = profile_name
    save_config(config)


def clear_active_profile() -> None:
    config = load_config()
    config.pop("active_profile", None)
    save_config(config)
