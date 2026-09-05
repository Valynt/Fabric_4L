"""Authentication commands for the CLI."""

from __future__ import annotations

import hmac
import http.server
import time
import webbrowser
from typing import Any
from urllib.parse import parse_qs, urljoin, urlparse

import httpx
import jwt
import typer
from rich import print as rich_print
from rich.prompt import Prompt

from .config import CONFIG_FILE, _load_config, _save_config

app = typer.Typer(help="Authentication management")

LOCAL_CALLBACK_HOST = "127.0.0.1"
LOCAL_CALLBACK_PORT = 8080
LOCAL_CALLBACK_PATH = "/callback"
LOCAL_REDIRECT_URI = f"http://{LOCAL_CALLBACK_HOST}:{LOCAL_CALLBACK_PORT}{LOCAL_CALLBACK_PATH}"
SESSION_COOKIE_NAME = "vf_session"


class TokenServer(http.server.HTTPServer):
    """Loopback HTTP server that captures a server-exchanged OIDC access token."""

    allow_reuse_address = True
    captured_token: str | None = None
    expected_state: str = ""
    oidc_callback_url: str = ""


class CallbackHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != LOCAL_CALLBACK_PATH:
            self.send_error(404)
            return

        qs = parse_qs(parsed.query)
        code = qs.get("code", [None])[0]
        state = qs.get("state", [None])[0]
        server = self.server
        assert isinstance(server, TokenServer)
        if (
            not code
            or not state
            or not server.expected_state
            or not hmac.compare_digest(state, server.expected_state)
        ):
            self.send_error(400, "Invalid OIDC callback")
            return

        try:
            response = httpx.get(
                server.oidc_callback_url,
                params={"code": code, "state": state},
                timeout=30.0,
            )
            response.raise_for_status()
            token = response.cookies.get(SESSION_COOKIE_NAME)
            if not isinstance(token, str) or not token:
                raise ValueError("OIDC callback did not set a session cookie")
            server.captured_token = token
        except Exception:
            # Break the CLI wait loop so it can fall back to manual JWT entry immediately.
            server.captured_token = ""
            self.send_error(502, "OIDC token exchange failed")
            return

        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(
            b"<html><body><h1>Authentication Successful</h1>"
            b"<p>You can close this window and return to the CLI.</p></body></html>"
        )

    def log_message(self, format: str, *args: Any) -> None:
        pass


def _wait_for_callback(server: TokenServer, timeout: int = 60) -> str | None:
    """Wait for a validated loopback callback; uses monotonic time for the timeout."""
    try:
        start_time = time.monotonic()
        while server.captured_token is None:
            if time.monotonic() - start_time > timeout:
                return None
            server.handle_request()
        return server.captured_token
    except Exception as e:
        rich_print(f"[dim]Local callback wait failed: {e}[/dim]")
        return None


def _begin_oidc_login(
    base_url: str,
    tenant: str,
    redirect_uri: str,
    server: TokenServer | None = None,
) -> tuple[str, str]:
    """Start the server-owned OIDC flow and open the returned IdP authorization URL."""
    login_url = urljoin(base_url, f"/api/v1/auth/oidc/{tenant}/login")
    response = httpx.get(login_url, params={"redirect_uri": redirect_uri}, timeout=30.0)
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, dict):
        raise ValueError("OIDC login endpoint returned an invalid response")
    authorization_url = data.get("authorization_url")
    state = data.get("state")
    if not isinstance(authorization_url, str) or not isinstance(state, str):
        raise ValueError("OIDC login response is missing authorization_url or state")
    if server is not None:
        server.expected_state = state
    webbrowser.open(authorization_url)
    return authorization_url, state


def _is_jwt(token: str) -> bool:
    """Check if token is a JWT (3 base64url parts separated by dots)."""
    parts = token.split(".")
    return len(parts) == 3 and all(p for p in parts)


@app.command("login")
def login(
    base_url: str | None = typer.Option(
        None, "--url", "-u", help="Base URL of the Value Fabric API"
    ),
    tenant: str | None = typer.Option(None, "--tenant", "-t", help="Tenant ID for OIDC login"),
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
        base_url = Prompt.ask(
            "Base URL",
            default=config.get("profiles", {})
            .get("default", {})
            .get("base_url", "https://api.valuefabric.io"),
        )

    assert base_url is not None
    api_key = Prompt.ask("API Key", password=True)

    try:
        from valuefabric import ValueFabricClient

        client = ValueFabricClient(base_url=base_url, api_key=api_key)
        health = client.health()
        rich_print("[green]✓ Authenticated successfully[/green]")
        rich_print(f"[dim]Server version: {health.version}[/dim]")
    except Exception as e:
        rich_print(f"[red]✗ Authentication failed: {e}[/red]")
        raise typer.Exit(1) from None

    config.setdefault("profiles", {}).setdefault("default", {})["base_url"] = base_url
    config["profiles"]["default"]["api_key"] = api_key
    _save_config(config)
    rich_print(f"[green]Credentials saved to {CONFIG_FILE}[/green]")


def _login_oidc(base_url: str | None, tenant: str | None) -> None:
    """Authenticate using server-owned OIDC with a local loopback callback."""
    config = _load_config()

    if not base_url:
        base_url = Prompt.ask(
            "Base URL",
            default=config.get("profiles", {})
            .get("default", {})
            .get("base_url", "https://api.valuefabric.io"),
        )

    if not tenant:
        tenant = Prompt.ask("Tenant ID")
    assert base_url is not None
    assert tenant is not None

    # Fail closed before opening the browser if the loopback port is unavailable.
    # Opening with a local redirect_uri when bind failed could leak the auth code
    # to whatever else is listening on that port.
    try:
        server = TokenServer((LOCAL_CALLBACK_HOST, LOCAL_CALLBACK_PORT), CallbackHandler)
        server.timeout = 1
    except OSError as e:
        rich_print(
            f"[red]Failed to bind local callback server on "
            f"{LOCAL_CALLBACK_HOST}:{LOCAL_CALLBACK_PORT}: {e}[/red]"
        )
        rich_print(
            "[dim]Free that port and retry, or paste a JWT after a successful browser login.[/dim]"
        )
        token = Prompt.ask("\nPaste the JWT access token", password=True)
        _persist_jwt(config, base_url, token)
        return

    server.oidc_callback_url = urljoin(base_url, "/api/v1/auth/oidc/callback")
    authorization_url = ""
    try:
        rich_print("[dim]Opening browser for authentication...[/dim]")
        authorization_url, state = _begin_oidc_login(base_url, tenant, LOCAL_REDIRECT_URI)
        server.expected_state = state
        token = _wait_for_callback(server)
    except Exception as e:
        rich_print(f"[red]Failed to start OIDC login: {e}[/red]")
        raise typer.Exit(1) from None
    finally:
        server.server_close()

    if token:
        rich_print("[green]✓ Access token captured via local callback[/green]")
    else:
        rich_print("\n[yellow]Automatic callback timed out or failed.[/yellow]")
        if authorization_url:
            rich_print("[yellow]If needed, reopen:[/yellow]")
            rich_print(f"{authorization_url}")
        token = Prompt.ask("\nPaste the JWT access token", password=True)

    _persist_jwt(config, base_url, token)


def _persist_jwt(config: dict[str, Any], base_url: str, token: str) -> None:
    """Validate and persist a JWT access token into the active CLI profile."""
    jwt_token = token if _is_jwt(token) else None
    if not jwt_token:
        rich_print("[red]Failed to obtain authentication token[/red]")
        raise typer.Exit(1) from None

    try:
        from valuefabric import ValueFabricClient

        client = ValueFabricClient(base_url=base_url, jwt_token=jwt_token)
        client.health()
        rich_print("[green]✓ Authenticated successfully[/green]")
    except Exception as e:
        rich_print(f"[red]✗ Token validation failed: {e}[/red]")
        raise typer.Exit(1) from None

    try:
        decoded = jwt.decode(jwt_token, options={"verify_signature": False})
        jwt_expires_at = decoded.get("exp")
    except Exception:
        jwt_expires_at = None

    config.setdefault("profiles", {}).setdefault("default", {})["base_url"] = base_url
    config["profiles"]["default"]["jwt_token"] = jwt_token
    if jwt_expires_at:
        config["profiles"]["default"]["jwt_expires_at"] = jwt_expires_at
    _save_config(config)
    rich_print(f"[green]Credentials saved to {CONFIG_FILE}[/green]")


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

    configured_url = profile_config.get("base_url", "Not set")
    base_url = configured_url if isinstance(configured_url, str) else "Not set"
    rich_print(f"[bold]Base URL:[/bold] {base_url}")

    auth_type = None
    if "jwt_token" in profile_config:
        auth_type = "JWT (OIDC)"
    elif "api_key" in profile_config:
        auth_type = "API Key"

    if auth_type:
        rich_print(f"[bold]Authentication:[/bold] [green]{auth_type}[/green]")

        try:
            from valuefabric import ValueFabricClient

            client = ValueFabricClient(
                base_url=base_url,
                api_key=profile_config.get("api_key"),
                jwt_token=profile_config.get("jwt_token"),
            )
            health = client.health()
            rich_print("[green]✓ Connected to Value Fabric API[/green]")
            rich_print(f"[dim]  Server version: {health.version}[/dim]")
            rich_print(f"[dim]  Status: {health.status}[/dim]")
        except Exception as e:
            rich_print(f"[red]✗ Connection failed: {e}[/red]")
    else:
        rich_print("[bold]Authentication:[/bold] [red]Not configured[/red]")
        rich_print("[dim]Run 'vf auth login' to authenticate[/dim]")
