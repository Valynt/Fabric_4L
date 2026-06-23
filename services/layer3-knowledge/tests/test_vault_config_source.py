from __future__ import annotations

"""Tests for S3-01: Vault config source raises VaultSourceNotSupportedError.

Verifies:
- vault source type raises VaultSourceNotSupportedError (not silent empty dict)
- Error message names the source and explains the ESO migration path
- VaultSourceNotSupportedError is a RuntimeError subclass
- env and file source types still work normally
- No silent empty-dict return from vault source
"""


import pytest

from src.config.manager import (
    ConfigSource,
    ConfigurationManager,
    VaultSourceNotSupportedError,
)


def _make_vault_source(name: str = "test-vault") -> ConfigSource:
    return ConfigSource(
        name=name,
        type="vault",
        location="secret/layer3/config",
        required=False,
    )


# ---------------------------------------------------------------------------
# VaultSourceNotSupportedError class tests
# ---------------------------------------------------------------------------


def test_vault_source_not_supported_error_is_runtime_error():
    """VaultSourceNotSupportedError must be a RuntimeError subclass."""
    err = VaultSourceNotSupportedError("test")
    assert isinstance(err, RuntimeError)


def test_vault_source_not_supported_error_message():
    """Error message must be non-empty."""
    err = VaultSourceNotSupportedError("vault source 'x' is not supported")
    assert "vault" in str(err).lower() or "x" in str(err)


# ---------------------------------------------------------------------------
# _load_from_vault raises, not returns empty dict
# ---------------------------------------------------------------------------


def test_vault_source_raises_not_returns_empty_dict():
    """_load_from_vault must raise VaultSourceNotSupportedError, not return {}."""
    manager = ConfigurationManager.__new__(ConfigurationManager)
    source = _make_vault_source()

    with pytest.raises(VaultSourceNotSupportedError):
        manager._load_from_vault(source)


def test_vault_source_error_message_names_source():
    """Error message must name the source and mention ESO migration."""
    manager = ConfigurationManager.__new__(ConfigurationManager)
    source = _make_vault_source("my-vault-source")

    with pytest.raises(VaultSourceNotSupportedError) as exc_info:
        manager._load_from_vault(source)

    msg = str(exc_info.value)
    assert "my-vault-source" in msg
    assert "env" in msg.lower() or "environment" in msg.lower() or "ESO" in msg or "External Secrets" in msg


def test_vault_source_error_is_not_silent():
    """Vault source must not silently return empty config."""
    manager = ConfigurationManager.__new__(ConfigurationManager)
    source = _make_vault_source()

    result = None
    raised = False
    try:
        result = manager._load_from_vault(source)
    except VaultSourceNotSupportedError:
        raised = True

    assert raised, "VaultSourceNotSupportedError was not raised"
    assert result is None, "vault source returned a value instead of raising"


def test_vault_source_raises_runtime_error():
    """_load_from_vault must raise a RuntimeError (or subclass)."""
    manager = ConfigurationManager.__new__(ConfigurationManager)
    source = _make_vault_source()

    with pytest.raises(RuntimeError):
        manager._load_from_vault(source)


# ---------------------------------------------------------------------------
# Other source types still work
# ---------------------------------------------------------------------------


def test_env_source_type_still_works(monkeypatch):
    """env source type must not be affected by the vault change."""
    monkeypatch.setenv("LAYER3_NEO4J_URI", "bolt://localhost:7687")
    monkeypatch.setenv("LAYER3_NEO4J_PASSWORD", "test")
    monkeypatch.setenv("LAYER3_DATABASE_URL", "postgresql://localhost/test")

    manager = ConfigurationManager.__new__(ConfigurationManager)
    manager.environment = "development"

    # _load_from_env takes no source argument — call it directly
    result = manager._load_from_env()
    # Result should be a dict (env vars are loaded into it)
    assert isinstance(result, dict)
