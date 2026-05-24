"""Phase 1 unit tests for the Fabric4L internal AuthContext envelope.

Covers:
- AuthContext frozen-model shape and validators
- Round-trip Ed25519 sign/verify
- Tampered payload rejection
- Wrong-kid rejection
- Expired envelope rejection
- Issuer/audience mismatch rejection
- Schema match against contracts/auth/fabric-auth-envelope.schema.json
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from value_fabric.shared.identity.fabric_auth import (
    AuthContext,
    EnvelopeExpiredError,
    EnvelopeInvalidError,
    KeySet,
    SigningKey,
    VerificationKey,
    sign_envelope,
    verify_envelope,
)
from value_fabric.shared.identity.fabric_auth.signer import ALGORITHM


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _generate_keypair(kid: str) -> tuple[SigningKey, VerificationKey]:
    private = Ed25519PrivateKey.generate()
    private_pem = private.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    public_pem = (
        private.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode()
    )
    return SigningKey(kid=kid, private_pem=private_pem), VerificationKey(
        kid=kid, public_pem=public_pem
    )


def _make_auth(*, kid: str = "k1", ttl: int = 60, **overrides) -> AuthContext:
    now = int(time.time())
    base = {
        "clerk_user_id": "user_abc",
        "clerk_org_id": "org_xyz",
        "user_id": "u_internal_1",
        "tenant_id": "ten_internal_1",
        "roles": frozenset({"org:admin"}),
        "permissions": frozenset({"org:accounts:read", "org:accounts:write"}),
        "request_id": "req_1",
        "iat": now,
        "exp": now + ttl,
        "nbf": now,
        "kid": kid,
    }
    base.update(overrides)
    return AuthContext(**base)


# ---------------------------------------------------------------------------
# AuthContext model
# ---------------------------------------------------------------------------

def test_auth_context_is_frozen():
    auth = _make_auth()
    with pytest.raises(Exception):
        auth.tenant_id = "tampered"  # type: ignore[misc]


def test_auth_context_rejects_non_iterable_permissions():
    with pytest.raises(Exception):
        _make_auth(permissions=42)  # type: ignore[arg-type]


def test_auth_context_coerces_iterable_permissions_to_strings():
    auth = _make_auth(permissions=("org:accounts:read", "org:accounts:write"))
    assert "org:accounts:read" in auth.permissions
    assert isinstance(auth.permissions, frozenset)


def test_auth_context_exp_must_exceed_iat():
    now = int(time.time())
    with pytest.raises(Exception):
        AuthContext(
            clerk_user_id="u",
            user_id="u",
            tenant_id="t",
            request_id="r",
            iat=now,
            exp=now,
            kid="k1",
        )


# ---------------------------------------------------------------------------
# Sign / verify round trip
# ---------------------------------------------------------------------------

def test_sign_and_verify_round_trip():
    sk, vk = _generate_keypair("k1")
    auth = _make_auth(kid="k1")
    token = sign_envelope(auth, signing_key=sk)
    verified = verify_envelope(token, key_set=KeySet([vk]))
    assert verified.tenant_id == auth.tenant_id
    assert verified.user_id == auth.user_id
    assert verified.permissions == auth.permissions
    assert verified.kid == "k1"


def test_sign_rejects_kid_mismatch():
    sk, _ = _generate_keypair("k1")
    auth = _make_auth(kid="k2")
    with pytest.raises(ValueError):
        sign_envelope(auth, signing_key=sk)


def test_verify_rejects_unknown_kid():
    sk, _ = _generate_keypair("k1")
    _, other_vk = _generate_keypair("k2")
    auth = _make_auth(kid="k1")
    token = sign_envelope(auth, signing_key=sk)
    with pytest.raises(EnvelopeInvalidError):
        verify_envelope(token, key_set=KeySet([other_vk]))


def test_verify_rejects_tampered_payload():
    sk, vk = _generate_keypair("k1")
    auth = _make_auth(kid="k1")
    token = sign_envelope(auth, signing_key=sk)

    # Flip a byte in the payload segment.
    header, payload, signature = token.split(".")
    tampered_payload = payload[:-2] + ("AA" if payload[-2:] != "AA" else "BB")
    tampered = ".".join([header, tampered_payload, signature])

    with pytest.raises(EnvelopeInvalidError):
        verify_envelope(tampered, key_set=KeySet([vk]))


def test_verify_rejects_expired_envelope():
    sk, vk = _generate_keypair("k1")
    now = int(time.time())
    auth = AuthContext(
        clerk_user_id="u",
        user_id="u",
        tenant_id="t",
        request_id="r",
        iat=now - 120,
        exp=now - 60,
        nbf=now - 120,
        kid="k1",
    )
    token = sign_envelope(auth, signing_key=sk)
    with pytest.raises(EnvelopeExpiredError):
        verify_envelope(token, key_set=KeySet([vk]), leeway_seconds=0)


def test_verify_rejects_wrong_issuer():
    sk, vk = _generate_keypair("k1")
    auth = _make_auth(kid="k1", iss="evil-issuer")
    token = sign_envelope(auth, signing_key=sk)
    with pytest.raises(EnvelopeInvalidError):
        verify_envelope(token, key_set=KeySet([vk]))


def test_verify_rejects_wrong_audience():
    sk, vk = _generate_keypair("k1")
    auth = _make_auth(kid="k1", aud="some-other-aud")
    token = sign_envelope(auth, signing_key=sk)
    with pytest.raises(EnvelopeInvalidError):
        verify_envelope(token, key_set=KeySet([vk]))


def test_verify_rejects_alg_none():
    """Defense-in-depth: the verifier must never accept alg=none."""
    import jwt as pyjwt

    auth = _make_auth(kid="k1")
    forged = pyjwt.encode(
        auth.to_jwt_claims(),
        key="",
        algorithm="none",
        headers={"kid": "k1"},
    )
    _, vk = _generate_keypair("k1")
    with pytest.raises(EnvelopeInvalidError):
        verify_envelope(forged, key_set=KeySet([vk]))


# ---------------------------------------------------------------------------
# Contract schema parity
# ---------------------------------------------------------------------------

def test_envelope_claims_match_contract_schema():
    """The runtime claim shape must satisfy the published contract."""
    # parents: [0]=tests [1]=identity [2]=shared [3]=value_fabric [4]=src
    # [5]=shared [6]=packages [7]=<repo-root>
    schema_path = (
        Path(__file__).resolve().parents[7]
        / "contracts"
        / "auth"
        / "fabric-auth-envelope.schema.json"
    )
    if not schema_path.exists():
        pytest.skip(f"contract schema not found at {schema_path}")

    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    jsonschema = pytest.importorskip("jsonschema")
    auth = _make_auth(kid="k1")
    claims = auth.to_jwt_claims()
    jsonschema.validate(claims, schema)


def test_algorithm_is_eddsa():
    assert ALGORITHM == "EdDSA"
