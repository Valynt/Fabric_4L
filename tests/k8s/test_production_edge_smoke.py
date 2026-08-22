from __future__ import annotations

import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "ci"))

from production_edge_smoke import probe  # noqa: E402


class _Handler(BaseHTTPRequestHandler):
    responses: dict[str, tuple[int, str, bytes]] = {}
    last_headers: dict[str, str] = {}

    def do_GET(self) -> None:
        type(self).last_headers = dict(self.headers.items())
        status, content_type, body = self.responses[self.path]
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        pass


@pytest.fixture
def server():
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{httpd.server_port}"
    finally:
        httpd.shutdown()
        thread.join()


def _response(path: str, status: int, content_type: str, body: object) -> None:
    encoded = json.dumps(body).encode() if not isinstance(body, bytes) else body
    _Handler.responses = {path: (status, content_type, encoded)}


@pytest.mark.parametrize("status", [200, 401, 403, 404])
def test_accepts_structured_gateway_json(server: str, status: int) -> None:
    _response(
        "/api/v1/accounts/missing", status, "application/json", {"detail": "expected"}
    )

    result = probe(server, "/api/v1/accounts/missing")

    assert result.status == status


def test_sends_optional_edge_credentials(server: str) -> None:
    _response("/api/v1/auth/health", 200, "application/json", {"status": "ok"})

    probe(
        server,
        "/api/v1/auth/health",
        authorization="Bearer smoke-token",
        cookie="session=smoke-cookie",
    )

    assert _Handler.last_headers["Authorization"] == "Bearer smoke-token"
    assert _Handler.last_headers["Cookie"] == "session=smoke-cookie"


def test_rejects_frontend_html(server: str) -> None:
    _response("/api/v1/auth/health", 200, "text/html", b"<!doctype html><html></html>")

    with pytest.raises(RuntimeError, match="expected JSON Content-Type"):
        probe(server, "/api/v1/auth/health")


def test_rejects_json_content_type_with_html_body(server: str) -> None:
    _response("/api/v1/auth/health", 200, "application/json", b"<!doctype html>")

    with pytest.raises(RuntimeError, match="frontend HTML"):
        probe(server, "/api/v1/auth/health")


def test_rejects_malformed_json(server: str) -> None:
    _response("/api/v1/auth/health", 404, "application/json", b"not-json")

    with pytest.raises(RuntimeError, match="not valid JSON"):
        probe(server, "/api/v1/auth/health")
