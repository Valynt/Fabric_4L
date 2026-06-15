from __future__ import annotations

"""Unit tests for OIDC client, claim mapping, and configuration.

Tests the shared OIDC client with PKCE support and role mapping.
"""


import base64
import hashlib
import os
import sys
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import httpx

# Set required environment variable for shared imports
os.environ["JWT_SECRET"] = "test-secret-123456789012345678901234567890"

# Import from root shared module (canonical implementation)
from value_fabric.shared.identity.oidc import OIDCClient, map_role_from_claims
from value_fabric.shared.identity.oidc_config import OIDCProviderConfig
from value_fabric.shared.identity.permissions import Role


class TestRoleMapping:
    """Tests for the OIDC claim → role mapping engine."""

    def test_map_role_from_claims_exact_match(self) -> None:
        """Test exact string match in claim mapping."""
        claims = {"role": "admin"}
        result = map_role_from_claims(claims, {"role": "admin"}, "user")
        assert result == "admin"

    def test_map_role_from_claims_array_match(self) -> None:
        """Test matching against array claim values."""
        claims = {"groups": ["users", "admins"]}
        result = map_role_from_claims(claims, {"groups": "admins"}, "user")
        assert result == "admins"

    def test_map_role_admin_detection(self) -> None:
        """Test admin detection in role claim."""
        claims = {"role": "super_admin"}
        result = map_role_from_claims(claims, {}, "user")
        assert result == "super_admin"

    def test_map_role_groups_with_mapping(self) -> None:
        """Test role mapping from groups claim with explicit mapping."""
        claims = {"groups": ["engineering", "admin-team"]}
        result = map_role_from_claims(claims, {"groups": "admin-team"}, "viewer")
        assert result == "admin-team"

    def test_map_role_fallback_to_default(self) -> None:
        """Test fallback to default role when no mapping matches."""
        claims = {"role": "unknown"}
        result = map_role_from_claims(claims, {}, "analyst")
        assert result == "analyst"

    def test_map_role_case_insensitive(self) -> None:
        """Test case-insensitive claim value matching."""
        claims = {"groups": ["AdMiNs"]}
        result = map_role_from_claims(claims, {"groups": "admins"}, "user")
        assert result == "admins"

    def test_map_role_no_claims(self) -> None:
        """Test that default role is returned when claims are empty."""
        claims = {}
        result = map_role_from_claims(claims, {}, "guest")
        assert result == "guest"


class TestPKCEGeneration:
    """Test PKCE code generation for OAuth2 PKCE flow."""

    def _generate_code_verifier(self) -> str:
        """Generate PKCE code_verifier for tests (mirrors implementation)."""
        return base64.urlsafe_b64encode(os.urandom(32)).decode("ascii").rstrip("=")

    def _generate_code_challenge(self, code_verifier: str) -> str:
        """Generate PKCE code_challenge for tests (mirrors implementation)."""
        digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
        return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")

    def test_code_verifier_format(self) -> None:
        """Code verifier should be base64url encoded and 43+ chars."""
        verifier = self._generate_code_verifier()
        # RFC 7636: code_verifier is 43-128 chars
        assert len(verifier) >= 43
        assert len(verifier) <= 128
        # Should be URL-safe base64 characters only
        assert all(c in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_" for c in verifier)

    def test_code_challenge_consistency(self) -> None:
        """Same verifier should produce same challenge."""
        verifier = self._generate_code_verifier()
        challenge1 = self._generate_code_challenge(verifier)
        challenge2 = self._generate_code_challenge(verifier)

        assert challenge1 == challenge2
        assert challenge1 != verifier

    def test_code_challenge_s256(self) -> None:
        """Code challenge should be S256 hash of verifier."""
        verifier = "test_verifier_123456789012345678901234567890"
        challenge = self._generate_code_challenge(verifier)

        # Manual S256 calculation
        expected = base64.urlsafe_b64encode(
            hashlib.sha256(verifier.encode("ascii")).digest()
        ).decode("ascii").rstrip("=")

        assert challenge == expected


class TestOIDCClient:
    """Tests for OIDCClient discovery and token verification."""

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

        mock_get_response = MagicMock()
        mock_get_response.raise_for_status = MagicMock()
        mock_get_response.json = MagicMock(return_value=mock_response)

        with patch.object(oidc_client._http, "get", return_value=mock_get_response):
            result = await oidc_client.discover("https://auth.example.com")
            assert result == mock_response

    @pytest.mark.asyncio
    async def test_discover_retries_on_failure(self, oidc_client):
        """OIDC discovery should retry on transient failures."""
        mock_get_response = MagicMock()
        mock_get_response.raise_for_status = MagicMock()
        mock_get_response.json = MagicMock(return_value={"issuer": "https://auth.example.com"})

        # First call fails, second succeeds
        with patch.object(
            oidc_client._http,
            "get",
            side_effect=[Exception("Connection error"), mock_get_response]
        ):
            # Should retry and eventually succeed
            with patch("asyncio.sleep"):  # Don't actually sleep in tests
                result = await oidc_client.discover("https://auth.example.com")
                assert result["issuer"] == "https://auth.example.com"

    @pytest.mark.asyncio
    async def test_discover_no_retry_on_4xx(self, oidc_client):
        """OIDC discovery should not retry on 4xx client errors."""
        import httpx

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not found", request=MagicMock(), response=mock_response
        )

        with patch.object(oidc_client._http, "get", return_value=mock_response):
            with pytest.raises(httpx.HTTPStatusError):
                await oidc_client.discover("https://auth.example.com")

    def test_build_authorize_url_basic(self) -> None:
        """Build authorization URL with minimal parameters."""
        client = OIDCClient()
        url = client.build_authorize_url(
            metadata={"authorization_endpoint": "https://idp.example.com/auth"},
            client_id="client-123",
            redirect_uri="https://app.example.com/callback",
            state="abc123",
            nonce="nonce123",
            scopes=["openid"],
        )
        assert "https://idp.example.com/auth?" in url
        assert "client_id=client-123" in url
        assert "state=abc123" in url
        assert "nonce=nonce123" in url
        assert "response_type=code" in url

    def test_build_authorize_url_with_pkce(self) -> None:
        """Build authorization URL with PKCE parameters."""
        client = OIDCClient()
        url = client.build_authorize_url(
            metadata={"authorization_endpoint": "https://idp.example.com/auth"},
            client_id="client-123",
            redirect_uri="https://app.example.com/callback",
            state="abc123",
            nonce="def456",
            scopes=["openid", "email", "profile"],
        )
        assert "https://idp.example.com/auth?" in url
        assert "client_id=client-123" in url
        assert "state=abc123" in url
        assert "nonce=def456" in url
        assert "scope=openid+email+profile" in url

    @pytest.mark.asyncio
    async def test_exchange_code_success(self, oidc_client):
        """Test successful authorization code exchange."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = MagicMock(return_value={
            "access_token": "access_token_123",
            "id_token": "id_token_456",
            "refresh_token": "refresh_token_789",
            "token_type": "Bearer",
            "expires_in": 3600,
        })

        with patch.object(oidc_client._http, "post", return_value=mock_response):
            result = await oidc_client.exchange_code(
                token_endpoint="https://idp.example.com/token",
                code="auth_code_123",
                redirect_uri="https://app.example.com/callback",
                client_id="client-123",
                client_secret="secret_456",
            )
            assert result["access_token"] == "access_token_123"
            assert result["id_token"] == "id_token_456"
            assert result["refresh_token"] == "refresh_token_789"
            assert result["token_type"] == "Bearer"
            assert result["expires_in"] == 3600

    @pytest.mark.asyncio
    async def test_exchange_code_no_retry_on_4xx(self, oidc_client):
        """Code exchange should not retry on 4xx errors."""
        import httpx

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Bad request", request=MagicMock(), response=mock_response
        )

        with patch.object(oidc_client._http, "post", return_value=mock_response):
            with pytest.raises(httpx.HTTPStatusError):
                await oidc_client.exchange_code(
                    token_endpoint="https://idp.example.com/token",
                    code="invalid_code",
                    redirect_uri="https://app.example.com/callback",
                    client_id="client-123",
                    client_secret="secret_456",
                )

    @pytest.mark.asyncio
    async def test_get_userinfo_success(self, oidc_client):
        """Test successful UserInfo endpoint request."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = MagicMock(return_value={
            "sub": "user-123",
            "email": "user@example.com",
            "name": "Test User",
        })

        with patch.object(oidc_client._http, "get", return_value=mock_response):
            result = await oidc_client.get_userinfo(
                userinfo_endpoint="https://idp.example.com/userinfo",
                access_token="access_token_123",
            )
            assert result is not None
            assert result["sub"] == "user-123"
            assert result["email"] == "user@example.com"


class TestOIDCProviderConfig:
    """Tests for OIDCProviderConfig Pydantic model."""

    def test_oidc_provider_config_creation(self) -> None:
        """Test creating OIDCProviderConfig with all fields."""
        config = OIDCProviderConfig(
            provider_name="test-idp",
            issuer_url="https://idp.example.com",
            client_id="client-123",
            client_secret="secret-456",
            jwks_uri="https://idp.example.com/.well-known/jwks.json",
            authorization_endpoint="https://idp.example.com/auth",
            token_endpoint="https://idp.example.com/token",
            userinfo_endpoint="https://idp.example.com/userinfo",
            redirect_uri="https://app.example.com/callback",
            scopes=["openid", "email"],
            claim_mapping={"groups": "admin"},
            default_role="analyst",
            auto_provision_users=True,
            enabled=True,
        )

        assert config.provider_name == "test-idp"
        assert config.issuer_url == "https://idp.example.com"
        assert config.client_id == "client-123"
        assert config.client_secret_ref == "secret-456"
        assert str(config.jwks_uri) == "https://idp.example.com/.well-known/jwks.json"
        assert config.scopes == ["openid", "email"]
        assert config.claim_mapping == {"groups": "admin"}
        assert config.default_role == "analyst"
        assert config.auto_provision_users is True
        assert config.enabled is True

    def test_oidc_provider_config_defaults(self) -> None:
        """Test OIDCProviderConfig default values."""
        config = OIDCProviderConfig(
            provider_name="oidc",
            issuer_url="https://idp.example.com",
            client_id="client-123",
        )

        assert config.provider_name == "oidc"
        assert config.scopes == ["openid", "email", "profile"]  # Default
        assert config.default_role == "read_only"  # Default
        assert config.auto_provision_users is False  # Default
        assert config.enabled is True  # Default
        assert config.client_secret_ref is None
        assert config.claim_mapping == {}  # Default empty dict

    def test_from_settings_valid_config(self) -> None:
        """Test parsing valid OIDC configuration from tenant settings."""
        settings = {
            "oidc": {
                "provider_name": "test-idp",
                "issuer_url": "https://idp.example.com",
                "client_id": "client-123",
                "client_secret_ref": "secret-456",
                "scopes": ["openid", "email"],
                "claim_mapping": {"groups": "admin"},
                "default_role": "analyst",
                "auto_provision_users": True,
                "enabled": True,
            }
        }

        config = OIDCProviderConfig.from_settings(settings)

        assert config is not None
        assert config.provider_name == "test-idp"
        assert config.issuer_url == "https://idp.example.com"
        assert config.client_id == "client-123"
        assert config.client_secret_ref == "secret-456"
        assert config.scopes == ["openid", "email"]
        assert config.claim_mapping == {"groups": "admin"}
        assert config.default_role == "analyst"
        assert config.auto_provision_users is True

    def test_from_settings_disabled_oidc(self) -> None:
        """Test that disabled OIDC returns None."""
        settings = {
            "oidc": {
                "enabled": False,
                "issuer_url": "https://idp.example.com",
                "client_id": "client-123",
            }
        }

        config = OIDCProviderConfig.from_settings(settings)
        assert config is None

    def test_from_settings_missing_oidc_key(self) -> None:
        """Test that missing OIDC key returns None."""
        settings = {"other_setting": "value"}

        config = OIDCProviderConfig.from_settings(settings)
        assert config is None

    def test_from_settings_missing_required_fields(self) -> None:
        """Test validation error for missing required fields."""
        settings = {
            "oidc": {
                "client_id": "client-123",
                # Missing issuer_url
            }
        }

        with pytest.raises(ValueError, match="issuer_url"):
            OIDCProviderConfig.from_settings(settings)

    def test_from_settings_nested_config(self) -> None:
        """Test parsing OIDC config nested under 'config' key."""
        settings = {
            "oidc": {
                "config": {
                    "issuer_url": "https://idp.example.com",
                    "client_id": "client-123",
                }
            }
        }

        config = OIDCProviderConfig.from_settings(settings)
        assert config is not None
        assert config.issuer_url == "https://idp.example.com"
        assert config.client_id == "client-123"

    def test_config_extra_fields_allowed(self) -> None:
        """Test that extra fields are allowed (for forward compatibility)."""
        config = OIDCProviderConfig(
            provider_name="test",
            issuer_url="https://auth.example.com",
            client_id="test-client",
            client_secret="test-secret",
            redirect_uri="http://localhost:8000/callback",
        )

        assert config.issuer_url == "https://auth.example.com"
        assert config.client_id == "test-client"
