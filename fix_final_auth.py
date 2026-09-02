import sys

def modify_auth():
    filepath = "src/valuefabric/cli/auth.py"
    with open(filepath, "r") as f:
        content = f.read()

    # Apply the same diff but be very careful about not doing anything wild.
    new_imports = """
import http.server
import time
import typing
from urllib.parse import parse_qs, urlencode, urljoin, urlparse, urlunparse
"""
    content = content.replace("from urllib.parse import urlencode, urljoin, urlparse, urlunparse", new_imports)

    server_code = """
class TokenServer(http.server.HTTPServer):
    captured_token: str | None = None


class CallbackHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)
        self.server.captured_token = (  # type: ignore[attr-defined]
            qs.get("code", [None])[0] or qs.get("token", [None])[0] or qs.get("jwt", [None])[0]
        )

        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(
            b"<html><body><h1>Authentication Successful</h1>"
            b"<p>You can close this window and return to the CLI.</p></body></html>"
        )

    def log_message(self, format: str, *args: typing.Any) -> None:
        pass


def _wait_for_callback(server: TokenServer, timeout: int = 60) -> str | None:
    try:
        start_time = time.time()
        while server.captured_token is None:
            if time.time() - start_time > timeout:
                return None
            server.handle_request()
        return server.captured_token
    except Exception as e:
        rich_print(f"[dim]Failed to start local callback server: {e}[/dim]")
        return None

"""
    # Insert server_code after PKCE_STATE_FILE = CONFIG_DIR / ".pkce_state"
    target = "PKCE_STATE_FILE = CONFIG_DIR / \".pkce_state\"\n"
    content = content.replace(target, target + "\n" + server_code)

    # modify _login_oidc to change redirect_uri
    content = content.replace('"redirect_uri": f"{base_url}/auth/callback",', '"redirect_uri": "http://localhost:8080/callback",')

    # replace TODO part
    search = """    # TODO(VF-SDK-AUTH-DEBT-001): Implement local callback server for automated token capture
    # For now, user manually copies token
    rich_print("\\n[yellow]If browser didn't open, visit:[/yellow]")
    rich_print(f"{full_url}")

    # Manual token entry fallback
    token = Prompt.ask(
        "\\nPaste the authorization code or JWT token from the callback", password=True
    )"""

    replace = """    rich_print("[dim]Opening browser for authentication...[/dim]")

    # Start the server before opening the browser to avoid race conditions
    try:
        server = TokenServer(("127.0.0.1", 8080), CallbackHandler)
        server.timeout = 1
    except Exception as e:
        rich_print(f"[dim]Failed to bind local callback server: {e}[/dim]")
        server = None

    webbrowser.open(full_url)

    # Wait for callback
    token = None
    if server:
        token = _wait_for_callback(server)
        server.server_close()

    if token:
        rich_print("[green]✓ Token captured automatically[/green]")
    else:
        # Manual token entry fallback
        rich_print("\\n[yellow]If browser didn't open or callback failed, visit:[/yellow]")
        rich_print(f"{full_url}")
        token = Prompt.ask(
            "\\nPaste the authorization code or JWT token from the callback", password=True
        )"""

    # We also need to remove the original opening browser block because we merged it into our replace block
    content = content.replace("""    rich_print("[dim]Opening browser for authentication...[/dim]")
    webbrowser.open(full_url)

""", "")
    content = content.replace(search, replace)

    with open(filepath, "w") as f:
        f.write(content)

modify_auth()
