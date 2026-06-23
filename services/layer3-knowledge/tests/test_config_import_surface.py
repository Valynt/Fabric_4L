"""Contract tests for the public config import surface."""

import os

from src.config import Settings, get_settings


def test_public_config_import_surface() -> None:
    """Ensure package exports support stable imports."""
    assert callable(Settings)
    assert callable(get_settings)


def test_get_settings_returns_settings_instance() -> None:
    """Ensure exported factory returns the exported settings type."""
    original_password = os.environ.get("NEO4J_PASSWORD")
    os.environ["NEO4J_PASSWORD"] = original_password or "test_password"

    get_settings.cache_clear()
    settings = get_settings()

    assert isinstance(settings, Settings)

    get_settings.cache_clear()
    if original_password is None:
        os.environ.pop("NEO4J_PASSWORD", None)
    else:
        os.environ["NEO4J_PASSWORD"] = original_password

