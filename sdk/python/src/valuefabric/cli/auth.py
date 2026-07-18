"""Authentication commands for the CLI."""

from __future__ import annotations

import webbrowser
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode, urljoin, urlparse, urlunparse
from uuid import uuid4

import httpx
import jwt
import typer
from rich import print as rich_print
from rich.prompt import Prompt

from ._utils import get_client
from .config import CONFIG_DIR, CONFIG_FILE, _load_config, _save_config

app = typer.Typer(help="Authentication management")

# PKCE state storage
PKCE_STATE_FILE = CONFIG_DIR / ".pkce_state"


def _generate_pkce_verifier() -> str:
    """Generate a PKCE code verifier."""
    import secrets

    return secrets.token_urlsafe(32)


def _generate_pkce_challenge(verifier: str) -> str:
    """Generate a PKCE code challenge from verifier."""
    import base64
    import hashlib

    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def _is_jwt(token: str) -> bool:
    """Check if token is a JWT (3 base64url parts separated by dots).

    Args:
        token: The token string to check

    Returns:
        True if token appears to be a JWT structure
    """
    parts = token.split(".")
    return len(parts) == 3 and all(p for p in parts)


@app.command("login")
def login(
    base_url: str | None = typer.Option(
        None, "--url", "-u", help="Base URL of the Value Fabric API"
    ),
    tenant: str | None = typer.Option(
        None, "--tenant", "-t", help="Tenant ID for OIDC login"
    ),
    api_key: bool = typer.Option(
        False, "--api-key", "-k", help="Use API key authentication instead of OIDC"
    ),
) -> None:
    """Authenticate with the Value Fabric API.

    Uses OIDC with PKCE by default, or API key if --api-key flag is provided.
    """
    if api_key:
        _login_api_key(base_url)
    else:
        _login_oidc(base_url, tenant)


def _login_api_key(base_url: str | None) -> None:
    """Authenticate using an API key."""
    config = _load_config()

    if not base_url:
        base_url = Prompt.ask("Base URL", default=config.get("profiles", {}).get("default", {}).get("base_url", "https://api.valuefabric.io"))

    api_key = Prompt.ask("API Key", password=True)

    # Verify the API key works
    try:
        from valuefabric import ValueFabricClient

        client = ValueFabricClient(base_url=base_url, api_key=api_key)
        health = client.health_check()
        rich_print(f"[green]✓ Authenticated successfully[/green]")
        rich_print(f"[dim]Server version: {health.get('version', 'unknown')}[/dim]")
    except Exception as e:
        rich_print(f"[red]✗ Authentication failed: {e}[/red]")
        raise typer.Exit(1)

    # Save to config
    config.setdefault("profiles", {}).setdefault("default", {})["base_url"] = base_url
    config["profiles"]["default"]["api_key"] = api_key
    _save_config(config)
    rich_print(f"[green]Credentials saved to {CONFIG_FILE}[/green]")


def _login_oidc(base_url: str | None, tenant: str | None) -> None:
    """Authenticate using OIDC with PKCE."""
    config = _load_config()

    if not base_url:
        base_url = Prompt.ask(
            "Base URL",
            default=config.get("profiles", {}).get("default", {}).get("base_url", "https://api.valuefabric.io")
        )

    if not tenant:
        tenant = Prompt.ask("Tenant ID")

    # Generate PKCE verifier and challenge
    code_verifier = _generate_pkce_verifier()
    code_challenge = _generate_pkce_challenge(code_verifier)
    state = str(uuid4())

    # Save state for callback verification
    PKCE_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    PKCE_STATE_FILE.write_text(f"{state}:{code_verifier}")

    # Build authorization URL
    auth_url = urljoin(base_url, f"/api/v1/auth/oidc/{tenant}/login")
    params = {
        "response_type": "code",
        "client_id": tenant,
        "redirect_uri": f"{base_url}/auth/callback",
        "scope": "openid profile email",
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    # Safely construct URL to avoid double query strings
    parsed = urlparse(urljoin(base_url, f"/api/v1/auth/oidc/{tenant}/login"))
    full_url = urlunparse((
        parsed.scheme, parsed.netloc, parsed.path, parsed.params,
        urlencode(params), parsed.fragment
    ))

    rich_print(f"[dim]Opening browser for authentication...[/dim]")
    webbrowser.open(full_url)

    # TODO: Implement local callback server for automated token capture
    # For now, user manually copies token
    rich_print(f"\n[yellow]If browser didn't open, visit:[/yellow]")
    rich_print(f"{full_url}")

    # Manual token entry fallback
    token = Prompt.ask("\nPaste the authorization code or JWT token from the callback", password=True)

    # Exchange code for token or use as-is
    if _is_jwt(token):
        jwt_token = token
    else:
        # Exchange code for token
        jwt_token = _exchange_code_for_token(base_url, token, code_verifier, tenant)

    if not jwt_token:
        rich_print("[red]Failed to obtain authentication token[/red]")
        raise typer.Exit(1)

    # Verify token works
    try:
        from valuefabric import ValueFabricClient

        client = ValueFabricClient(base_url=base_url, jwt_token=jwt_token)
        health = client.health_check()
        rich_print(f"[green]✓ Authenticated successfully[/green]")
    except Exception as e:
        rich_print(f"[red]✗ Token validation failed: {e}[/red]")
        raise typer.Exit(1)

    # Extract token expiration for tracking
    try:
        decoded = jwt.decode(jwt_token, options={"verify_signature": False})
        jwt_expires_at = decoded.get("exp")
    except Exception:
        jwt_expires_at = None

    # Save to config
    config.setdefault("profiles", {}).setdefault("default", {})["base_url"] = base_url
    config["profiles"]["default"]["jwt_token"] = jwt_token
    if jwt_expires_at:
        config["profiles"]["default"]["jwt_expires_at"] = jwt_expires_at
    _save_config(config)
    rich_print(f"[green]Credentials saved to {CONFIG_FILE}[/green]")


def _exchange_code_for_token(base_url: str, code: str, code_verifier: str, tenant: str) -> str | None:
    """Exchange authorization code for access token."""
    token_url = urljoin(base_url, f"/api/v1/auth/oidc/{tenant}/token")

    try:
        response = httpx.post(
            token_url,
            json={
                "grant_type": "authorization_code",
                "code": code,
                "code_verifier": code_verifier,
                "client_id": "valuefabric-cli",
                "redirect_uri": "http://localhost:8080/callback",
            },
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()
        return data.get("access_token")
    except Exception as e:
        rich_print(f"[red]Token exchange failed: {e}[/red]")
        return None


@app.command("logout")
def logout(
    profile: str = typer.Option("default", "--profile", "-p", help="Profile to logout from"),
) -> None:
    """Remove stored authentication credentials."""
    config = _load_config()

    if "profiles" in config and profile in config["profiles"]:
        config["profiles"][profile].pop("api_key", None)
        config["profiles"][profile].pop("jwt_token", None)
        _save_config(config)
        rich_print(f"[green]Logged out from profile '{profile}'[/green]")
    else:
        rich_print(f"[yellow]No credentials found for profile '{profile}'[/yellow]")


@app.command("status")
def status() -> None:
    """Check authentication status."""
    config = _load_config()
    profile = config.get("active_profile", "default")
    profile_config = config.get("profiles", {}).get(profile, {})

    rich_print(f"[bold]Active profile:[/bold] {profile}")

    base_url = profile_config.get("base_url", "Not set")
    rich_print(f"[bold]Base URL:[/bold] {base_url}")

    auth_type = None
    if "jwt_token" in profile_config:
        auth_type = "JWT (OIDC)"
    elif "api_key" in profile_config:
        auth_type = "API Key"

    if auth_type:
        rich_print(f"[bold]Authentication:[/bold] [green]{auth_type}[/green]")

        # Test connection
        try:
            from valuefabric import ValueFabricClient

            client = ValueFabricClient(
                base_url=base_url,
                api_key=profile_config.get("api_key"),
                jwt_token=profile_config.get("jwt_token"),
            )
            health = client.health_check()
            rich_print(f"[green]✓ Connected to Value Fabric API[/green]")
            rich_print(f"[dim]  Server version: {health.get('version', 'unknown')}[/dim]")
            rich_print(f"[dim]  Status: {health.get('status', 'unknown')}[/dim]")
        except Exception as e:
            rich_print(f"[red]✗ Connection failed: {e}[/red]")
    else:
        rich_print(f"[bold]Authentication:[/bold] [red]Not configured[/red]")
        rich_print(f"[dim]Run 'vf auth login' to authenticate[/dim]")
