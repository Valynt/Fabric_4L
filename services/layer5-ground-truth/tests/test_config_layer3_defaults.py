from __future__ import annotations

"""Regression tests for Layer 3 integration config defaults and validation."""


import pytest
from pydantic import ValidationError

from layer5_ground_truth.config import Settings


def _clear_layer3_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in ("LAYER3_BASE_URL", "LAYER3_API_KEY", "LAYER3_TIMEOUT_SECONDS"):
        monkeypatch.delenv(key, raising=False)


def test_layer3_base_url_default_targets_layer3_port(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_layer3_env(monkeypatch)

    settings = Settings()

    assert settings.layer3_base_url == "http://localhost:8003"


@pytest.mark.parametrize(
    "unsafe_value",
    [
        "localhost:8003",
        "ftp://localhost:8003",
        "http://localhost:8003/api",
        "http://localhost:8003?debug=true",
    ],
)
def test_layer3_base_url_rejects_malformed_or_unsafe_values(
    monkeypatch: pytest.MonkeyPatch,
    unsafe_value: str,
) -> None:
    _clear_layer3_env(monkeypatch)
    monkeypatch.setenv("LAYER3_BASE_URL", unsafe_value)

    with pytest.raises(ValidationError):
        Settings()


def test_layer3_base_url_trims_trailing_slash(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_layer3_env(monkeypatch)
    monkeypatch.setenv("LAYER3_BASE_URL", "http://localhost:8003/")

    settings = Settings()

    assert settings.layer3_base_url == "http://localhost:8003"
