"""OIDC provider resolution helpers.

These helpers keep tenant OIDC route configuration provider-agnostic while
centralizing lightweight provider presets and client-secret lookup.
"""

from __future__ import annotations

import os

from .oidc_config import OIDCProviderConfig


def resolve_oidc_config(config: OIDCProviderConfig) -> OIDCProviderConfig:
    """Return an OIDC config with provider-specific defaults applied."""
    provider = (config.provider_name or "").strip().lower()
    if provider == "google":
        if not config.issuer_url:
            config.issuer_url = "https://accounts.google.com"
        if not config.scopes:
            config.scopes = ["openid", "email", "profile"]
    elif provider == "microsoft":
        if not config.scopes:
            config.scopes = ["openid", "email", "profile", "offline_access"]
    elif provider == "apple":
        if not config.scopes:
            config.scopes = ["name", "email"]
    elif provider == "clerk":
        # Clerk uses standard OIDC with Organizations for multi-tenancy
        if not config.issuer_url:
            clerk_domain = os.getenv("CLERK_JWT_ISSUER", "").replace("https://", "")
            if clerk_domain:
                config.issuer_url = f"https://{clerk_domain}"
        if not config.scopes:
            config.scopes = ["openid", "email", "profile", "org"]
        if not config.jwks_uri:
            clerk_jwks = os.getenv("CLERK_JWKS_URL")
            if clerk_jwks:
                config.jwks_uri = clerk_jwks
    return config


async def resolve_client_secret(config: OIDCProviderConfig) -> str:
    """Resolve a client secret from the configured reference or fallback env."""
    if config.client_secret_ref:
        if config.client_secret_ref.startswith("vault:"):
            raise ValueError("Vault-backed OIDC client secret resolution is not configured in this environment")
        secret = os.getenv(config.client_secret_ref)
        if secret:
            return secret
        raise ValueError(f"Environment variable not set: {config.client_secret_ref}")

    fallback_key = f"OIDC_CLIENT_SECRET_{(config.provider_name or 'OIDC').upper()}"
    secret = os.getenv(fallback_key)
    if secret:
        return secret
    raise ValueError(
        f"No client secret found. Set {fallback_key} or configure client_secret_ref in tenant settings."
    )
