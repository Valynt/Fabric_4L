"""Tests for dynamic JWKS URL fetching (Keycloak support)."""

from __future__ import annotations

import json
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from unittest.mock import patch

import jwt
import pytest
from value_fabric.shared.identity.jwt import (
    _JWKS_URL_CACHE,
    _JWKS_URL_CACHE_EXPIRY,
    _fetch_jwks_from_url,
    _resolve_external_key,
    decode_jwt,
)


class MockJWKSHandler(BaseHTTPRequestHandler):
    """Simple HTTP handler that returns a mock JWKS."""

    # Generate a single fixed RSA key pair for the lifetime of the server
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    _private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    _public_key = _private_key.public_key()

    @classmethod
    def get_jwks(cls):
        from jwt.algorithms import RSAAlgorithm
        jwk = RSAAlgorithm.to_jwk(cls._public_key)
        jwk_obj = json.loads(jwk)
        jwk_obj["kid"] = "test-key-1"
        jwk_obj["alg"] = "RS256"
        jwk_obj["use"] = "sig"
        return {"keys": [jwk_obj]}

    def do_GET(self):
        if self.path == "/jwks":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(self.get_jwks()).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # Suppress logs


@pytest.fixture(scope="module")
def mock_jwks_server():
    server = HTTPServer(("127.0.0.1", 0), MockJWKSHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]
    yield f"http://127.0.0.1:{port}"
    server.shutdown()


def test_fetch_jwks_from_url_success(mock_jwks_server):
    url = f"{mock_jwks_server}/jwks"
    jwks = _fetch_jwks_from_url(url)
    assert jwks is not None
    assert "keys" in jwks
    assert len(jwks["keys"]) == 1
    assert jwks["keys"][0]["kid"] == "test-key-1"


def test_fetch_jwks_from_url_caching(mock_jwks_server):
    url = f"{mock_jwks_server}/jwks"
    # First fetch populates cache
    jwks1 = _fetch_jwks_from_url(url)
    # Second fetch should hit cache
    jwks2 = _fetch_jwks_from_url(url)
    assert jwks1 == jwks2


def test_fetch_jwks_from_url_404():
    jwks = _fetch_jwks_from_url("http://127.0.0.1:1/jwks")
    assert jwks is None


def test_resolve_external_key_with_jwks_url(mock_jwks_server):
    url = f"{mock_jwks_server}/jwks"
    with patch.dict("os.environ", {"OIDC_JWKS_URL": url}):
        header = {"kid": "test-key-1", "alg": "RS256"}
        key = _resolve_external_key(header, "https://example.com")
        assert key is not None


def test_resolve_external_key_missing_kid(mock_jwks_server):
    url = f"{mock_jwks_server}/jwks"
    with patch.dict("os.environ", {"OIDC_JWKS_URL": url}):
        header = {"alg": "RS256"}
        key = _resolve_external_key(header, "https://example.com")
        assert key is None


def test_resolve_external_key_revoked_kid(mock_jwks_server):
    url = f"{mock_jwks_server}/jwks"
    with patch.dict("os.environ", {"OIDC_JWKS_URL": url, "JWT_REVOKED_KIDS": "test-key-1"}):
        header = {"kid": "test-key-1", "alg": "RS256"}
        key = _resolve_external_key(header, "https://example.com")
        assert key is None


def test_decode_jwt_with_external_jwks_url(mock_jwks_server):
    from value_fabric.shared.identity import jwt as jwt_module

    # Clear any cached JWKS to ensure fresh fetch
    jwt_module._JWKS_URL_CACHE.clear()
    jwt_module._JWKS_URL_CACHE_EXPIRY.clear()

    url = f"{mock_jwks_server}/jwks"
    # Generate a test token signed with the mock server's private key
    from cryptography.hazmat.primitives import serialization

    private_key = MockJWKSHandler._private_key
    pem_private = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    now = int(time.time())
    payload = {
        "sub": "test-user",
        "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
        "roles": ["analyst"],
        "iss": "https://example.com",
        "aud": "fabric-api",
        "iat": now,
        "exp": now + 3600,
    }
    token = jwt.encode(payload, pem_private, algorithm="RS256", headers={"kid": "test-key-1"})

    with patch.dict(
        "os.environ",
        {
            "OIDC_JWKS_URL": url,
            "OIDC_ISSUER": "https://example.com",
            "OIDC_AUDIENCE": "fabric-api",
            "JWT_ALGORITHM": "RS256",
            "JWT_PUBLIC_KEY_PEM": "dummy",
            "JWT_PRIVATE_KEY_PEM": "dummy",
        },
    ):
        claims = decode_jwt(token)
        assert claims is not None
        assert claims.sub == "test-user"
        assert claims.tenant_id == "550e8400-e29b-41d4-a716-446655440000"
        assert "analyst" in claims.roles


# ---------------------------------------------------------------------------
# kid-miss cache-busting re-fetch (new behaviour after hardening)
# ---------------------------------------------------------------------------

class RotatingKeyJWKSHandler(BaseHTTPRequestHandler):
    """JWKS server that starts with key-A and can be switched to key-B."""

    from cryptography.hazmat.primitives.asymmetric import rsa as _rsa

    _key_a = _rsa.generate_private_key(public_exponent=65537, key_size=2048)
    _key_b = _rsa.generate_private_key(public_exponent=65537, key_size=2048)
    _serve_key_b: bool = False  # class-level toggle

    @classmethod
    def _make_jwk(cls, private_key, kid: str) -> dict:
        from jwt.algorithms import RSAAlgorithm
        jwk = json.loads(RSAAlgorithm.to_jwk(private_key.public_key()))
        jwk["kid"] = kid
        jwk["alg"] = "RS256"
        jwk["use"] = "sig"
        return jwk

    @classmethod
    def get_jwks(cls) -> dict:
        if cls._serve_key_b:
            return {"keys": [cls._make_jwk(cls._key_b, "key-b")]}
        return {"keys": [cls._make_jwk(cls._key_a, "key-a")]}

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(self.get_jwks()).encode())

    def log_message(self, format, *args):
        pass


@pytest.fixture(scope="module")
def rotating_jwks_server():
    server = HTTPServer(("127.0.0.1", 0), RotatingKeyJWKSHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]
    yield f"http://127.0.0.1:{port}"
    server.shutdown()


def test_resolve_external_key_cache_busts_on_kid_miss(rotating_jwks_server):
    """kid not in cached JWKS triggers a single re-fetch; new key is found."""
    from cryptography.hazmat.primitives import serialization

    url = f"{rotating_jwks_server}/"

    # Seed the cache with key-A
    _JWKS_URL_CACHE.pop(url, None)
    _JWKS_URL_CACHE_EXPIRY.pop(url, None)
    RotatingKeyJWKSHandler._serve_key_b = False
    _fetch_jwks_from_url(url)  # populates cache with key-A

    # Rotate the IdP to key-B
    RotatingKeyJWKSHandler._serve_key_b = True

    # Build a token signed with key-B
    pem_b = RotatingKeyJWKSHandler._key_b.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    now = int(time.time())
    token = jwt.encode(
        {"sub": "u", "iss": "https://idp.example.com", "aud": "api", "exp": now + 600,
         "iat": now, "tenant_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"},
        pem_b,
        algorithm="RS256",
        headers={"kid": "key-b"},
    )

    header = jwt.get_unverified_header(token)
    with patch.dict("os.environ", {"OIDC_JWKS_URL": url, "JWT_REVOKED_KIDS": ""}):
        key = _resolve_external_key(header, "https://idp.example.com")

    assert key is not None, "Expected key-B to be found after cache-busting re-fetch"

    # Cleanup
    RotatingKeyJWKSHandler._serve_key_b = False
    _JWKS_URL_CACHE.pop(url, None)
    _JWKS_URL_CACHE_EXPIRY.pop(url, None)


def test_resolve_external_key_returns_none_after_refetch_if_still_missing(mock_jwks_server):
    """If kid is absent even after re-fetch, return None (fail closed)."""
    url = f"{mock_jwks_server}/jwks"
    _JWKS_URL_CACHE.pop(url, None)
    _JWKS_URL_CACHE_EXPIRY.pop(url, None)

    header = {"kid": "nonexistent-kid", "alg": "RS256"}
    with patch.dict("os.environ", {"OIDC_JWKS_URL": url, "JWT_REVOKED_KIDS": ""}):
        key = _resolve_external_key(header, "https://example.com")

    assert key is None


def test_resolve_external_key_static_jwks_json_no_refetch():
    """Static OIDC_JWKS_JSON: kid miss returns None without any network call."""
    static_jwks = json.dumps({"keys": [{"kid": "only-key", "kty": "RSA",
                                         "n": "abc", "e": "AQAB", "alg": "RS256"}]})
    header = {"kid": "different-kid", "alg": "RS256"}
    with patch.dict("os.environ", {"OIDC_JWKS_JSON": static_jwks,
                                    "OIDC_JWKS_URL": "", "KEYCLOAK_URL": ""}):
        key = _resolve_external_key(header, "https://example.com")
    assert key is None


def test_resolve_external_key_keycloak_auto_url(mock_jwks_server):
    """KEYCLOAK_URL + KEYCLOAK_REALM auto-builds the JWKS URL when OIDC_JWKS_URL is unset."""
    # The mock server serves /jwks; we fake the Keycloak path to point there
    # by patching _build_keycloak_jwks_url to return the mock URL.
    url = f"{mock_jwks_server}/jwks"
    _JWKS_URL_CACHE.pop(url, None)
    _JWKS_URL_CACHE_EXPIRY.pop(url, None)

    header = {"kid": "test-key-1", "alg": "RS256"}
    with patch("value_fabric.shared.identity.jwt_external._build_keycloak_jwks_url", return_value=url):
        with patch.dict("os.environ", {"OIDC_JWKS_URL": "", "OIDC_JWKS_JSON": ""}):
            key = _resolve_external_key(header, "https://keycloak.example.com")

    assert key is not None


# ---------------------------------------------------------------------------
# decode_jwt: missing / invalid required claims
# ---------------------------------------------------------------------------

def test_decode_jwt_missing_exp_returns_none():
    """Token without exp claim is rejected before signature verification."""
    import os
    secret = "test-secret-for-missing-exp-32chars!!"
    now = int(time.time())
    token = jwt.encode(
        {"sub": "u", "tenant_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
         "iss": "value-fabric-internal", "aud": "value-fabric-services", "iat": now},
        secret, algorithm="HS256",
    )
    with patch.dict("os.environ", {"JWT_SECRET": secret, "JWT_ALGORITHM": "HS256",
                                    "JWT_ISSUER": "value-fabric-internal",
                                    "JWT_AUDIENCE": "value-fabric-services"}):
        result = decode_jwt(token)
    assert result is None


def test_decode_jwt_missing_tenant_id_returns_none():
    """Token without tenant_id claim returns None (fail closed)."""
    secret = "test-secret-no-tenant-id-32chars!!"
    now = int(time.time())
    token = jwt.encode(
        {"sub": "u", "iss": "value-fabric-internal", "aud": "value-fabric-services",
         "iat": now, "exp": now + 600},
        secret, algorithm="HS256",
    )
    with patch.dict("os.environ", {"JWT_SECRET": secret, "JWT_ALGORITHM": "HS256",
                                    "JWT_ISSUER": "value-fabric-internal",
                                    "JWT_AUDIENCE": "value-fabric-services"}):
        result = decode_jwt(token)
    assert result is None


def test_decode_jwt_invalid_uuid_tenant_id_returns_none():
    """Non-UUID tenant_id in a non-test environment returns None."""
    secret = "test-secret-bad-tenant-uuid-32chars!!"
    now = int(time.time())
    token = jwt.encode(
        {"sub": "u", "tenant_id": "not-a-uuid",
         "iss": "value-fabric-internal", "aud": "value-fabric-services",
         "iat": now, "exp": now + 600},
        secret, algorithm="HS256",
    )
    with patch.dict("os.environ", {"JWT_SECRET": secret, "JWT_ALGORITHM": "HS256",
                                    "JWT_ISSUER": "value-fabric-internal",
                                    "JWT_AUDIENCE": "value-fabric-services",
                                    "ALLOW_LEGACY_TEST_TENANT_IDS": "false",
                                    "TESTING": "false"}):
        result = decode_jwt(token)
    assert result is None


def test_decode_jwt_hs256_rejected_for_oidc_issuer():
    """HS256 token is rejected when OIDC_ISSUER is configured (external tokens must use RS256/ES256)."""
    secret = "test-secret-hs256-oidc-rejection-!!"
    now = int(time.time())
    token = jwt.encode(
        {"sub": "u", "tenant_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
         "iss": "https://idp.example.com", "aud": "fabric-api",
         "iat": now, "exp": now + 600},
        secret, algorithm="HS256",
    )
    with patch.dict("os.environ", {"JWT_SECRET": secret, "JWT_ALGORITHM": "HS256",
                                    "OIDC_ISSUER": "https://idp.example.com",
                                    "OIDC_AUDIENCE": "fabric-api"}):
        result = decode_jwt(token)
    assert result is None
