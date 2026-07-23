"""Tests for JWT encode/decode helpers (shared/identity/jwt.py)."""

import json
import os
import time
from unittest.mock import patch
from uuid import uuid4

import jwt as pyjwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException

from ..jwt import TokenClaims, _get_jwt_secret, decode_jwt, encode_jwt


# Use a fixed secret across all tests to avoid env-var interference
_TEST_SECRET = "test-jwt-secret-for-unit-tests-32"
_TEST_TENANT = uuid4()
_TEST_ISSUER = "value-fabric-internal"
_TEST_AUDIENCE = "value-fabric-services"
_TEST_CLERK_ISSUER = "https://clerk.fabric4l.test"
_TEST_CLERK_AUDIENCE = "fabric4l-api"
_TEST_CLERK_ORIGIN = "http://localhost:3001"


def test_jwt_facade_exposes_extracted_token_implementations():
    """The legacy jwt module remains a stable import façade after the split."""
    from .. import jwt as jwt_facade
    from .. import jwt_tokens

    assert jwt_facade.decode_jwt is jwt_tokens.decode_jwt
    assert jwt_facade.encode_jwt is jwt_tokens.encode_jwt
    assert jwt_facade.decode_service_jwt is jwt_tokens.decode_service_jwt
    assert jwt_facade.encode_service_jwt is jwt_tokens.encode_service_jwt


@pytest.fixture(autouse=True)
def _jwt_env():
    """Set predictable JWT env vars for every test."""
    with patch.dict(
        os.environ,
        {
            "JWT_SECRET": _TEST_SECRET,
            "JWT_ALGORITHM": "HS256",
            "JWT_ISSUER": _TEST_ISSUER,
            "JWT_AUDIENCE": _TEST_AUDIENCE,
        },
    ):
        yield


# ---------------------------------------------------------------------------
# TokenClaims
# ---------------------------------------------------------------------------


class TestTokenClaims:
    """Tests for the TokenClaims model."""

    def test_roles_are_preserved(self):
        tc = TokenClaims(sub="user-1", tenant_id=str(_TEST_TENANT), roles=["analyst", "read_only"])
        assert tc.roles == ["analyst", "read_only"]

    def test_required_subject_is_enforced(self):
        with pytest.raises(Exception):
            TokenClaims(tenant_id=str(_TEST_TENANT), roles=["analyst"])


class TestJwtSecretValidation:
    """Tests for strict JWT_SECRET required behavior."""

    def test_missing_secret_raises_in_production(self):
        with patch.dict(os.environ, {"ENV": "production"}, clear=True):
            with pytest.raises(RuntimeError, match="JWT_SECRET is required"):
                _get_jwt_secret()

    def test_missing_secret_raises_in_local(self):
        with patch.dict(os.environ, {"ENV": "local"}, clear=True):
            with pytest.raises(RuntimeError, match="JWT_SECRET is required"):
                _get_jwt_secret()

    def test_missing_secret_raises_in_test(self):
        with patch.dict(os.environ, {"APP_ENV": "test"}, clear=True):
            with pytest.raises(RuntimeError, match="JWT_SECRET is required"):
                _get_jwt_secret()


# ---------------------------------------------------------------------------
# encode_jwt
# ---------------------------------------------------------------------------


class TestEncodeJwt:
    """Tests for encode_jwt()."""

    def test_basic_encode(self):
        """Produces a decodable JWT string."""
        token = encode_jwt(_TEST_TENANT)
        payload = pyjwt.decode(
            token,
            _TEST_SECRET,
            algorithms=["HS256"],
            audience=_TEST_AUDIENCE,
            issuer=_TEST_ISSUER,
        )
        assert payload["tenant_id"] == str(_TEST_TENANT)

    def test_includes_exp_claim(self):
        token = encode_jwt(_TEST_TENANT, expires_in_seconds=600)
        payload = pyjwt.decode(token, _TEST_SECRET, algorithms=["HS256"], audience=_TEST_AUDIENCE, issuer=_TEST_ISSUER)
        assert "exp" in payload
        assert "iat" in payload
        assert payload["exp"] - payload["iat"] == 600

    def test_includes_user_id(self):
        token = encode_jwt(_TEST_TENANT, user_id="user-42")
        payload = pyjwt.decode(token, _TEST_SECRET, algorithms=["HS256"], audience=_TEST_AUDIENCE, issuer=_TEST_ISSUER)
        assert payload["sub"] == "user-42"

    def test_includes_roles(self):
        token = encode_jwt(_TEST_TENANT, roles=["analyst", "content_admin"])
        payload = pyjwt.decode(token, _TEST_SECRET, algorithms=["HS256"], audience=_TEST_AUDIENCE, issuer=_TEST_ISSUER)
        assert payload["roles"] == ["analyst", "content_admin"]

    def test_includes_api_key_id(self):
        token = encode_jwt(_TEST_TENANT, api_key_id="key-99")
        payload = pyjwt.decode(token, _TEST_SECRET, algorithms=["HS256"], audience=_TEST_AUDIENCE, issuer=_TEST_ISSUER)
        assert payload["api_key_id"] == "key-99"

    def test_extra_claims_merged(self):
        token = encode_jwt(_TEST_TENANT, extra_claims={"custom": "value"})
        payload = pyjwt.decode(token, _TEST_SECRET, algorithms=["HS256"], audience=_TEST_AUDIENCE, issuer=_TEST_ISSUER)
        assert payload["custom"] == "value"


# ---------------------------------------------------------------------------
# decode_jwt
# ---------------------------------------------------------------------------


class TestDecodeJwt:
    """Tests for decode_jwt()."""

    def test_valid_token(self):
        """Round-trip: encode → decode produces matching claims."""
        token = encode_jwt(
            _TEST_TENANT,
            user_id="user-1",
            roles=["analyst"],
            api_key_id="key-1",
        )
        claims = decode_jwt(token)
        assert claims is not None
        assert claims.tenant_id == str(_TEST_TENANT)
        assert claims.sub == "user-1"
        assert claims.roles == ["analyst"]
        assert claims.jti is None

    def test_expired_token_raises_401(self):
        """An expired token raises HTTPException(401)."""
        token = encode_jwt(_TEST_TENANT, expires_in_seconds=-1)
        with pytest.raises(HTTPException) as exc_info:
            decode_jwt(token)
        assert exc_info.value.status_code == 401

    def test_invalid_signature_returns_none(self):
        """A token signed with the wrong secret returns None."""
        bad_token = pyjwt.encode(
            {"tenant_id": str(_TEST_TENANT), "iss": _TEST_ISSUER, "aud": _TEST_AUDIENCE, "exp": int(time.time()) + 3600},
            "wrong-secret",
            algorithm="HS256",
        )
        assert decode_jwt(bad_token) is None

    def test_missing_tenant_claim_returns_none(self):
        """A token without the tenant_id claim returns None."""
        token = pyjwt.encode(
            {"iss": _TEST_ISSUER, "aud": _TEST_AUDIENCE, "exp": int(time.time()) + 3600},
            _TEST_SECRET,
            algorithm="HS256",
        )
        assert decode_jwt(token) is None

    def test_invalid_tenant_uuid_returns_none(self):
        """A token with a non-UUID tenant_id returns None."""
        token = pyjwt.encode(
            {"tenant_id": "not-a-uuid", "iss": _TEST_ISSUER, "aud": _TEST_AUDIENCE, "exp": int(time.time()) + 3600},
            _TEST_SECRET,
            algorithm="HS256",
        )
        assert decode_jwt(token) is None

    def test_roles_as_string_converted_to_list(self):
        """A single role string is wrapped into a list."""
        token = pyjwt.encode(
            {
                "tenant_id": str(_TEST_TENANT),
                "roles": "analyst",
                "iss": _TEST_ISSUER,
                "aud": _TEST_AUDIENCE,
                "exp": int(time.time()) + 3600,
            },
            _TEST_SECRET,
            algorithm="HS256",
        )
        claims = decode_jwt(token)
        assert claims is not None
        assert claims.roles == ["analyst"]

    def test_malformed_token_returns_none(self):
        """Garbage input returns None."""
        assert decode_jwt("not.a.jwt") is None
        assert decode_jwt("") is None

    @pytest.mark.parametrize(
        "env_overrides",
        [
            {"ENVIRONMENT": "staging", "ALLOW_LEGACY_TEST_TENANT_IDS": "true", "PYTEST_CURRENT_TEST": "x"},
            {"ENVIRONMENT": "production", "TESTING": "true", "PYTEST_CURRENT_TEST": "x"},
            {"ENVIRONMENT": "development", "ALLOW_LEGACY_TEST_TENANT_IDS": "true", "KUBERNETES_SERVICE_HOST": "10.0.0.1", "PYTEST_CURRENT_TEST": "x"},
        ],
    )
    def test_non_uuid_tenant_rejected_in_prod_like_matrices(self, env_overrides):
        token = pyjwt.encode(
            {"tenant_id": "tenant-a", "iss": _TEST_ISSUER, "aud": _TEST_AUDIENCE, "exp": int(time.time()) + 3600},
            _TEST_SECRET,
            algorithm="HS256",
        )
        with patch.dict(os.environ, env_overrides, clear=False):
            assert decode_jwt(token) is None

    def test_clerk_token_accepts_configured_authorized_party(self):
        token, env = _make_clerk_rs256_token(azp=_TEST_CLERK_ORIGIN)
        with patch.dict(os.environ, env, clear=False):
            claims = decode_jwt(token)

        assert claims is not None
        assert claims.tenant_id == str(_TEST_TENANT)
        assert claims.extra_claims["azp"] == _TEST_CLERK_ORIGIN

    def test_clerk_token_rejects_unconfigured_authorized_party(self):
        token, env = _make_clerk_rs256_token(azp="https://attacker.example")
        with patch.dict(os.environ, env, clear=False):
            assert decode_jwt(token) is None

    def test_clerk_token_rejects_missing_authorized_party_when_configured(self):
        token, env = _make_clerk_rs256_token(azp=None)
        with patch.dict(os.environ, env, clear=False):
            assert decode_jwt(token) is None

    def test_clerk_token_accepts_compat_issuer_alias(self):
        token, env = _make_clerk_rs256_token(azp=_TEST_CLERK_ORIGIN)
        env["CLERK_ISSUER"] = ""
        env["CLERK_JWT_ISSUER"] = _TEST_CLERK_ISSUER
        with patch.dict(os.environ, env, clear=False):
            claims = decode_jwt(token)

        assert claims is not None
        assert claims.tenant_id == str(_TEST_TENANT)


class TestJwtSecretPolicy:
    """Tests for fail-closed JWT secret policy."""

    def test_non_dev_raises_when_secret_unset(self):
        with patch.dict(
            os.environ,
            {"ENVIRONMENT": "production"},
            clear=True,
        ):
            with pytest.raises(RuntimeError, match="JWT_SECRET is required"):
                _get_jwt_secret()

    def test_token_operations_fail_without_explicit_secret(self):
        with patch.dict(os.environ, {"APP_ENV": "test"}, clear=True):
            with pytest.raises(RuntimeError, match="JWT_SECRET is required"):
                encode_jwt(_TEST_TENANT)


def _make_clerk_rs256_token(*, azp: str | None) -> tuple[str, dict[str, str]]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_jwk = json.loads(pyjwt.algorithms.RSAAlgorithm.to_jwk(private_key.public_key()))
    public_jwk.update({"kid": "clerk-test-key", "alg": "RS256", "use": "sig"})
    now = int(time.time())
    payload = {
        "sub": "user_clerk_123",
        "tenant_id": str(_TEST_TENANT),
        "org_id": "org_clerk_123",
        "roles": ["analyst"],
        "iss": _TEST_CLERK_ISSUER,
        "aud": _TEST_CLERK_AUDIENCE,
        "iat": now,
        "nbf": now,
        "exp": now + 3600,
    }
    if azp is not None:
        payload["azp"] = azp

    token = pyjwt.encode(
        payload,
        private_key,
        algorithm="RS256",
        headers={"kid": "clerk-test-key"},
    )
    env = {
        "CLERK_ISSUER": _TEST_CLERK_ISSUER,
        "CLERK_JWT_AUDIENCE": _TEST_CLERK_AUDIENCE,
        "CLERK_AUTHORIZED_PARTIES": _TEST_CLERK_ORIGIN,
        "OIDC_JWKS_JSON": json.dumps({"keys": [public_jwk]}),
        "OIDC_ISSUER": "",
        "OIDC_AUDIENCE": "",
        "OIDC_JWKS_URL": "",
        "CLERK_JWKS_URL": "",
    }
    return token, env
