"""Tests for OIDC provider default resolution."""

from value_fabric.shared.identity.oidc_config import OIDCProviderConfig
from value_fabric.shared.identity.providers import resolve_oidc_config


def _blank_config(provider_name: str) -> OIDCProviderConfig:
    """Return a config with blank fields so defaults can be applied."""
    return OIDCProviderConfig.model_construct(
        provider_name=provider_name,
        issuer_url="",
        client_id="cid",
        scopes=[],
        jwks_uri=None,
    )


def test_google_defaults():
    config = _blank_config("google")
    result = resolve_oidc_config(config)
    assert result.issuer_url == "https://accounts.google.com"
    assert result.scopes == ["openid", "email", "profile"]


def test_microsoft_defaults():
    config = _blank_config("microsoft")
    result = resolve_oidc_config(config)
    assert result.scopes == ["openid", "email", "profile", "offline_access"]


def test_apple_defaults():
    config = _blank_config("apple")
    result = resolve_oidc_config(config)
    assert result.scopes == ["name", "email"]


def test_clerk_defaults_from_env(monkeypatch):
    monkeypatch.setenv("CLERK_JWT_ISSUER", "https://clerk.example.com")
    monkeypatch.setenv(
        "CLERK_JWKS_URL", "https://clerk.example.com/.well-known/jwks.json"
    )

    config = _blank_config("clerk")
    result = resolve_oidc_config(config)
    assert result.issuer_url == "https://clerk.example.com"
    assert result.jwks_uri == "https://clerk.example.com/.well-known/jwks.json"
    assert result.scopes == ["openid", "email", "profile", "org"]


def test_clerk_defaults_without_env():
    config = _blank_config("clerk")
    result = resolve_oidc_config(config)
    assert result.issuer_url == ""
    assert result.jwks_uri is None
    assert result.scopes == ["openid", "email", "profile", "org"]


def test_existing_values_are_not_overwritten():
    config = OIDCProviderConfig(
        provider_name="google",
        issuer_url="https://custom.example.com",
        client_id="cid",
        scopes=["openid"],
    )
    result = resolve_oidc_config(config)
    assert result.issuer_url == "https://custom.example.com"
    assert result.scopes == ["openid"]


def test_unknown_provider_is_unchanged():
    config = _blank_config("unknown")
    result = resolve_oidc_config(config)
    assert result.issuer_url == ""
    assert result.scopes == []


def test_provider_name_is_case_insensitive():
    config = _blank_config("Google")
    result = resolve_oidc_config(config)
    assert result.issuer_url == "https://accounts.google.com"
