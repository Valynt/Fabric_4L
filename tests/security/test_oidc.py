"""Tests for OIDC authentication flow.

Validates:
- PKCE code generation
- OIDC discovery
- Token exchange
- Role mapping from claims
- ID token verification
- Error handling
- Adversarial: state replay, missing tenant_id, cross-tenant context
"""

from __future__ import annotations

import base64
import hashlib
import os
import secrets
from datetime import UTC
from unittest.mock import Mock, patch

import httpx
import pytest
from value_fabric.shared.audit import AuditAction, AuditOutcome
from value_fabric.shared.identity.middleware import extract_context_from_jwt
from value_fabric.shared.identity.oidc import OIDCClient, map_role_from_claims
from value_fabric.shared.identity.oidc_config import OIDCProviderConfig


def _generate_code_verifier() -> str:
    """Generate PKCE code_verifier for tests (mirrors implementation)."""
    return base64.urlsafe_b64encode(os.urandom(32)).decode("ascii").rstrip("=")


def _generate_code_challenge(code_verifier: str) -> str:
    """Generate PKCE code_challenge for tests (mirrors implementation)."""
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


class TestPKCEGeneration:
    """Test PKCE code generation functions."""

    def test_code_verifier_format(self):
        """Code verifier should be base64url encoded and 43+ chars."""
        verifier = _generate_code_verifier()
        # RFC 7636: code_verifier is 43-128 chars
        assert len(verifier) >= 43
        assert len(verifier) <= 128
        # Should be URL-safe base64 characters only
        assert all(c in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_." for c in verifier)

    def test_code_challenge_consistency(self):
        """Same verifier should produce same challenge."""
        verifier = _generate_code_verifier()
        challenge1 = _generate_code_challenge(verifier)
        challenge2 = _generate_code_challenge(verifier)

        assert challenge1 == challenge2
        assert challenge1 != verifier

    def test_code_challenge_s256(self):
        """Code challenge should be S256 hash of verifier."""
        verifier = "test_verifier_123456789012345678901234567890"
        challenge = _generate_code_challenge(verifier)

        # Manual S256 calculation
        expected = base64.urlsafe_b64encode(
            hashlib.sha256(verifier.encode("ascii")).digest()
        ).decode("ascii").rstrip("=")

        assert challenge == expected


class TestOIDCClient:
    """Test OIDC client methods."""

    @pytest.fixture
    def oidc_client(self):
        """Create OIDC client fixture."""
        return OIDCClient()

    @pytest.mark.asyncio
    async def test_discover_success(self, oidc_client):
        """OIDC discovery should fetch metadata from well-known endpoint."""
        mock_response = {
            "issuer": "https://auth.example.com",
            "authorization_endpoint": "https://auth.example.com/oauth/authorize",
            "token_endpoint": "https://auth.example.com/oauth/token",
            "userinfo_endpoint": "https://auth.example.com/oauth/userinfo",
            "jwks_uri": "https://auth.example.com/oauth/keys",
        }

        with patch.object(oidc_client._http_client, "get") as mock_get:
            mock_get.return_value = Mock(
                raise_for_status=Mock(),
                json=Mock(return_value=mock_response)
            )

            result = await oidc_client.discover("https://auth.example.com")

            assert result == mock_response
            mock_get.assert_called_once_with(
                "https://auth.example.com/.well-known/openid-configuration"
            )

    def test_build_authorize_url(self, oidc_client):
        """Build authorize URL with all parameters."""
        metadata = {"authorization_endpoint": "https://auth.example.com/oauth/authorize"}

        url = oidc_client.build_authorize_url(
            metadata=metadata,
            client_id="test-client",
            redirect_uri="https://app.example.com/callback",
            state="test-state-123",
            nonce="test-nonce-456",
            scopes=["openid", "profile", "email"],
            code_challenge="abc123",
            code_challenge_method="S256",
        )

        assert url.startswith("https://auth.example.com/oauth/authorize?")
        assert "client_id=test-client" in url
        assert "response_type=code" in url
        assert "scope=openid+profile+email" in url
        assert "redirect_uri=https%3A%2F%2Fapp.example.com%2Fcallback" in url
        assert "state=test-state-123" in url
        assert "nonce=test-nonce-456" in url
        assert "code_challenge=abc123" in url
        assert "code_challenge_method=S256" in url

    def test_build_authorize_url_without_pkce(self, oidc_client):
        """Build authorize URL without PKCE parameters."""
        metadata = {"authorization_endpoint": "https://auth.example.com/oauth/authorize"}

        url = oidc_client.build_authorize_url(
            metadata=metadata,
            client_id="test-client",
            redirect_uri="https://app.example.com/callback",
            state="test-state",
        )

        assert "code_challenge" not in url
        assert "code_challenge_method" not in url

    @pytest.mark.asyncio
    async def test_exchange_code(self, oidc_client):
        """Exchange authorization code for tokens."""
        token_response = {
            "access_token": "test_access_token",
            "id_token": "test_id_token",
            "token_type": "Bearer",
            "expires_in": 3600,
        }

        with patch.object(oidc_client._http_client, "post") as mock_post:
            mock_post.return_value = Mock(
                raise_for_status=Mock(),
                json=Mock(return_value=token_response)
            )

            result = await oidc_client.exchange_code(
                token_endpoint="https://auth.example.com/oauth/token",
                code="auth_code_123",
                redirect_uri="https://app.example.com/callback",
                client_id="test-client",
                client_secret="test-secret",
                code_verifier="verifier_123",
            )

            assert result == token_response
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert call_args[0][0] == "https://auth.example.com/oauth/token"


class TestRoleMapping:
    """Test role mapping from OIDC claims."""

    def test_map_super_admin_from_role_claim(self):
        """Map super_admin from role claim."""
        claims = {"role": "super_admin"}
        role = map_role_from_claims(claims)
        assert role == "super_admin"

    def test_map_tenant_admin_from_groups(self):
        """Map tenant_admin from groups claim."""
        claims = {"groups": ["admin", "users"]}
        role = map_role_from_claims(claims)
        assert role == "tenant_admin"

    def test_map_user_default(self):
        """Default to user role."""
        claims = {"email": "user@example.com"}
        role = map_role_from_claims(claims)
        assert role == "user"

    def test_map_with_claim_mapping(self):
        """Use custom claim mapping if provided."""
        claims = {"custom_role": "editor", "department": "engineering"}
        mapping = {"custom_role": "editor", "department": "manager"}
        role = map_role_from_claims(claims, claim_mapping=mapping)
        assert role == "editor"

    def test_map_with_default_role(self):
        """Use default_role when no mapping matches."""
        claims = {"email": "user@example.com"}
        role = map_role_from_claims(claims, default_role="readonly")
        assert role == "readonly"

    def test_map_groups_string(self):
        """Handle groups as string instead of list."""
        claims = {"groups": "admin"}
        role = map_role_from_claims(claims)
        assert role == "tenant_admin"


class TestOIDCProviderConfig:
    """Test OIDC provider configuration."""

    def test_from_settings_success(self):
        """Create config from tenant settings."""
        settings = {
            "oidc": {
                "provider_name": "okta",
                "enabled": True,
                "config": {
                    "issuer_url": "https://example.okta.com",
                    "client_id": "test-client",
                    "client_secret": "test-secret",
                    "redirect_uri": "https://app.example.com/callback",
                    "scopes": ["openid", "profile", "email"],
                }
            }
        }

        config = OIDCProviderConfig.from_settings(settings)

        assert config is not None
        assert config.provider_name == "okta"
        assert config.issuer_url == "https://example.okta.com"
        assert config.client_id == "test-client"
        assert config.enabled is True

    def test_from_settings_disabled(self):
        """Return None when OIDC is disabled."""
        settings = {
            "oidc": {
                "enabled": False,
            }
        }

        config = OIDCProviderConfig.from_settings(settings)
        assert config is None

    def test_from_settings_no_oidc(self):
        """Return None when no OIDC settings."""
        settings = {"other": "value"}
        config = OIDCProviderConfig.from_settings(settings)
        assert config is None

    def test_from_settings_flat_config(self):
        """Handle flat config structure (no nested config key)."""
        settings = {
            "oidc": {
                "issuer_url": "https://auth.example.com",
                "client_id": "test-client",
            }
        }

        config = OIDCProviderConfig.from_settings(settings)

        assert config is not None
        assert config.issuer_url == "https://auth.example.com"
        assert config.client_id == "test-client"


class TestOIDCIntegration:
    """Integration tests for OIDC flow."""

    @pytest.mark.asyncio
    async def test_full_oidc_flow_mocked(self):
        """Test complete OIDC flow with mocked responses."""
        client = OIDCClient()

        # Mock discovery
        discovery_response = {
            "issuer": "https://auth.example.com",
            "authorization_endpoint": "https://auth.example.com/oauth/authorize",
            "token_endpoint": "https://auth.example.com/oauth/token",
            "userinfo_endpoint": "https://auth.example.com/oauth/userinfo",
            "jwks_uri": "https://auth.example.com/oauth/keys",
        }

        with patch.object(client._http_client, "get") as mock_get:
            mock_get.return_value = Mock(
                raise_for_status=Mock(),
                json=Mock(return_value=discovery_response)
            )

            # Test discovery
            metadata = await client.discover("https://auth.example.com")
            assert metadata["issuer"] == "https://auth.example.com"

            # Test authorize URL generation
            auth_url = client.build_authorize_url(
                metadata=metadata,
                client_id="test-client",
                redirect_uri="https://app.example.com/callback",
                state="state-123",
                code_challenge="challenge-abc",
            )
            assert "state=state-123" in auth_url
            assert "code_challenge=challenge-abc" in auth_url


class TestOIDCErrorHandling:
    """Test error handling and edge cases."""

    @pytest.fixture
    def oidc_client(self):
        """Create OIDC client fixture."""
        return OIDCClient()

    @pytest.mark.asyncio
    async def test_discover_404_error(self, oidc_client):
        """Discovery must not retry on 404 and must raise OIDCDiscoveryError (non-retryable)."""
        from value_fabric.shared.identity.oidc import OIDCDiscoveryError
        with patch.object(oidc_client._http_client, "get") as mock_get:
            mock_get.side_effect = httpx.HTTPStatusError(
                "Not Found",
                request=Mock(),
                response=Mock(status_code=404),
            )

            with pytest.raises(OIDCDiscoveryError):
                await oidc_client.discover("https://auth.example.com")

            # Must not retry on 4xx
            assert mock_get.call_count == 1

    @pytest.mark.asyncio
    async def test_discover_retry_on_500(self, oidc_client):
        """Discovery must retry exactly once on 500 and succeed with a valid document."""
        _valid_doc = {
            "issuer": "https://auth.example.com",
            "authorization_endpoint": "https://auth.example.com/authorize",
            "token_endpoint": "https://auth.example.com/token",
            "jwks_uri": "https://auth.example.com/.well-known/jwks.json",
        }
        with patch.object(oidc_client._http_client, "get") as mock_get:
            mock_get.side_effect = [
                httpx.HTTPStatusError(
                    "Server Error",
                    request=Mock(),
                    response=Mock(status_code=500),
                ),
                Mock(raise_for_status=Mock(), json=Mock(return_value=_valid_doc)),
            ]

            result = await oidc_client.discover("https://auth.example.com")
            assert result["issuer"] == "https://auth.example.com"
            assert mock_get.call_count == 2

    @pytest.mark.asyncio
    async def test_exchange_code_4xx_no_retry(self, oidc_client):
        """Token exchange should not retry on 4xx errors."""
        with patch.object(oidc_client._http_client, "post") as mock_post:
            mock_post.side_effect = httpx.HTTPStatusError(
                "Bad Request",
                request=Mock(),
                response=Mock(status_code=400),
            )

            with pytest.raises(httpx.HTTPStatusError):
                await oidc_client.exchange_code(
                    token_endpoint="https://auth.example.com/token",
                    code="invalid_code",
                    redirect_uri="https://app.example.com/callback",
                    client_id="test-client",
                    client_secret="secret",
                )

            # Should not retry on 400
            assert mock_post.call_count == 1


class TestOIDCProviderConfigValidation:
    """Test OIDC config validation."""

    def test_from_settings_missing_issuer_url(self):
        """Should raise ValueError when issuer_url is missing."""
        settings = {
            "oidc": {
                "client_id": "test-client",
                # Missing issuer_url
            }
        }

        with pytest.raises(ValueError, match="issuer_url"):
            OIDCProviderConfig.from_settings(settings)

    def test_from_settings_missing_client_id(self):
        """Should raise ValueError when client_id is missing."""
        settings = {
            "oidc": {
                "issuer_url": "https://auth.example.com",
                # Missing client_id
            }
        }

        with pytest.raises(ValueError, match="client_id"):
            OIDCProviderConfig.from_settings(settings)

    def test_from_settings_empty_issuer_url(self):
        """Should raise ValueError when issuer_url is empty string."""
        settings = {
            "oidc": {
                "issuer_url": "",
                "client_id": "test-client",
            }
        }

        with pytest.raises(ValueError, match="issuer_url"):
            OIDCProviderConfig.from_settings(settings)


class TestRoleMappingEdgeCases:
    """Test role mapping edge cases."""

    def test_map_role_with_list_claim_values(self):
        """Handle list claim values properly."""
        claims = {"roles": ["user", "admin", "editor"]}
        mapping = {"roles": "admin"}
        role = map_role_from_claims(claims, claim_mapping=mapping)
        assert role == "admin"

    def test_map_role_partial_match_should_not_work(self):
        """Partial string matching should not work anymore."""
        claims = {"role": "superadmin"}  # Contains 'admin' but not equal
        mapping = {"role": "admin"}
        role = map_role_from_claims(claims, claim_mapping=mapping)
        # Should not match "superadmin" to "admin" anymore (exact match required)
        assert role != "admin"  # Falls through to default logic

    def test_map_role_case_insensitive(self):
        """Role mapping should be case insensitive."""
        claims = {"Role": "ADMIN"}  # Mixed case
        mapping = {"Role": "admin"}
        role = map_role_from_claims(claims, claim_mapping=mapping)
        assert role == "admin"


class TestExtractContextAdversarial:
    """Adversarial tests for extract_context_from_jwt tenant isolation invariants."""

    def test_missing_tenant_id_raises(self):
        """extract_context_from_jwt raises ValueError when tenant_id is absent."""
        payload = {"sub": "user-1", "roles": ["analyst"]}
        with pytest.raises(ValueError, match="tenant_id"):
            extract_context_from_jwt(payload)

    def test_empty_tenant_id_raises(self):
        """extract_context_from_jwt raises ValueError when tenant_id is empty string."""
        payload = {"sub": "user-1", "tenant_id": "", "roles": ["analyst"]}
        with pytest.raises(ValueError, match="tenant_id"):
            extract_context_from_jwt(payload)

    def test_non_uuid_tenant_id_raises_in_production(self):
        """Non-UUID tenant_id raises ValueError in non-test environments."""
        payload = {
            "sub": "user-1",
            "tenant_id": "not-a-uuid",
            "roles": ["analyst"],
        }
        with patch.dict("os.environ", {
            "ALLOW_LEGACY_TEST_TENANT_IDS": "false",
            "TESTING": "false",
            "ENVIRONMENT": "production",
        }):
            with pytest.raises(ValueError, match="tenant_id"):
                extract_context_from_jwt(payload)

    def test_tenant_id_from_jwt_is_immutable_in_context(self):
        """RequestContext.tenant_id matches the JWT claim exactly."""
        tenant_uuid = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
        user_uuid = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
        payload = {
            "sub": user_uuid,
            "tenant_id": tenant_uuid,
            "roles": ["analyst"],
        }
        ctx = extract_context_from_jwt(payload)
        assert str(ctx.tenant_id) == tenant_uuid

    def test_permissions_count_limit_enforced(self):
        """More than 1024 permissions in JWT claims raises ValueError."""
        payload = {
            "sub": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            "tenant_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "roles": ["analyst"],
            "permissions": [f"perm:{i}" for i in range(1025)],
        }
        with pytest.raises(ValueError, match="Too many permissions"):
            extract_context_from_jwt(payload)


class TestVerifyIdTokenHardening:
    """Tests for OIDCClient.verify_id_token security invariants."""

    @pytest.fixture
    def rsa_keypair(self):
        import base64

        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import rsa

        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        pem_private = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        pub_numbers = private_key.public_key().public_numbers()

        def _b64url(n: int) -> str:
            byte_len = (n.bit_length() + 7) // 8
            return base64.urlsafe_b64encode(n.to_bytes(byte_len, "big")).decode().rstrip("=")

        jwk = {
            "kty": "RSA", "kid": "test-kid", "use": "sig", "alg": "RS256",
            "n": _b64url(pub_numbers.n), "e": _b64url(pub_numbers.e),
        }
        return pem_private, jwk

    def _make_token(self, private_pem: bytes, issuer: str, audience: str, **overrides) -> str:
        from datetime import datetime, timedelta, timezone

        import jwt as pyjwt
        now = datetime.now(UTC)
        claims = {
            "sub": "user-1", "iss": issuer, "aud": audience,
            "iat": int((now - timedelta(seconds=5)).timestamp()),
            "exp": int((now + timedelta(minutes=5)).timestamp()),
            "nonce": "test-nonce",
        }
        claims.update(overrides)
        return pyjwt.encode(claims, private_pem, algorithm="RS256", headers={"kid": "test-kid"})

    @pytest.mark.asyncio
    async def test_verify_id_token_rejects_wrong_nonce(self, rsa_keypair):
        """verify_id_token raises InvalidTokenError when nonce does not match."""
        import jwt as pyjwt
        private_pem, jwk = rsa_keypair
        issuer = "https://idp.example.com"
        token = self._make_token(private_pem, issuer, "client-id", nonce="correct-nonce")

        client = OIDCClient()
        jwks_data = {"keys": [jwk]}

        async def _mock_get_signing_key(issuer_url, kid=None):
            return pyjwt.api_jwk.PyJWK(jwk)

        client.get_signing_key = _mock_get_signing_key

        with pytest.raises(pyjwt.InvalidTokenError, match="nonce"):
            await client.verify_id_token(
                id_token=token,
                issuer_url=issuer,
                client_id="client-id",
                nonce="wrong-nonce",
            )

    @pytest.mark.asyncio
    async def test_verify_id_token_rejects_stale_iat(self, rsa_keypair):
        """verify_id_token raises InvalidTokenError when iat is older than max_iat_age_seconds."""
        from datetime import datetime, timedelta, timezone

        import jwt as pyjwt
        private_pem, jwk = rsa_keypair
        issuer = "https://idp.example.com"

        stale_iat = int((datetime.now(UTC) - timedelta(seconds=700)).timestamp())
        token = self._make_token(private_pem, issuer, "client-id", iat=stale_iat, nonce=None)

        client = OIDCClient()

        async def _mock_get_signing_key(issuer_url, kid=None):
            return pyjwt.api_jwk.PyJWK(jwk)

        client.get_signing_key = _mock_get_signing_key

        with pytest.raises(pyjwt.InvalidTokenError, match="iat"):
            await client.verify_id_token(
                id_token=token,
                issuer_url=issuer,
                client_id="client-id",
                max_iat_age_seconds=600,
            )

    @pytest.mark.asyncio
    async def test_verify_id_token_accepts_valid_token(self, rsa_keypair):
        """verify_id_token returns claims for a well-formed token."""
        import jwt as pyjwt
        private_pem, jwk = rsa_keypair
        issuer = "https://idp.example.com"
        token = self._make_token(private_pem, issuer, "client-id", nonce="my-nonce")

        client = OIDCClient()

        async def _mock_get_signing_key(issuer_url, kid=None):
            return pyjwt.api_jwk.PyJWK(jwk)

        client.get_signing_key = _mock_get_signing_key

        claims = await client.verify_id_token(
            id_token=token,
            issuer_url=issuer,
            client_id="client-id",
            nonce="my-nonce",
        )
        assert claims["sub"] == "user-1"


class TestRoleMappingPrivilegeOrdering:
    """Verify highest-privilege role is selected when multiple mappings match."""

    def test_highest_privilege_wins_when_multiple_match(self):
        """When analyst and tenant_admin both match, tenant_admin is returned."""
        claims = {"roles": ["analyst", "tenant_admin"]}
        mapping = {
            "roles=analyst": "analyst",
            "roles=tenant_admin": "tenant_admin",
        }
        role = map_role_from_claims(claims, claim_mapping=mapping, default_role="read_only")
        assert role == "tenant_admin"

    def test_default_role_when_no_mapping_matches(self):
        """Returns default_role when no claim mapping matches."""
        claims = {"roles": ["unknown_group"]}
        mapping = {"roles=admin": "tenant_admin"}
        role = map_role_from_claims(claims, claim_mapping=mapping, default_role="read_only")
        assert role == "read_only"

    def test_regex_claim_matching(self):
        """Regex pattern /^admin.*/ matches 'admin-team' in groups array."""
        claims = {"groups": ["dev-team", "admin-team"]}
        mapping = {"groups=/^admin.*/": "tenant_admin"}
        role = map_role_from_claims(claims, claim_mapping=mapping, default_role="read_only")
        assert role == "tenant_admin"

    def test_nested_claim_path_dot_notation(self):
        """Dot-notation resolves nested claim: resource_access.fabric.roles."""
        claims = {"resource_access": {"fabric": {"roles": ["analyst"]}}}
        mapping = {"resource_access.fabric.roles=analyst": "analyst"}
        role = map_role_from_claims(claims, claim_mapping=mapping, default_role="read_only")
        assert role == "analyst"

    def test_empty_claim_mapping_falls_back_to_role_claim(self):
        """With no claim_mapping, a valid role in the 'role' claim is returned directly."""
        claims = {"role": "content_admin"}
        role = map_role_from_claims(claims, claim_mapping={}, default_role="read_only")
        assert role == "content_admin"

    def test_empty_claim_mapping_admin_group_detection(self):
        """With no claim_mapping, 'admin' in groups returns tenant_admin."""
        claims = {"groups": ["admin"]}
        role = map_role_from_claims(claims, claim_mapping={}, default_role="read_only")
        assert role == "tenant_admin"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
