"""JWT Configuration Validation Tests — P0 Critical Gap Remediation

Validates that JWT configuration is properly validated at startup,
especially in production environments.

Production Invariant: Production deployments must have secure JWT configuration.

Author: Autonomous Test Assurance Agent
Date: 2026-04-29
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

pytestmark = [
    pytest.mark.security,
    pytest.mark.jwt_config,
]


class TestProductionJWTSecretValidation:
    """P0: Production requires strong JWT secrets."""

    def test_layer1_configs_do_not_default_jwt_secret_to_changeme(self):
        """P0: L1 canonical and compatibility configs must not ship weak JWT defaults."""
        repo_root = Path(__file__).parents[2]
        config_paths = [
            repo_root / "services/layer1-ingestion/src/layer1_ingestion/shared/config.py",
            repo_root / "services/layer1-ingestion/src/shared/config.py",
        ]

        for config_path in config_paths:
            source = config_path.read_text(encoding="utf-8")
            assert 'jwt_secret: str = Field(default="changeme"' not in source
            assert "jwt_secret: str = Field(" in source and "description=" in source

    def test_production_requires_jwt_secret(self):
        """P0: Production startup fails without JWT_SECRET."""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "JWT_SECRET": "",  # Empty
            "JWT_ISSUER": "test-issuer",
            "JWT_AUDIENCE": "test-audience",
        }, clear=False):
            # Import and test the validation function
            try:
                from value_fabric.shared.security.config import validate_jwt_config
                
                with pytest.raises(ValueError) as exc_info:
                    validate_jwt_config()
                
                assert "JWT_SECRET is required" in str(exc_info.value), (
                    "Production should require JWT_SECRET"
                )
            except ImportError as exc:
                raise AssertionError("Required shared.identity.dependencies import is unavailable") from exc

    def test_production_rejects_weak_jwt_secret(self):
        """P0: Production startup fails with weak JWT_SECRET (<32 chars)."""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "JWT_SECRET": "short",  # Too short (only 5 chars)
            "JWT_ISSUER": "test-issuer",
            "JWT_AUDIENCE": "test-audience",
        }, clear=False):
            try:
                from value_fabric.shared.security.config import validate_jwt_config
                
                with pytest.raises(ValueError) as exc_info:
                    validate_jwt_config()
                
                assert "at least 32 characters" in str(exc_info.value), (
                    "Production should reject weak JWT_SECRET"
                )
            except ImportError as exc:
                raise AssertionError("Required shared.identity.dependencies import is unavailable") from exc

    def test_production_rejects_31_char_secret(self):
        """P0: 31-character secret is rejected (need 32+)."""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "JWT_SECRET": "a" * 31,  # Exactly 31 chars - should fail
            "JWT_ISSUER": "test-issuer",
            "JWT_AUDIENCE": "test-audience",
        }, clear=False):
            try:
                from value_fabric.shared.security.config import validate_jwt_config
                
                with pytest.raises(ValueError) as exc_info:
                    validate_jwt_config()
                
                assert "at least 32 characters" in str(exc_info.value)
            except ImportError as exc:
                raise AssertionError("Required shared.identity.dependencies import is unavailable") from exc

    def test_production_accepts_32_char_secret(self):
        """POSITIVE: 32-character secret is accepted."""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "JWT_SECRET": "a" * 32,  # Exactly 32 chars - should pass
            "JWT_ISSUER": "test-issuer",
            "JWT_AUDIENCE": "test-audience",
        }, clear=False):
            try:
                from value_fabric.shared.security.config import validate_jwt_config
                
                # Should not raise
                validate_jwt_config()
            except ImportError as exc:
                raise AssertionError("Required shared.identity.dependencies import is unavailable") from exc


class TestProductionJWTIssuerValidation:
    """P0: Production requires JWT issuer."""

    def test_production_requires_jwt_issuer(self):
        """P0: Production startup fails without JWT_ISSUER."""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "JWT_SECRET": "a" * 32,
            "JWT_ISSUER": "",  # Empty
            "JWT_AUDIENCE": "test-audience",
        }, clear=False):
            try:
                from value_fabric.shared.security.config import validate_jwt_config
                
                with pytest.raises(ValueError) as exc_info:
                    validate_jwt_config()
                
                assert "JWT_ISSUER is required" in str(exc_info.value), (
                    "Production should require JWT_ISSUER"
                )
            except ImportError as exc:
                raise AssertionError("Required shared.identity.dependencies import is unavailable") from exc

    def test_production_rejects_missing_issuer(self):
        """P0: Production startup fails when JWT_ISSUER not set."""
        # Remove JWT_ISSUER from environment
        env_copy = os.environ.copy()
        env_copy.pop("JWT_ISSUER", None)
        env_copy["ENVIRONMENT"] = "production"
        env_copy["JWT_SECRET"] = "a" * 32
        env_copy["JWT_AUDIENCE"] = "test-audience"
        
        with patch.dict(os.environ, env_copy, clear=True):
            try:
                from value_fabric.shared.security.config import validate_jwt_config
                
                with pytest.raises(ValueError) as exc_info:
                    validate_jwt_config()
                
                assert "JWT_ISSUER is required" in str(exc_info.value)
            except ImportError as exc:
                raise AssertionError("Required shared.identity.dependencies import is unavailable") from exc


class TestProductionJWTAudienceValidation:
    """P0: Production requires JWT audience."""

    def test_production_requires_jwt_audience(self):
        """P0: Production startup fails without JWT_AUDIENCE."""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "JWT_SECRET": "a" * 32,
            "JWT_ISSUER": "test-issuer",
            "JWT_AUDIENCE": "",  # Empty
        }, clear=False):
            try:
                from value_fabric.shared.security.config import validate_jwt_config
                
                with pytest.raises(ValueError) as exc_info:
                    validate_jwt_config()
                
                assert "JWT_AUDIENCE is required" in str(exc_info.value), (
                    "Production should require JWT_AUDIENCE"
                )
            except ImportError as exc:
                raise AssertionError("Required shared.identity.dependencies import is unavailable") from exc


class TestDevelopmentEnvironment:
    """Development environment is more permissive."""

    def test_development_allows_missing_jwt_secret(self):
        """Development allows missing JWT_SECRET."""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "development",
            "JWT_SECRET": "",
        }, clear=False):
            try:
                from value_fabric.shared.security.config import validate_jwt_config
                
                # Should not raise in development
                validate_jwt_config()
            except ImportError as exc:
                raise AssertionError("Required shared.identity.dependencies import is unavailable") from exc

    def test_development_allows_weak_jwt_secret(self):
        """Development allows weak JWT_SECRET."""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "development",
            "JWT_SECRET": "weak",
        }, clear=False):
            try:
                from value_fabric.shared.security.config import validate_jwt_config
                
                # Should not raise in development
                validate_jwt_config()
            except ImportError as exc:
                raise AssertionError("Required shared.identity.dependencies import is unavailable") from exc


class TestStagingEnvironment:
    """Staging environment should match production validation."""

    def test_staging_requires_jwt_secret(self):
        """P0: Staging should validate like production."""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "staging",
            "JWT_SECRET": "",
            "JWT_ISSUER": "test-issuer",
            "JWT_AUDIENCE": "test-audience",
        }, clear=False):
            try:
                from value_fabric.shared.security.config import validate_jwt_config
                
                # Staging should enforce production-like validation
                with pytest.raises(ValueError) as exc_info:
                    validate_jwt_config()
                
                assert "JWT_SECRET is required" in str(exc_info.value)
            except ImportError as exc:
                raise AssertionError("Required shared.identity.dependencies import is unavailable") from exc


class TestEdgeCases:
    """Edge cases for JWT configuration."""

    def test_jwt_secret_with_special_characters_accepted(self):
        """Special characters in JWT secret are handled."""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "JWT_SECRET": "my$ecr3t!@#$%^&*()_+key-that-is-32chars",
            "JWT_ISSUER": "test-issuer",
            "JWT_AUDIENCE": "test-audience",
        }, clear=False):
            try:
                from value_fabric.shared.security.config import validate_jwt_config
                
                # Should not raise - special chars should be fine
                validate_jwt_config()
            except ImportError as exc:
                raise AssertionError("Required shared.identity.dependencies import is unavailable") from exc

    def test_very_long_jwt_secret_accepted(self):
        """Very long JWT secrets are accepted."""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "JWT_SECRET": "a" * 128,  # 128 chars
            "JWT_ISSUER": "test-issuer",
            "JWT_AUDIENCE": "test-audience",
        }, clear=False):
            try:
                from value_fabric.shared.security.config import validate_jwt_config
                
                # Should not raise
                validate_jwt_config()
            except ImportError as exc:
                raise AssertionError("Required shared.identity.dependencies import is unavailable") from exc

    def test_unicode_jwt_secret_handled(self):
        """Unicode characters in JWT secret are handled."""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "JWT_SECRET": "🔐secret-key-with-32-chars!!🔐🔐🔐🔐🔐",
            "JWT_ISSUER": "test-issuer",
            "JWT_AUDIENCE": "test-audience",
        }, clear=False):
            try:
                from value_fabric.shared.security.config import validate_jwt_config
                
                # Should not raise or crash
                validate_jwt_config()
            except ImportError as exc:
                raise AssertionError("Required shared.identity.dependencies import is unavailable") from exc


# ---------------------------------------------------------------------------
# P0 expansion: runtime decode_jwt attack vectors
# ---------------------------------------------------------------------------

import time as _time

import jwt as _jwt

_RUNTIME_SECRET = "runtime-test-secret-must-be-32chars!!"
_RUNTIME_ISSUER = "value-fabric-internal"
_RUNTIME_AUDIENCE = "value-fabric-services"
_RUNTIME_TENANT = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"

_RUNTIME_ENV = {
    "JWT_SECRET": _RUNTIME_SECRET,
    "JWT_ALGORITHM": "HS256",
    "JWT_ISSUER": _RUNTIME_ISSUER,
    "JWT_AUDIENCE": _RUNTIME_AUDIENCE,
}


def _make_token(payload: dict, *, secret: str = _RUNTIME_SECRET) -> str:
    return _jwt.encode(payload, secret, algorithm="HS256")


def _valid_claims(**overrides) -> dict:
    now = int(_time.time())
    base = {
        "sub": "user-1",
        "tenant_id": _RUNTIME_TENANT,
        "iss": _RUNTIME_ISSUER,
        "aud": _RUNTIME_AUDIENCE,
        "iat": now,
        "exp": now + 600,
    }
    base.update(overrides)
    return base


@pytest.mark.security
@pytest.mark.jwt_config
class TestRuntimeDecodeAttackVectors:
    """P0: decode_jwt must reject all known token-level attack vectors.

    These tests complement TestProductionJWTSecretValidation (startup config)
    by verifying the runtime decode path fails closed on adversarial inputs.
    """

    @patch.dict("os.environ", _RUNTIME_ENV, clear=False)
    def test_expired_token_raises_401(self):
        """Expired token raises HTTPException 401."""
        from fastapi import HTTPException
        from value_fabric.shared.identity.jwt import decode_jwt

        token = _make_token(_valid_claims(
            exp=int(_time.time()) - 60,
            iat=int(_time.time()) - 120,
        ))
        with pytest.raises(HTTPException) as exc_info:
            decode_jwt(token)
        assert exc_info.value.status_code == 401, (
            f"Expired token should raise 401, got {exc_info.value.status_code}."
        )

    @patch.dict("os.environ", _RUNTIME_ENV, clear=False)
    def test_wrong_audience_rejected(self):
        """Token with wrong audience is rejected (returns None)."""
        from value_fabric.shared.identity.jwt import decode_jwt

        token = _make_token(_valid_claims(aud="wrong-audience"))
        assert decode_jwt(token) is None, (
            "Token with wrong audience must be rejected. "
            "P0: Audience bypass allows cross-service token reuse."
        )

    @patch.dict("os.environ", _RUNTIME_ENV, clear=False)
    def test_wrong_issuer_rejected(self):
        """Token with wrong issuer is rejected (returns None)."""
        from value_fabric.shared.identity.jwt import decode_jwt

        token = _make_token(_valid_claims(iss="https://attacker.example.com"))
        assert decode_jwt(token) is None, (
            "Token with wrong issuer must be rejected. "
            "P0: Issuer bypass allows tokens from untrusted IdPs."
        )

    @patch.dict("os.environ", _RUNTIME_ENV, clear=False)
    def test_malformed_token_returns_none(self):
        """Truncated or garbage tokens return None without raising."""
        from value_fabric.shared.identity.jwt import decode_jwt

        assert decode_jwt("not.a.jwt") is None
        assert decode_jwt("eyJhbGciOiJIUzI1NiJ9.truncated") is None
        assert decode_jwt("") is None
        assert decode_jwt("....") is None

    @patch.dict("os.environ", _RUNTIME_ENV, clear=False)
    def test_wrong_secret_rejected(self):
        """Token signed with a different secret is rejected."""
        from value_fabric.shared.identity.jwt import decode_jwt

        token = _make_token(_valid_claims(), secret="completely-different-secret-32ch!!")
        assert decode_jwt(token) is None, (
            "Token signed with wrong secret must be rejected. "
            "P0: Signature bypass."
        )

    @patch.dict("os.environ", _RUNTIME_ENV, clear=False)
    def test_missing_tenant_id_rejected(self):
        """Token without tenant_id claim returns None (fail closed)."""
        from value_fabric.shared.identity.jwt import decode_jwt

        claims = _valid_claims()
        claims.pop("tenant_id")
        token = _make_token(claims)
        assert decode_jwt(token) is None, (
            "Token without tenant_id must be rejected. "
            "P0: Missing tenant_id would allow unscoped access."
        )

    @patch.dict("os.environ", _RUNTIME_ENV, clear=False)
    def test_missing_exp_rejected(self):
        """Token without exp claim is rejected."""
        from value_fabric.shared.identity.jwt import decode_jwt

        claims = _valid_claims()
        claims.pop("exp")
        token = _make_token(claims)
        assert decode_jwt(token) is None, (
            "Token without exp must be rejected. "
            "P0: Non-expiring tokens are a persistent credential risk."
        )

    @patch.dict("os.environ", _RUNTIME_ENV, clear=False)
    def test_none_algorithm_rejected(self):
        """Token with 'none' algorithm is rejected (algorithm confusion attack)."""
        import base64
        import json

        from value_fabric.shared.identity.jwt import decode_jwt

        header = base64.urlsafe_b64encode(
            json.dumps({"alg": "none", "typ": "JWT"}).encode()
        ).decode().rstrip("=")
        payload = base64.urlsafe_b64encode(
            json.dumps(_valid_claims()).encode()
        ).decode().rstrip("=")
        none_alg_token = f"{header}.{payload}."

        result = decode_jwt(none_alg_token)
        assert result is None, (
            "Token with 'none' algorithm must be rejected. "
            "P0: Algorithm confusion attack."
        )

    @patch.dict("os.environ", {**_RUNTIME_ENV, "JWT_REVOKED_KIDS": "revoked-kid-001"}, clear=False)
    def test_revoked_kid_rejected(self):
        """Token with a revoked kid is rejected before signature verification."""
        from value_fabric.shared.identity.jwt import decode_jwt

        token = _jwt.encode(
            _valid_claims(),
            _RUNTIME_SECRET,
            algorithm="HS256",
            headers={"kid": "revoked-kid-001"},
        )
        assert decode_jwt(token) is None, (
            "Token with revoked kid must be rejected. "
            "P0: Revoked key bypass."
        )
