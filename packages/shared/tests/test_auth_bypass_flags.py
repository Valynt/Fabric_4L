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
def test_bypass_flag_detected_when_set(flag, monkeypatch):
    for other in ["DEV_AUTH_BYPASS", "ALLOW_INSECURE_DEV_AUTH_BYPASS", "ALLOW_DEV_AUTH_BYPASS", "AUTH_BYPASS_ENABLED"]:
        monkeypatch.delenv(other, raising=False)
    monkeypatch.setenv(flag, "true")
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


def test_local_env_allows_bypass_with_warning(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "local")
    monkeypatch.setenv("DEV_AUTH_BYPASS", "true")
    # Should not raise
    _raise_if_bypass_in_nonlocal_env(service_name="test-service")
