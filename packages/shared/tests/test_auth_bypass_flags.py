import logging

import pytest

from value_fabric.shared.identity.auth_mode import (
    _bypass_flags_are_set,
    _raise_if_bypass_in_nonlocal_env,
)


@pytest.mark.parametrize("flag", [
    "DEV_AUTH_BYPASS",
    "ALLOW_INSECURE_DEV_AUTH_BYPASS",
    "ALLOW_DEV_AUTH_BYPASS",
    "AUTH_BYPASS_ENABLED",
])
@pytest.mark.parametrize("value", [
    "true",
    "1",
    "yes",
    "on",
    "i_understand_risk",
])
def test_bypass_flag_detected_when_set(flag, value, monkeypatch):
    for other in ["DEV_AUTH_BYPASS", "ALLOW_INSECURE_DEV_AUTH_BYPASS", "ALLOW_DEV_AUTH_BYPASS", "AUTH_BYPASS_ENABLED"]:
        monkeypatch.delenv(other, raising=False)
    monkeypatch.setenv(flag, value)
    assert _bypass_flags_are_set() == {flag}


def test_no_bypass_flags_detected_by_default(monkeypatch):
    for flag in ["DEV_AUTH_BYPASS", "ALLOW_INSECURE_DEV_AUTH_BYPASS", "ALLOW_DEV_AUTH_BYPASS", "AUTH_BYPASS_ENABLED"]:
        monkeypatch.delenv(flag, raising=False)
    assert _bypass_flags_are_set() == set()


def test_nonlocal_env_raises_when_bypass_set(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DEV_AUTH_BYPASS", "true")
    with pytest.raises(RuntimeError, match="auth bypass flags"):
        _raise_if_bypass_in_nonlocal_env(service_name="test-service")


def test_local_env_allows_bypass_with_warning(monkeypatch, caplog):
    monkeypatch.setenv("ENVIRONMENT", "local")
    monkeypatch.setenv("DEV_AUTH_BYPASS", "true")
    with caplog.at_level(logging.WARNING):
        # Should not raise
        _raise_if_bypass_in_nonlocal_env(service_name="test-service")
    assert any(
        record.levelno == logging.WARNING
        and "DEV_AUTH_BYPASS" in record.message
        and "local" in record.message
        for record in caplog.records
    )
