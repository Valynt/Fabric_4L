"""Tests for JWT algorithm validation and environment enforcement (P2-004)."""

from __future__ import annotations

import pytest
from value_fabric.shared.crypto.jwt_algorithm import (
    ALLOWED_ALGORITHMS,
    JWTAlgorithm,
    validate_algorithm,
)


def test_jwt_algorithm_enum_values() -> None:
    """JWTAlgorithm enum must define RS256 and HS256."""
    assert JWTAlgorithm.RS256 == "RS256"
    assert JWTAlgorithm.HS256 == "HS256"


def test_allowed_algorithms_matrix() -> None:
    """Production must strictly only allow RS256; dev/staging allow RS256 and HS256."""
    assert ALLOWED_ALGORITHMS["production"] == {JWTAlgorithm.RS256}
    assert ALLOWED_ALGORITHMS["staging"] == {JWTAlgorithm.RS256, JWTAlgorithm.HS256}
    assert ALLOWED_ALGORITHMS["development"] == {JWTAlgorithm.RS256, JWTAlgorithm.HS256}


def test_validate_algorithm_production_rs256_allowed(monkeypatch: pytest.MonkeyPatch) -> None:
    """In production, RS256 must be allowed and returned."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    assert validate_algorithm("RS256") == JWTAlgorithm.RS256


def test_validate_algorithm_production_case_insensitive_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """ENVIRONMENT variable should be evaluated case-insensitively."""
    monkeypatch.setenv("ENVIRONMENT", "PRODUCTION")
    assert validate_algorithm("RS256") == JWTAlgorithm.RS256

    with pytest.raises(ValueError, match="JWT algorithm HS256 not allowed in production. Use RS256."):
        validate_algorithm("HS256")


def test_validate_algorithm_production_hs256_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    """In production, HS256 must be rejected with ValueError to prevent weak symmetric algos."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    with pytest.raises(ValueError, match="JWT algorithm HS256 not allowed in production. Use RS256."):
        validate_algorithm("HS256")


@pytest.mark.parametrize("env", ["development", "staging", "dev", "local"])
def test_validate_algorithm_non_production_both_allowed(monkeypatch: pytest.MonkeyPatch, env: str) -> None:
    """In non-production environments or unset/unknown env, both RS256 and HS256 are valid."""
    monkeypatch.setenv("ENVIRONMENT", env)
    assert validate_algorithm("RS256") == JWTAlgorithm.RS256
    assert validate_algorithm("HS256") == JWTAlgorithm.HS256


def test_validate_algorithm_default_env_without_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    """When ENVIRONMENT is unset, defaults to development."""
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    assert validate_algorithm("RS256") == JWTAlgorithm.RS256
    assert validate_algorithm("HS256") == JWTAlgorithm.HS256


@pytest.mark.parametrize("unsupported_algo", ["none", "None", "ES256", "ES384", "RS512", "INVALID", ""])
def test_validate_algorithm_unsupported_algorithms_rejected(monkeypatch: pytest.MonkeyPatch, unsupported_algo: str) -> None:
    """Unsupported or dangerous algorithms (e.g. 'none') must raise ValueError."""
    monkeypatch.setenv("ENVIRONMENT", "development")
    with pytest.raises(ValueError):
        validate_algorithm(unsupported_algo)
