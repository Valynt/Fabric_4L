"""Compatibility shim; canonical Layer 6 config lives under layer6.settings."""

from .settings import (
    Layer6Settings,
    Settings,
    get_layer6_settings,
    get_settings,
    validate_layer6_startup_settings,
)

__all__ = [
    "Layer6Settings",
    "Settings",
    "get_layer6_settings",
    "get_settings",
    "validate_layer6_startup_settings",
]
