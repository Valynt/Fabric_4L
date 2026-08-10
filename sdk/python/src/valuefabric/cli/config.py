"""CLI configuration management."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import typer
from rich import print as rich_print

from ..errors import ConfigurationError

app = typer.Typer(help="Manage CLI configuration")

CONFIG_DIR = Path.home() / ".config" / "valuefabric"
CONFIG_FILE = CONFIG_DIR / "config.toml"

DEFAULT_PROFILE = "default"


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


def _format_toml_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        return "[" + ", ".join(_format_toml_value(item) for item in value) + "]"
    escaped = str(value).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _dump_profile_toml(config: dict[str, Any]) -> str:
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


def _check_token_expiration(profile_config: dict, profile_name: str) -> None:
    """Check if JWT token is expired and warn user.

    Args:
        profile_config: The profile configuration dict
        profile_name: Name of the profile being loaded
    """
    jwt_expires_at = profile_config.get("jwt_expires_at")
    if jwt_expires_at:
        try:
            exp_timestamp = float(jwt_expires_at)
            if datetime.now(timezone.utc).timestamp() > exp_timestamp:
                rich_print(
                    f"[yellow]Warning: JWT token for profile '{profile_name}' has expired. "
                    f"Run 'vf auth login' to re-authenticate.[/yellow]"
                )
        except (ValueError, TypeError):
            # Invalid timestamp format, ignore
            pass


def _load_config() -> dict:
    if not CONFIG_FILE.exists():
        return {}
    try:
        return _load_profile_toml(CONFIG_FILE.read_text(encoding="utf-8"))
    except ValueError as e:
        raise ConfigurationError(
            f"Config file is corrupted: {CONFIG_FILE}\n"
            f"Parse error: {e}\n"
            f"You may need to delete it and re-run 'vf config set-url'"
        ) from e


def _save_config(config: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(_dump_profile_toml(config), encoding="utf-8")


def get_active_profile() -> str:
    config = _load_config()
    return config.get("active_profile", DEFAULT_PROFILE)


def get_profile_config(profile: str | None = None) -> dict:
    config = _load_config()
    profile = profile or config.get("active_profile", DEFAULT_PROFILE)
    profile_config = config.get("profiles", {}).get(profile, {})
    _check_token_expiration(profile_config, profile)
    return profile_config


@app.command("set-url")
def set_url(
    url: str,
    profile: str = typer.Option("default", "--profile", "-p", help="Profile name"),
) -> None:
    """Set the base URL for a profile."""
    config = _load_config()
    config.setdefault("profiles", {}).setdefault(profile, {})["base_url"] = url
    _save_config(config)
    rich_print(f"[green]Base URL set for profile '{profile}': {url}[/green]")


@app.command("set-api-key")
def set_api_key(
    api_key: str,
    profile: str = typer.Option("default", "--profile", "-p", help="Profile name"),
) -> None:
    """Set the API key for a profile."""
    config = _load_config()
    config.setdefault("profiles", {}).setdefault(profile, {})["api_key"] = api_key
    _save_config(config)
    rich_print(f"[green]API key set for profile '{profile}'.[/green]")


@app.command("use-profile")
def use_profile(
    profile: str,
) -> None:
    """Switch the active profile."""
    config = _load_config()
    config["active_profile"] = profile
    _save_config(config)
    rich_print(f"[green]Active profile set to '{profile}'.[/green]")


@app.command("show")
def show_config() -> None:
    """Display the current configuration."""
    config = _load_config()
    active = config.get("active_profile", DEFAULT_PROFILE)
    rich_print(f"[bold]Active profile:[/bold] {active}")
    profiles = config.get("profiles", {})
    for name, values in profiles.items():
        marker = " *" if name == active else ""
        rich_print(f"\n[bold]{name}{marker}[/bold]")
        for key, value in values.items():
            display = value if key != "api_key" else "*" * 8
            rich_print(f"  {key}: {display}")
