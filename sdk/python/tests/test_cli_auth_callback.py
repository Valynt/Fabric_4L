"""Regression tests for the CLI's server-owned OIDC callback flow."""

from __future__ import annotations

import threading
from http.client import HTTPConnection
from unittest.mock import Mock, patch

from valuefabric.cli.auth import CallbackHandler, TokenServer, _begin_oidc_login


def _request(server: TokenServer, path: str) -> tuple[int, bytes]:
    thread = threading.Thread(target=server.handle_request)
    thread.start()
    connection = HTTPConnection("127.0.0.1", server.server_port)
    connection.request("GET", path)
    response = connection.getresponse()
    body = response.read()
    thread.join(timeout=2)
    connection.close()
    return response.status, body


def test_begin_oidc_login_opens_server_returned_authorization_url() -> None:
    response = Mock()
    response.json.return_value = {
        "authorization_url": "https://idp.example/authorize?state=server-state",
        "state": "server-state",
    }
    response.raise_for_status.return_value = None

    with (
        patch("valuefabric.cli.auth.httpx.get", return_value=response) as get,
        patch("valuefabric.cli.auth.webbrowser.open") as open_browser,
    ):
        authorization_url, state = _begin_oidc_login(
            "https://api.example", "acme", "http://localhost:8080/callback"
        )

    assert authorization_url == "https://idp.example/authorize?state=server-state"
    assert state == "server-state"
    open_browser.assert_called_once_with("https://idp.example/authorize?state=server-state")
    get.assert_called_once_with(
        "https://api.example/api/v1/auth/oidc/acme/login",
        params={"redirect_uri": "http://localhost:8080/callback"},
        timeout=30.0,
    )


def test_callback_rejects_wrong_path_and_token_injection() -> None:
    server = TokenServer(("127.0.0.1", 0), CallbackHandler)
    server.expected_state = "expected"
    server.oidc_callback_url = "https://api.example/api/v1/auth/oidc/callback"
    try:
        status, _ = _request(server, "/?jwt=attacker.jwt.token&state=expected")
        assert status == 404
        assert server.captured_token is None
    finally:
        server.server_close()


def test_callback_rejects_mismatched_state_without_exchange() -> None:
    server = TokenServer(("127.0.0.1", 0), CallbackHandler)
    server.expected_state = "expected"
    server.oidc_callback_url = "https://api.example/api/v1/auth/oidc/callback"
    try:
        with patch("valuefabric.cli.auth.httpx.get") as get:
            status, _ = _request(server, "/callback?code=code&state=wrong")
        assert status == 400
        assert server.captured_token is None
        get.assert_not_called()
    finally:
        server.server_close()


def test_callback_exchanges_code_through_server_owned_callback() -> None:
    server = TokenServer(("127.0.0.1", 0), CallbackHandler)
    server.expected_state = "expected"
    server.oidc_callback_url = "https://api.example/api/v1/auth/oidc/callback"
    response = Mock()
    response.json.return_value = {"access_token": "header.payload.signature"}
    response.raise_for_status.return_value = None
    try:
        with patch("valuefabric.cli.auth.httpx.get", return_value=response) as get:
            status, body = _request(server, "/callback?code=auth-code&state=expected")
        assert status == 200
        assert b"Authentication Successful" in body
        assert server.captured_token == "header.payload.signature"
        get.assert_called_once_with(
            "https://api.example/api/v1/auth/oidc/callback",
            params={"code": "auth-code", "state": "expected"},
            timeout=30.0,
        )
    finally:
        server.server_close()
