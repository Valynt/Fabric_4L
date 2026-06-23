"""P0-005: Rate limiter must not trust spoofable IP headers.

Verifies that _get_client_key prioritises authenticated identity over
X-Forwarded-For / X-Real-IP, and that IP-based fallbacks are gated by
TRUSTED_PROXY_COUNT.
"""

import os
from unittest.mock import MagicMock

import pytest
from fastapi import Request

from src.api.rate_limiter import RateLimiter


class FakeClient:
    def __init__(self, host: str):
        self.host = host


def _make_request(
    *,
    client_host: str = "203.0.113.5",
    headers: dict | None = None,
    state_attrs: dict | None = None,
) -> Request:
    """Build a minimal FastAPI Request mock."""
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/v1/search",
        "headers": [
            (k.lower().encode(), v.encode()) for k, v in (headers or {}).items()
        ],
        "client": (client_host, 12345),
    }
    request = Request(scope)
    request._cookies = {}  # type: ignore[attr-defined]
    for key, value in (state_attrs or {}).items():
        setattr(request.state, key, value)
    return request


class FakeAPIKey:
    key_id = "ak_test_123"


@pytest.fixture
def limiter():
    return RateLimiter()


class TestGetClientKeyAuthenticatedIdentity:
    """Authenticated identity must always win over IP headers."""

    def test_uses_api_key_id_when_present(self, limiter: RateLimiter):
        req = _make_request(
            headers={"X-Forwarded-For": "1.2.3.4"},
            state_attrs={"authenticated_api_key": FakeAPIKey()},
        )
        assert limiter._get_client_key(req) == "key:ak_test_123"

    def test_uses_tenant_id_when_no_api_key(self, limiter: RateLimiter):
        req = _make_request(
            headers={"X-Forwarded-For": "1.2.3.4"},
            state_attrs={"tenant_id": "tenant-abc-123"},
        )
        assert limiter._get_client_key(req) == "tenant:tenant-abc-123"

    def test_uses_governance_context_tenant_id(self, limiter: RateLimiter):
        gov_ctx = MagicMock()
        gov_ctx.tenant_id = "gov-tenant-xyz"
        req = _make_request(
            headers={"X-Forwarded-For": "1.2.3.4"},
            state_attrs={"governance_context": gov_ctx},
        )
        assert limiter._get_client_key(req) == "tenant:gov-tenant-xyz"

    def test_api_key_wins_over_tenant_id(self, limiter: RateLimiter):
        req = _make_request(
            headers={"X-Forwarded-For": "1.2.3.4"},
            state_attrs={
                "authenticated_api_key": FakeAPIKey(),
                "tenant_id": "tenant-abc-123",
            },
        )
        assert limiter._get_client_key(req) == "key:ak_test_123"


class TestGetClientKeyIpFallback:
    """IP-based fallback must be gated by TRUSTED_PROXY_COUNT."""

    def test_x_forwarded_for_ignored_without_trusted_proxy_count(self, limiter: RateLimiter):
        """Without TRUSTED_PROXY_COUNT, raw X-Forwarded-For is not trusted."""
        req = _make_request(
            client_host="203.0.113.5",
            headers={"X-Forwarded-For": "1.2.3.4, 5.6.7.8"},
        )
        assert limiter._get_client_key(req) == "203.0.113.5"

    def test_x_real_ip_ignored_without_trusted_proxy_count(self, limiter: RateLimiter):
        req = _make_request(
            client_host="203.0.113.5",
            headers={"X-Real-IP": "1.2.3.4"},
        )
        assert limiter._get_client_key(req) == "203.0.113.5"

    def test_trusted_proxy_count_parses_from_right(self, limiter: RateLimiter, monkeypatch):
        """With TRUSTED_PROXY_COUNT=2, take 2nd from last IP."""
        monkeypatch.setenv("TRUSTED_PROXY_COUNT", "2")
        req = _make_request(
            headers={"X-Forwarded-For": "1.2.3.4, 198.51.100.10, 203.0.113.5"},
        )
        assert limiter._get_client_key(req) == "198.51.100.10"

    def test_trusted_proxy_count_one_takes_last(self, limiter: RateLimiter, monkeypatch):
        monkeypatch.setenv("TRUSTED_PROXY_COUNT", "1")
        req = _make_request(
            headers={"X-Forwarded-For": "1.2.3.4, 203.0.113.5"},
        )
        assert limiter._get_client_key(req) == "203.0.113.5"

    def test_trusted_proxy_count_exceeds_list_length(self, limiter: RateLimiter, monkeypatch):
        """If not enough IPs, fall through to X-Real-IP then client.host."""
        monkeypatch.setenv("TRUSTED_PROXY_COUNT", "5")
        req = _make_request(
            client_host="203.0.113.5",
            headers={"X-Forwarded-For": "1.2.3.4"},
        )
        assert limiter._get_client_key(req) == "203.0.113.5"

    def test_trusted_proxy_count_falls_back_to_x_real_ip(self, limiter: RateLimiter, monkeypatch):
        monkeypatch.setenv("TRUSTED_PROXY_COUNT", "2")
        req = _make_request(
            headers={
                "X-Forwarded-For": "1.2.3.4",
                "X-Real-IP": "198.51.100.10",
            },
        )
        assert limiter._get_client_key(req) == "198.51.100.10"

    def test_invalid_trusted_proxy_count_treated_as_zero(self, limiter: RateLimiter, monkeypatch):
        monkeypatch.setenv("TRUSTED_PROXY_COUNT", "not_a_number")
        req = _make_request(
            client_host="203.0.113.5",
            headers={"X-Forwarded-For": "1.2.3.4"},
        )
        assert limiter._get_client_key(req) == "203.0.113.5"

    def test_empty_trusted_proxy_count_treated_as_zero(self, limiter: RateLimiter, monkeypatch):
        monkeypatch.setenv("TRUSTED_PROXY_COUNT", "")
        req = _make_request(
            client_host="203.0.113.5",
            headers={"X-Forwarded-For": "1.2.3.4"},
        )
        assert limiter._get_client_key(req) == "203.0.113.5"

    def test_unknown_when_no_client(self, limiter: RateLimiter):
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/v1/search",
            "headers": [],
            "client": None,
        }
        request = Request(scope)
        request._cookies = {}  # type: ignore[attr-defined]
        assert limiter._get_client_key(request) == "unknown"


class TestGetClientKeySpoofingResistance:
    """Explicit spoofing scenarios must fail."""

    def test_spoofed_x_forwarded_for_ignored_without_trusted_proxy(self, limiter: RateLimiter):
        req = _make_request(
            client_host="203.0.113.5",
            headers={"X-Forwarded-For": "10.0.0.1, 192.168.1.1"},
        )
        # Without TRUSTED_PROXY_COUNT, falls back to direct client host
        assert limiter._get_client_key(req) == "203.0.113.5"

    def test_spoofed_x_forwarded_for_with_trusted_proxy_parses_correctly(self, limiter: RateLimiter, monkeypatch):
        """Attacker sends '1.2.3.4, 10.0.0.1' with TRUSTED_PROXY_COUNT=1.

        The last IP (10.0.0.1) is the proxy's view of the client; the first
        IP (1.2.3.4) is attacker-spoofed and must be ignored.
        """
        monkeypatch.setenv("TRUSTED_PROXY_COUNT", "1")
        req = _make_request(
            headers={"X-Forwarded-For": "1.2.3.4, 10.0.0.1"},
        )
        assert limiter._get_client_key(req) == "10.0.0.1"

    def test_spoofed_x_real_ip_ignored_without_trusted_proxy(self, limiter: RateLimiter):
        req = _make_request(
            client_host="203.0.113.5",
            headers={"X-Real-IP": "10.0.0.1"},
        )
        assert limiter._get_client_key(req) == "203.0.113.5"
