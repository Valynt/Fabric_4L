"""Contract tests for SDK profile parsing and CLI configuration failures."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from valuefabric.cli.config import (
    _load_config,
    _load_profile_toml,
    _parse_toml_value,
    get_profile_config,
)
from valuefabric.cli.main import main
from valuefabric.errors import ConfigurationError


def test_valid_profile_parsing_preserves_supported_scalar_types() -> None:
    result = _load_profile_toml(
        """
active_profile = "prod"
[profiles."prod"]
base_url = "https://api.example.com"
api_key = "secret"
timeout = 45
enabled = true
scopes = ["read", "write"]
"""
    )

    assert result == {
        "active_profile": "prod",
        "profiles": {
            "prod": {
                "base_url": "https://api.example.com",
                "api_key": "secret",
                "timeout": 45,
                "enabled": True,
                "scopes": ["read", "write"],
            }
        },
    }


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("unknown-token", "unknown-token"),
        ("3.5", 3.5),
        ("false", False),
        ("[]", []),
    ],
)
def test_documented_value_fallbacks(raw: str, expected: object) -> None:
    assert _parse_toml_value(raw) == expected


@pytest.mark.parametrize(
    "text",
    [
        'profiles = false\n[profiles.default]\nbase_url = "https://api.example.com"',
        'active_profile = "default"\nthis line has no equals',
    ],
)
def test_invalid_profile_structure_is_rejected(text: str) -> None:
    with pytest.raises(ValueError):
        _load_profile_toml(text)


def test_missing_config_returns_empty_mapping(tmp_path: Path) -> None:
    missing = tmp_path / "missing.toml"
    with patch("valuefabric.cli.config.CONFIG_FILE", missing):
        assert _load_config() == {}


def test_corrupt_config_raises_safe_configuration_error(tmp_path: Path) -> None:
    config_file = tmp_path / "config.toml"
    config_file.write_text("invalid line", encoding="utf-8")

    with (
        patch("valuefabric.cli.config.CONFIG_FILE", config_file),
        pytest.raises(ConfigurationError) as captured,
    ):
        _load_config()

    message = str(captured.value)
    assert "Config file is corrupted" in message
    assert "line 1" in message
    assert "invalid line" not in message
    assert "api-key-secret" not in message


def test_corrupt_config_error_does_not_echo_secret_line(tmp_path: Path) -> None:
    secret = "api-key-secret"
    config_file = tmp_path / "config.toml"
    config_file.write_text(secret, encoding="utf-8")

    with (
        patch("valuefabric.cli.config.CONFIG_FILE", config_file),
        pytest.raises(ConfigurationError) as captured,
    ):
        _load_config()

    assert secret not in str(captured.value)
    assert captured.value.__cause__ is not None
    assert secret not in str(captured.value.__cause__)
    assert secret not in repr(captured.value.__cause__)


def test_explicit_profile_takes_precedence_over_active_profile() -> None:
    config = {
        "active_profile": "dev",
        "profiles": {
            "dev": {"base_url": "https://dev.example.com"},
            "prod": {"base_url": "https://prod.example.com"},
        },
    }
    with patch("valuefabric.cli.config._load_config", return_value=config):
        assert get_profile_config("prod") == {"base_url": "https://prod.example.com"}


def test_missing_required_profile_fields_remain_explicitly_empty() -> None:
    config = {"active_profile": "empty", "profiles": {"empty": {}}}
    with patch("valuefabric.cli.config._load_config", return_value=config):
        assert get_profile_config() == {}


def test_cli_main_converts_configuration_error_to_safe_exit() -> None:
    with (
        patch(
            "valuefabric.cli.main.app",
            side_effect=ConfigurationError("missing base URL"),
        ),
        patch("valuefabric.cli.main.rich_print") as mock_print,
        pytest.raises(SystemExit) as captured,
    ):
        main()

    assert captured.value.code == 1
    mock_print.assert_called_once_with("[red]Configuration error:[/red] missing base URL")
