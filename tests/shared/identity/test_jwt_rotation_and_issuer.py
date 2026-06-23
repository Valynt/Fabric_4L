from __future__ import annotations

import json
import os
import time
from uuid import uuid4

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException

from value_fabric.shared.identity.jwt import decode_jwt, encode_jwt


@pytest.fixture(autouse=True)
def _env():
    old = dict(os.environ)
    os.environ.update(
        {
            "JWT_SECRET": "active-secret-key-must-be-at-least-32-bytes!!",
            "JWT_ALGORITHM": "HS256",
            "JWT_ACTIVE_KID": "active-k1",
            "JWT_PREVIOUS_KID": "prev-k0",
            "JWT_PREVIOUS_SECRET": "previous-secret-key-must-be-at-least-32-bytes!!",
            "JWT_ISSUER": "value-fabric-internal",
            "JWT_AUDIENCE": "value-fabric-services",
        }
    )
    yield
    os.environ.clear()
    os.environ.update(old)


def test_invalid_issuer_returns_none():
    token = encode_jwt(uuid4(), extra_claims={"iss": "evil-issuer"})
    assert decode_jwt(token) is None


def test_wrong_audience_returns_none():
    token = encode_jwt(uuid4(), extra_claims={"aud": "wrong-aud"})
    assert decode_jwt(token) is None


def test_expired_token_raises_401():
    token = encode_jwt(uuid4(), expires_in_seconds=-5)
    with pytest.raises(HTTPException) as exc:
        decode_jwt(token)
    assert exc.value.status_code == 401


def test_revoked_kid_is_rejected():
    os.environ["JWT_REVOKED_KIDS"] = "active-k1"
    token = encode_jwt(uuid4())
    assert decode_jwt(token) is None


def test_rotated_previous_key_is_accepted():
    payload = {
        "tenant_id": str(uuid4()),
        "iss": "value-fabric-internal",
        "aud": "value-fabric-services",
        "exp": int(time.time()) + 3600,
        "iat": int(time.time()),
    }
    token = jwt.encode(payload, "previous-secret-key-must-be-at-least-32-bytes!!", algorithm="HS256", headers={"kid": "prev-k0"})
    claims = decode_jwt(token)
    assert claims is not None


def test_external_oidc_jwks_verification():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_key = key.public_key()
    jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(public_key))
    jwk["kid"] = "oidc-k1"
    jwk["alg"] = "RS256"
    jwk["use"] = "sig"

    os.environ["OIDC_ISSUER"] = "https://issuer.example.com"
    os.environ["OIDC_AUDIENCE"] = "api://fabric"
    os.environ["OIDC_JWKS_JSON"] = json.dumps({"keys": [jwk]})

    payload = {
        "tenant_id": str(uuid4()),
        "iss": "https://issuer.example.com",
        "aud": "api://fabric",
        "exp": int(time.time()) + 3600,
        "iat": int(time.time()),
        "sub": "user-1",
    }
    token = jwt.encode(payload, private_pem, algorithm="RS256", headers={"kid": "oidc-k1"})
    claims = decode_jwt(token)
    assert claims is not None
    assert claims.sub == "user-1"
