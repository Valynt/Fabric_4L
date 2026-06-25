"""OIDC provider resolution helpers.

These helpers keep tenant OIDC route configuration provider-agnostic while
centralizing lightweight provider presets and client-secret lookup.
"""

from __future__ import annotations

import os
from typing import Callable

from .oidc_config import OIDCProviderConfig


def _set_google_defaults(config: OIDCProviderConfig) -> None:
    if not config.issuer_url:
        config.issuer_url = "https://accounts.google.com"
    if not config.scopes:
        config.scopes = ["openid", "email", "profile"]


def _set_microsoft_defaults(config: OIDCProviderConfig) -> None:
    if not config.scopes:
        config.scopes = ["openid", "email", "profile", "offline_access"]


def _set_apple_defaults(config: OIDCProviderConfig) -> None:
    if not config.scopes:
        config.scopes = ["name", "email"]


def _set_clerk_defaults(config: OIDCProviderConfig) -> None:
    # Clerk uses standard OIDC with Organizations for multi-tenancy.
    # Fallback env vars are read here only when the tenant settings do not
    # already specify issuer_url / jwks_uri. The caller (gateway/L4) should
    # ideally pre-populate these from its centralized Settings so this
    # fallback is not reached in production.
    if not config.issuer_url:
        # Historical compatibility alias. New gateway deployments should
        # use services/api's canonical Clerk issuer setting instead.
        clerk_domain = os.getenv("CLERK_JWT_ISSUER", "").replace("https://", "")
        if clerk_domain:
            config.issuer_url = f"https://{clerk_domain}"
    if not config.scopes:
        config.scopes = ["openid", "email", "profile", "org"]
    if not config.jwks_uri:
        clerk_jwks = os.getenv("CLERK_JWKS_URL")
        if clerk_jwks:
            config.jwks_uri = clerk_jwks


_OIDC_PROVIDER_DEFAULTS: dict[str, Callable[[OIDCProviderConfig], None]] = {
    "google": _set_google_defaults,
    "microsoft": _set_microsoft_defaults,
    "apple": _set_apple_defaults,
    "clerk": _set_clerk_defaults,
}


def resolve_oidc_config(config: OIDCProviderConfig) -> OIDCProviderConfig:
    """Return an OIDC config with provider-specific defaults applied."""
    provider = (config.provider_name or "").strip().lower()
    defaults_fn = _OIDC_PROVIDER_DEFAULTS.get(provider)
    if defaults_fn is not None:
        defaults_fn(config)
    return config


async def resolve_client_secret(config: OIDCProviderConfig) -> str:
    """Resolve a client secret from the configured reference or fallback env."""
    if config.client_secret_ref:
        if config.client_secret_ref.startswith("vault:"):
            raise ValueError(
                "Vault-backed OIDC client secret resolution is not configured in this environment"
            )
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
