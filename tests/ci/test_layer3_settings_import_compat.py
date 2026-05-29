"""Regression tests for Layer 3 settings import compatibility."""

from __future__ import annotations

from layer3_knowledge.config import Settings as ShimSettings
from layer3_knowledge.config import get_settings as shim_get_settings
from layer3_knowledge.config.settings import Settings as CanonicalSettings
from layer3_knowledge.config.settings import get_settings as canonical_get_settings


def test_settings_types_are_identical() -> None:
    """Legacy and canonical import paths must resolve the same Settings class."""
    assert ShimSettings is CanonicalSettings


def test_get_settings_callable_is_identical() -> None:
    """Legacy and canonical import paths must resolve the same factory."""
    assert shim_get_settings is canonical_get_settings
