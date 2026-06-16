import logging

import pytest

from value_fabric.shared.identity.auth_mode import (
    _bypass_flags_are_set,
    _raise_if_bypass_in_nonlocal_env,
    assert_safe_jwt_and_bypass_configuration,
    is_dev_bypass_acknowledged,
    is_dev_bypass_enabled,
    validate_dev_bypass_configuration,
)

_BYPASS_FLAGS = [
    "DEV_AUTH_BYPASS",
    "ALLOW_INSECURE_DEV_AUTH_BYPASS",
    "ALLOW_DEV_AUTH_BYPASS",
    "AUTH_BYPASS_ENABLED",
]


@pytest.mark.parametrize("flag", _BYPASS_FLAGS)
@pytest.mark.parametrize("value", [
    "true",
    "1",
    "yes",
    "on",
    "i_understand_risk",
])
def test_bypass_flag_detected_when_set(flag, value, monkeypatch):
    for other in _BYPASS_FLAGS:
        monkeypatch.delenv(other, raising=False)
    monkeypatch.setenv(flag, value)
    assert _bypass_flags_are_set() == {flag}


@pytest.mark.parametrize("flag", _BYPASS_FLAGS)
@pytest.mark.parametrize("value", [
    "false",
    "0",
    "no",
    "off",
    "",
])
def test_falseish_bypass_values_not_detected(flag, value, monkeypatch):
    for other in _BYPASS_FLAGS:
        monkeypatch.delenv(other, raising=False)
    monkeypatch.setenv(flag, value)
    assert _bypass_flags_are_set() == set()


def test_no_bypass_flags_detected_by_default(monkeypatch):
    for flag in _BYPASS_FLAGS:
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


@pytest.mark.parametrize("func", [
    is_dev_bypass_enabled,
    is_dev_bypass_acknowledged,
    validate_dev_bypass_configuration,
    assert_safe_jwt_and_bypass_configuration,
])
def test_public_functions_return_safe_noop_and_warn_when_flag_set(
    func, monkeypatch, caplog
):
    for flag in _BYPASS_FLAGS:
        monkeypatch.delenv(flag, raising=False)
    monkeypatch.setenv("DEV_AUTH_BYPASS", "true")
    with caplog.at_level(logging.WARNING):
        result = func()
    assert result in (None, False)
    assert any(
        record.levelno == logging.WARNING
        and "DEV_AUTH_BYPASS" in record.message
        for record in caplog.records
    )


def test_public_functions_return_safe_noop_without_flag(monkeypatch, caplog):
    for flag in _BYPASS_FLAGS:
        monkeypatch.delenv(flag, raising=False)
    with caplog.at_level(logging.WARNING):
        assert is_dev_bypass_enabled() is False
        assert is_dev_bypass_acknowledged() is False
        assert validate_dev_bypass_configuration() is None
        assert assert_safe_jwt_and_bypass_configuration() is None
    assert not any(
        "auth bypass" in record.message.lower() for record in caplog.records
    )
