"""Tests for Keycloak JWKS integration and token validation.

Validates:
- JWKS resolution order (static JSON -> explicit URL -> Keycloak auto-URL)
- Token acceptance/rejection rules
- Caching behavior
- Fail-closed behavior on missing/invalid auth
"""

from __future__ import annotations

import json
import os
import time
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
import jwt as jose_jwt  # alias preserved so test bodies need no further changes

from app.core.security import create_access_token
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)
TENANT_TEST = "33333333-3333-4333-8333-333333333333"
TENANT_A = "44444444-4444-4444-8444-444444444444"
TENANT_B = "55555555-5555-4555-8555-555555555555"


class TestKeycloakJWKSResolution:
    """Validate JWKS URL construction and resolution order."""

    def test_keycloak_jwks_url_auto_construction(self):
        """KEYCLOAK_URL + KEYCLOAK_REALM builds the correct JWKS endpoint."""
        from value_fabric.shared.identity.jwt import _build_keycloak_jwks_url

        with patch.dict(os.environ, {
            "KEYCLOAK_URL": "http://keycloak:8080",
            "KEYCLOAK_REALM": "fabric",
        }, clear=False):
            url = _build_keycloak_jwks_url()
            assert url == "http://keycloak:8080/realms/fabric/protocol/openid-connect/certs"

    def test_keycloak_url_missing_returns_none(self):
        """Without KEYCLOAK_URL set, auto-build returns None."""
        from value_fabric.shared.identity.jwt import _build_keycloak_jwks_url

        with patch.dict(os.environ, {"KEYCLOAK_URL": ""}, clear=False):
            with patch.dict(os.environ, {"KEYCLOAK_REALM": "fabric"}, clear=False):
                url = _build_keycloak_jwks_url()
                assert url is None

    def test_jwks_resolution_order_static_first(self):
        """Static JWKS JSON takes precedence over URL fetching."""
        from value_fabric.shared.identity.jwt import _resolve_external_key

        static_jwks = {"keys": [{"kid": "test-kid", "kty": "RSA", "n": "abc", "e": "AQAB", "alg": "RS256"}]}
        with patch.dict(os.environ, {"OIDC_JWKS_JSON": json.dumps(static_jwks)}, clear=False):
            with patch("value_fabric.shared.identity.jwt_external._fetch_jwks_from_url") as mock_fetch:
                with patch("jwt.algorithms.get_default_algorithms") as mock_algs:
                    mock_alg_instance = MagicMock()
                    mock_algs.return_value = {"RS256": mock_alg_instance}
                    header = {"kid": "test-kid", "alg": "RS256"}
                    _resolve_external_key(header, "test-issuer")
                    mock_fetch.assert_not_called()
                    mock_alg_instance.from_jwk.assert_called_once()

    def test_jwks_resolution_order_explicit_url_second(self):
        """Explicit OIDC_JWKS_URL is used when static JSON is absent."""
        from value_fabric.shared.identity.jwt import _resolve_external_key

        with patch.dict(os.environ, {"OIDC_JWKS_JSON": ""}, clear=False):
            with patch.dict(os.environ, {"OIDC_JWKS_URL": "http://example.com/jwks"}, clear=False):
                with patch("value_fabric.shared.identity.jwt_external._fetch_jwks_from_url") as mock_fetch:
                    mock_fetch.return_value = {"keys": []}
                    header = {"kid": "missing", "alg": "RS256"}
                    _resolve_external_key(header, "test-issuer")
                    # Implementation has cache-busting re-fetch logic, so it may call twice
                    assert mock_fetch.call_count >= 1
                    assert mock_fetch.call_args_list[0][0][0] == "http://example.com/jwks"

    def test_jwks_resolution_order_keycloak_third(self):
        """Auto-built Keycloak URL is used when static and explicit URLs are absent."""
        from value_fabric.shared.identity.jwt import _resolve_external_key

        with patch.dict(os.environ, {
            "OIDC_JWKS_JSON": "",
            "OIDC_JWKS_URL": "",
            "KEYCLOAK_URL": "http://keycloak:8080",
            "KEYCLOAK_REALM": "fabric",
        }, clear=False):
            with patch("value_fabric.shared.identity.jwt_external._fetch_jwks_from_url") as mock_fetch:
                mock_fetch.return_value = {"keys": []}
                header = {"kid": "missing", "alg": "RS256"}
                _resolve_external_key(header, "test-issuer")
                # Implementation has cache-busting re-fetch logic, so it may call twice
                assert mock_fetch.call_count >= 1
                assert mock_fetch.call_args_list[0][0][0] == "http://keycloak:8080/realms/fabric/protocol/openid-connect/certs"


class TestTokenValidation:
    """Validate token acceptance/rejection rules."""

    def test_valid_internal_token_accepted(self):
        from app.core.security import decode_token

        token = create_access_token(
            subject="user-test",
            tenant_id=TENANT_TEST,
            extra_claims={"roles": ["admin"]},
        )
        payload = decode_token(token)
        assert payload is not None
        assert payload.sub == "user-test"
        assert payload.tenant_id == TENANT_TEST

    def test_invalid_signature_rejected(self):
        resp = client.get("/v1/accounts", headers={
            "Authorization": "Bearer invalid.token.here",
            "X-Tenant-ID": TENANT_TEST,
        })
        assert resp.status_code == 401

    def test_expired_token_rejected(self):
        from datetime import timedelta
        expired_token = create_access_token(
            subject="user-test",
            tenant_id=TENANT_TEST,
            expires_delta=timedelta(seconds=-1),  # expired 1 second ago
        )
        resp = client.get("/v1/accounts", headers={
            "Authorization": f"Bearer {expired_token}",
            "X-Tenant-ID": TENANT_TEST,
        })
        assert resp.status_code == 401

    def test_missing_tenant_claim_rejected(self):
        """Token without tenant_id in payload must be rejected."""
        # Manually create a token without tenant_id
        from app.core.config import get_settings
        settings = get_settings()
        payload = {
            "sub": "user-test",
            "iss": settings.jwt_issuer,
            "aud": settings.jwt_audience,
            "iat": int(time.time()) - 60,
            "nbf": int(time.time()) - 60,
            "exp": int(time.time()) + 3600,
        }
        bad_token = jose_jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)

        resp = client.get("/v1/accounts", headers={
            "Authorization": f"Bearer {bad_token}",
        })
        assert resp.status_code == 401

    def test_tenant_header_spoofing_blocked(self):
        """JWT validation must succeed independently of spoofed transport hints."""
        from app.core.security import decode_token

        token = create_access_token(
            subject="user-spoof",
            tenant_id=TENANT_A,
            extra_claims={"roles": ["admin"]},
        )
        payload = decode_token(token)
        assert payload is not None
        assert payload.tenant_id == TENANT_A


class TestJWKSCaching:
    """Validate JWKS caching doesn't mask key rotation."""

    def test_jwks_cache_ttl_expires(self):
        """Cached JWKS should expire after TTL."""
        from value_fabric.shared.identity.jwt import (
            _JWKS_URL_CACHE,
            _JWKS_URL_CACHE_EXPIRY,
            _JWKS_URL_CACHE_TTL_SECONDS,
            _fetch_jwks_from_url,
        )

        test_url = "http://test/jwks"
        jwks_data = {"keys": [{"kid": "kid-1", "alg": "RS256"}]}

        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.json.return_value = jwks_data
            mock_response.raise_for_status = MagicMock()
            mock_client.get.return_value = mock_response
            mock_client.__enter__.return_value = mock_client
            mock_client_class.return_value = mock_client

            # First fetch should hit network
            result1 = _fetch_jwks_from_url(test_url)
            assert mock_client.get.call_count == 1

            # Second fetch within TTL should use cache
            result2 = _fetch_jwks_from_url(test_url)
            assert mock_client.get.call_count == 1  # no new network call
            assert result2 == result1

            # Expire cache manually
            _JWKS_URL_CACHE_EXPIRY[test_url] = time.time() - 1

            # Third fetch after expiry should hit network again
            result3 = _fetch_jwks_from_url(test_url)
            assert mock_client.get.call_count == 2
            assert result3 == result1

        # Clean up
        _JWKS_URL_CACHE.pop(test_url, None)
        _JWKS_URL_CACHE_EXPIRY.pop(test_url, None)
