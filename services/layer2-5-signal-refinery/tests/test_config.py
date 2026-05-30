"""Tests for L2.5 Signal Refinery configuration."""

from __future__ import annotations

import os

import pytest
from pydantic import ValidationError

from layer2_5_signal_refinery.config import Settings


class TestJWTSecret:
    def test_jwt_secret_required_no_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """jwt_secret must be explicitly provided; the weak default is removed."""
        monkeypatch.delenv("JWT_SECRET", raising=False)
        # Ensure pydantic-settings does not pick up a stray env value
        monkeypatch.setenv("JWT_SECRET", "")
        with pytest.raises((ValidationError, ValueError)):
            Settings()

    def test_jwt_secret_accepts_strong_value(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("JWT_SECRET", "strong-production-secret-minimum-32-chars-long")
        settings = Settings()
        assert settings.jwt_secret == "strong-production-secret-minimum-32-chars-long"
