"""JWT validation regression tests for shared identity decoding behavior."""

from __future__ import annotations

import json
import time
from unittest.mock import patch

import jwt
import pytest

from value_fabric.shared.identity.jwt import decode_jwt


TEST_SECRET = "jwt-validation-test-secret-32-bytes-min"
TEST_AUDIENCE = "value-fabric-services"
TEST_ISSUER = "value-fabric-internal"
TEST_TENANT_ID = "11111111-1111-1111-1111-111111111111"


def _sign(payload: dict, *, secret: str = TEST_SECRET, kid: str | None = None) -> str:
    headers = {"kid": kid} if kid else None
    return jwt.encode(payload, secret, algorithm="HS256", headers=headers)


@patch.dict(
    "os.environ",
    {
        "JWT_SECRET": TEST_SECRET,
        "JWT_ALGORITHM": "HS256",
        "JWT_ISSUER": TEST_ISSUER,
        "JWT_AUDIENCE": TEST_AUDIENCE,
    },
    clear=False,
)
def test_decode_rejects_wrong_issuer() -> None:
    token = _sign(
        {
            "tenant_id": TEST_TENANT_ID,
            "iss": "unexpected-issuer",
            "aud": TEST_AUDIENCE,
            "exp": int(time.time()) + 600,
        }
    )

    assert decode_jwt(token) is None


@patch.dict(
    "os.environ",
    {
        "JWT_SECRET": TEST_SECRET,
        "JWT_ALGORITHM": "HS256",
        "JWT_ISSUER": TEST_ISSUER,
        "JWT_AUDIENCE": TEST_AUDIENCE,
        "JWT_REVOKED_KIDS": "revoked-kid",
    },
    clear=False,
)
def test_decode_rejects_revoked_kid() -> None:
    token = _sign(
        {
            "tenant_id": TEST_TENANT_ID,
            "iss": TEST_ISSUER,
            "aud": TEST_AUDIENCE,
            "exp": int(time.time()) + 600,
        },
        kid="revoked-kid",
    )

    assert decode_jwt(token) is None


@patch.dict(
    "os.environ",
    {
        "JWT_SECRET": TEST_SECRET,
        "JWT_ALGORITHM": "HS256",
        "JWT_ISSUER": TEST_ISSUER,
        "JWT_AUDIENCE": TEST_AUDIENCE,
    },
    clear=False,
)
def test_decode_accepts_valid_internal_token() -> None:
    token = _sign(
        {
            "tenant_id": TEST_TENANT_ID,
            "sub": "user-1",
            "roles": ["analyst"],
            "iss": TEST_ISSUER,
            "aud": TEST_AUDIENCE,
            "exp": int(time.time()) + 600,
            "iat": int(time.time()),
        }
    )

    claims = decode_jwt(token)

    assert claims is not None
    assert claims.tenant_id == TEST_TENANT_ID
    assert claims.sub == "user-1"
    assert claims.roles == ["analyst"]


# ---------------------------------------------------------------------------
# Adversarial: OIDC-specific attack vectors
# ---------------------------------------------------------------------------

_OIDC_ENV = {
    "JWT_SECRET": TEST_SECRET,
    "JWT_ALGORITHM": "HS256",
    "JWT_ISSUER": TEST_ISSUER,
    "JWT_AUDIENCE": TEST_AUDIENCE,
}


@patch.dict("os.environ", _OIDC_ENV, clear=False)
def test_decode_rejects_wrong_audience() -> None:
    """Token with wrong audience is rejected."""
    token = _sign(
        {
            "tenant_id": TEST_TENANT_ID,
            "iss": TEST_ISSUER,
            "aud": "wrong-audience",
            "exp": int(time.time()) + 600,
            "iat": int(time.time()),
        }
    )
    assert decode_jwt(token) is None


@patch.dict("os.environ", _OIDC_ENV, clear=False)
def test_decode_expired_token_raises_401() -> None:
    """Expired token raises HTTPException 401, not returns None."""
    from fastapi import HTTPException
    token = _sign(
        {
            "tenant_id": TEST_TENANT_ID,
            "iss": TEST_ISSUER,
            "aud": TEST_AUDIENCE,
            "exp": int(time.time()) - 60,
            "iat": int(time.time()) - 120,
        }
    )
    with pytest.raises(HTTPException) as exc_info:
        decode_jwt(token)
    assert exc_info.value.status_code == 401


@patch.dict("os.environ", _OIDC_ENV, clear=False)
def test_decode_malformed_token_returns_none() -> None:
    """Truncated / garbage token returns None without raising."""
    assert decode_jwt("not.a.jwt") is None
    assert decode_jwt("eyJhbGciOiJIUzI1NiJ9.truncated") is None
    assert decode_jwt("") is None


@patch.dict("os.environ", _OIDC_ENV, clear=False)
def test_decode_token_signed_with_wrong_secret_returns_none() -> None:
    """Token signed with a different secret is rejected."""
    token = _sign(
        {
            "tenant_id": TEST_TENANT_ID,
            "iss": TEST_ISSUER,
            "aud": TEST_AUDIENCE,
            "exp": int(time.time()) + 600,
            "iat": int(time.time()),
        },
        secret="completely-different-secret-32ch!!",
    )
    assert decode_jwt(token) is None


@patch.dict("os.environ", _OIDC_ENV, clear=False)
def test_decode_missing_tenant_id_returns_none() -> None:
    """Token without tenant_id claim returns None (fail closed)."""
    token = _sign(
        {
            "sub": "user-1",
            "iss": TEST_ISSUER,
            "aud": TEST_AUDIENCE,
            "exp": int(time.time()) + 600,
            "iat": int(time.time()),
        }
    )
    assert decode_jwt(token) is None


def test_decode_hs256_rejected_when_oidc_issuer_configured() -> None:
    """HS256 token is rejected when OIDC_ISSUER is set and issuer matches (must use RS256/ES256)."""
    oidc_issuer = "https://idp.example.com"
    token = _sign(
        {
            "tenant_id": TEST_TENANT_ID,
            "iss": oidc_issuer,
            "aud": "fabric-api",
            "exp": int(time.time()) + 600,
            "iat": int(time.time()),
        }
    )
    with patch.dict("os.environ", {
        "JWT_SECRET": TEST_SECRET,
        "JWT_ALGORITHM": "HS256",
        "OIDC_ISSUER": oidc_issuer,
        "OIDC_AUDIENCE": "fabric-api",
    }, clear=False):
        assert decode_jwt(token) is None


@patch.dict("os.environ", _OIDC_ENV, clear=False)
def test_decode_revoked_kid_returns_none() -> None:
    """Token with a revoked kid is rejected before signature verification."""
    token = _sign(
        {
            "tenant_id": TEST_TENANT_ID,
            "iss": TEST_ISSUER,
            "aud": TEST_AUDIENCE,
            "exp": int(time.time()) + 600,
            "iat": int(time.time()),
        },
        kid="revoked-key-id",
    )
    with patch.dict("os.environ", {"JWT_REVOKED_KIDS": "revoked-key-id"}, clear=False):
        assert decode_jwt(token) is None


@patch.dict("os.environ", _OIDC_ENV, clear=False)
def test_decode_missing_required_registered_claims_returns_none() -> None:
    """Tokens missing exp, iss, or aud are rejected before signature verification."""
    now = int(time.time())

    # Missing exp
    token_no_exp = _sign({"tenant_id": TEST_TENANT_ID, "iss": TEST_ISSUER, "aud": TEST_AUDIENCE, "iat": now})
    assert decode_jwt(token_no_exp) is None

    # Missing iss
    token_no_iss = _sign({"tenant_id": TEST_TENANT_ID, "aud": TEST_AUDIENCE, "exp": now + 600, "iat": now})
    assert decode_jwt(token_no_iss) is None

    # Missing aud
    token_no_aud = _sign({"tenant_id": TEST_TENANT_ID, "iss": TEST_ISSUER, "exp": now + 600, "iat": now})
    assert decode_jwt(token_no_aud) is None
