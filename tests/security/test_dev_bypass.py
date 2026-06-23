"""Dev Bypass Security Tests — P1 Gap Remediation

Validates that development authentication bypass flags are rejected in
production-like environments. Extends test_production_bypass_guardrails.py
with the specific gaps from the gap matrix: no production bypass tests for
the full set of bypass env vars and the DEBUG flag.

Gap matrix ref:
  P1 gap 15 — Dev Bypass Security: dev bypass in production

Author: Platform Security Team
"""

from __future__ import annotations

import os

import pytest

from value_fabric.shared.security.config import (
    ProductionSafetyValidator,
    validate_production_safety,
)

pytestmark = [
    pytest.mark.security,
    pytest.mark.production_safety,
]

# Bypass env vars checked by validate_production_safety.
# All bypass flags are now validated by ProductionSafetyValidator.
_BYPASS_VARS = [
    ("ALLOW_INSECURE_DEV_AUTH_BYPASS", "true"),
    ("ALLOW_INSECURE_DEV_AUTH_BYPASS", "1"),
    ("ALLOW_INSECURE_DEV_AUTH_BYPASS", "yes"),
    ("DEV_AUTH_BYPASS", "true"),
    ("DEV_AUTH_BYPASS", "1"),
    ("ALLOW_DEV_AUTH_BYPASS", "true"),
    ("AUTH_BYPASS_ENABLED", "true"),
]

_PRODUCTION_ENVS = ["production", "prod", "staging", "stage", "preprod"]

_BASE_PRODUCTION_ENV = {
    "ENVIRONMENT": "production",
    "JWT_SECRET": "x" * 48,
    "JWT_ISSUER": "https://auth.example.com",
    "JWT_AUDIENCE": "value-fabric-api",
    "DATABASE_URL": "postgresql://app_user:securepassword@db.internal:5432/valuefabric?sslmode=require",
    "CORS_ORIGINS": "https://app.example.com",
}


def _set_base_env(monkeypatch: pytest.MonkeyPatch, environment: str = "production") -> None:
    for key, value in _BASE_PRODUCTION_ENV.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv("ENVIRONMENT", environment)


# ---------------------------------------------------------------------------
# Bypass flags rejected in production
# ---------------------------------------------------------------------------


class TestBypassFlagsRejectedInProduction:
    """P1 gap 15: Every bypass flag must raise in production-like environments."""

    @pytest.mark.parametrize("bypass_var,bypass_value", _BYPASS_VARS)
    def test_bypass_flag_rejected_in_production(
        self, monkeypatch: pytest.MonkeyPatch, bypass_var: str, bypass_value: str
    ):
        """NEGATIVE: Each bypass flag raises RuntimeError in production."""
        _set_base_env(monkeypatch, "production")
        monkeypatch.setenv(bypass_var, bypass_value)
        with pytest.raises(RuntimeError, match=bypass_var):
            validate_production_safety(environment="production")

    @pytest.mark.parametrize("env", _PRODUCTION_ENVS)
    def test_bypass_rejected_across_all_production_like_envs(
        self, monkeypatch: pytest.MonkeyPatch, env: str
    ):
        """NEGATIVE: DEV_AUTH_BYPASS is rejected in all production-like envs."""
        _set_base_env(monkeypatch, env)
        monkeypatch.setenv("DEV_AUTH_BYPASS", "true")
        with pytest.raises(RuntimeError, match="DEV_AUTH_BYPASS"):
            validate_production_safety(environment=env)

    def test_no_bypass_flags_set_passes_validation(self, monkeypatch: pytest.MonkeyPatch):
        """POSITIVE: Production validation passes when no bypass flags are set."""
        _set_base_env(monkeypatch, "production")
        # Ensure no bypass vars are set
        for var, _ in _BYPASS_VARS:
            monkeypatch.delenv(var, raising=False)
        # Should not raise
        try:
            validate_production_safety(environment="production")
        except RuntimeError as exc:
            # Only fail if the error is about a bypass flag
            if any(var for var, _ in _BYPASS_VARS if var in str(exc)):
                pytest.fail(f"Bypass-free production config must not raise. Got: {exc}")


# ---------------------------------------------------------------------------
# DEBUG flag rejected in production
# ---------------------------------------------------------------------------


class TestDebugFlagRejectedInProduction:
    """DEBUG=true must be rejected in production environments."""

    def test_debug_true_rejected_in_production(self, monkeypatch: pytest.MonkeyPatch):
        """NEGATIVE: DEBUG=true raises in production."""
        _set_base_env(monkeypatch, "production")
        monkeypatch.setenv("DEBUG", "true")
        with pytest.raises(RuntimeError):
            validate_production_safety(environment="production")

    def test_debug_false_accepted_in_production(self, monkeypatch: pytest.MonkeyPatch):
        """POSITIVE: DEBUG=false is acceptable in production."""
        _set_base_env(monkeypatch, "production")
        monkeypatch.setenv("DEBUG", "false")
        # Should not raise due to DEBUG
        try:
            validate_production_safety(environment="production")
        except RuntimeError as exc:
            if "DEBUG" in str(exc):
                pytest.fail(f"DEBUG=false must not raise. Got: {exc}")

    def test_debug_unset_accepted_in_production(self, monkeypatch: pytest.MonkeyPatch):
        """POSITIVE: Unset DEBUG is acceptable in production."""
        _set_base_env(monkeypatch, "production")
        monkeypatch.delenv("DEBUG", raising=False)
        try:
            validate_production_safety(environment="production")
        except RuntimeError as exc:
            if "DEBUG" in str(exc):
                pytest.fail(f"Unset DEBUG must not raise. Got: {exc}")


# ---------------------------------------------------------------------------
# Bypass flags allowed (with warning) in development
# ---------------------------------------------------------------------------


class TestBypassFlagsAllowedInDevelopment:
    """Bypass flags must not raise in development — they should only log a warning."""

    def test_bypass_flag_does_not_raise_in_development(self, monkeypatch: pytest.MonkeyPatch):
        """POSITIVE: ALLOW_INSECURE_DEV_AUTH_BYPASS set to true is allowed in development."""
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.setenv("ALLOW_INSECURE_DEV_AUTH_BYPASS", "true")
        # Must not raise in development
        try:
            validate_production_safety(environment="development")
        except RuntimeError as exc:
            if "ALLOW_INSECURE_DEV_AUTH_BYPASS" in str(exc):
                pytest.fail(
                    f"Bypass flag must not raise in development. Got: {exc}"
                )

    def test_bypass_flag_logs_warning_in_development(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ):
        """POSITIVE: ALLOW_INSECURE_DEV_AUTH_BYPASS set to true logs at least one WARNING in development."""
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.setenv("ALLOW_INSECURE_DEV_AUTH_BYPASS", "true")
        with caplog.at_level("WARNING"):
            try:
                validate_production_safety(environment="development")
            except RuntimeError:
                pass  # If it raises, the warning check below still applies
        warning_records = [r for r in caplog.records if r.levelname == "WARNING"]
        assert len(warning_records) >= 1, (
            "validate_production_safety must emit at least one WARNING when "
            "ALLOW_INSECURE_DEV_AUTH_BYPASS set to true in development."
        )


# ---------------------------------------------------------------------------
# Adversarial bypass attempts
# ---------------------------------------------------------------------------


class TestAdversarialBypassAttempts:
    """Bypass flags must be rejected regardless of casing or encoding."""

    @pytest.mark.parametrize("value", ["TRUE", "True", "YES", "Yes", "1"])
    def test_bypass_flag_case_insensitive_rejection(
        self, monkeypatch: pytest.MonkeyPatch, value: str
    ):
        """ADVERSARIAL: Bypass flag is rejected regardless of value casing."""
        _set_base_env(monkeypatch, "production")
        monkeypatch.setenv("ALLOW_INSECURE_DEV_AUTH_BYPASS", value)
        with pytest.raises(RuntimeError):
            validate_production_safety(environment="production")

    def test_bypass_flag_with_whitespace_not_accepted(self, monkeypatch: pytest.MonkeyPatch):
        """ADVERSARIAL: Whitespace-padded ' true ' is stripped and rejected in production."""
        _set_base_env(monkeypatch, "production")
        monkeypatch.setenv("ALLOW_INSECURE_DEV_AUTH_BYPASS", " true ")
        # The validator calls .lower() which strips surrounding whitespace on comparison
        with pytest.raises(RuntimeError):
            validate_production_safety(environment="production")
