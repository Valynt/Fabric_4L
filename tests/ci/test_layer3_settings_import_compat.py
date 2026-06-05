"""Regression tests for Layer 3 settings import compatibility."""

from __future__ import annotations

from pathlib import Path

import src
from src.config import Settings as ShimSettings
from src.config import get_settings as shim_get_settings
from src.config.settings import Settings as CanonicalSettings
from src.config.settings import get_settings as canonical_get_settings

ROOT = Path(__file__).resolve().parents[2]
LAYER3_SRC = ROOT / "services" / "layer3-knowledge" / "src"
LAYER4_SRC = ROOT / "services" / "layer4-agents" / "src"


def test_settings_types_are_identical() -> None:
    """Legacy and canonical import paths must resolve the same Settings class."""
    assert ShimSettings is CanonicalSettings


def test_get_settings_callable_is_identical() -> None:
    """Legacy and canonical import paths must resolve the same factory."""
    assert shim_get_settings is canonical_get_settings


def test_root_collection_src_namespace_prefers_layer3_for_overlapping_modules() -> None:
    """Root pytest collection must resolve legacy src imports deterministically."""

    for name in ("agents", "api", "analytics", "models", "retrieval", "services", "tools"):
        assert hasattr(src, name)

    assert list(src.api.__path__)[:2] == [str(LAYER3_SRC / "api"), str(LAYER4_SRC / "api")]
    assert list(src.agents.__path__)[:2] == [str(LAYER3_SRC / "agents"), str(LAYER4_SRC / "agents")]
    assert list(src.services.__path__)[:2] == [str(LAYER3_SRC / "services"), str(LAYER4_SRC / "services")]
