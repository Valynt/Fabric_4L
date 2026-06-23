import pytest
from fastapi import Depends, FastAPI, Request
from fastapi.testclient import TestClient
from value_fabric.shared.rate_limiting.ip_limiter import (
    IPRateLimitDependency,
    get_client_ip,
)


@pytest.fixture
def app_with_limit():
    app = FastAPI()
    limiter = IPRateLimitDependency(requests_per_minute=2)

    @app.post("/clerk")
    async def clerk(request: Request, _=Depends(limiter)):
        return {"ok": True}

    return app


def test_client_ip_prefers_rightmost_non_private_x_forwarded_for():
    request = Request(
        scope={
            "type": "http",
            "headers": [(b"x-forwarded-for", b"203.0.113.1, 10.0.0.1, 192.168.1.1")],
            "client": ("127.0.0.1", 12345),
        }
    )
    assert get_client_ip(request) == "203.0.113.1"


def test_client_ip_ignores_leftmost_spoofed_x_forwarded_for_values(app_with_limit):
    """Many different left-most XFF values must not bypass the rate limit.

    The rate limiter keys on the right-most untrusted IP, so a client that
    appends arbitrary left-most entries still shares the same bucket as the
    real client IP.
    """
    client = TestClient(app_with_limit)
    base_ip = "1.2.3.100"
    for spoofed in ["9.9.9.9", "8.8.8.8"]:
        r = client.post(
            "/clerk",
            headers={"X-Forwarded-For": f"{spoofed}, {base_ip}"},
        )
        assert r.status_code == 200

    # Third request from the same real IP is rate limited, even though the
    # left-most spoofed value keeps changing.
    r = client.post(
        "/clerk",
        headers={"X-Forwarded-For": f"7.7.7.7, {base_ip}"},
    )
    assert r.status_code == 429


def test_client_ip_returns_rightmost_untrusted_ip_with_trusted_proxy_hops():
    request = Request(
        scope={
            "type": "http",
            "headers": [(b"x-forwarded-for", b"203.0.113.1, 1.2.3.4, 192.168.1.1")],
            "client": ("127.0.0.1", 12345),
        }
    )
    # Strip the trusted proxy 192.168.1.1, then pick the right-most
    # remaining non-private IP.
    assert get_client_ip(request, trusted_proxy_hops=1) == "1.2.3.4"


def test_client_ip_skips_private_and_malformed_ips():
    request = Request(
        scope={
            "type": "http",
            "headers": [
                (
                    b"x-forwarded-for",
                    b"203.0.113.1, not-an-ip, 10.0.0.1, 192.168.1.1",
                )
            ],
            "client": ("127.0.0.1", 12345),
        }
    )
    assert get_client_ip(request, trusted_proxy_hops=1) == "203.0.113.1"


def test_client_ip_falls_back_to_request_client_host():
    request = Request(
        scope={
            "type": "http",
            "headers": [],
            "client": ("1.2.3.4", 12345),
        }
    )
    assert get_client_ip(request) == "1.2.3.4"


def test_rate_limit_allows_under_threshold(app_with_limit):
    client = TestClient(app_with_limit)
    for _ in range(2):
        r = client.post("/clerk", headers={"X-Forwarded-For": "1.2.3.4"})
        assert r.status_code == 200


def test_rate_limit_blocks_over_threshold(app_with_limit):
    client = TestClient(app_with_limit)
    for _ in range(2):
        client.post("/clerk", headers={"X-Forwarded-For": "1.2.3.4"})
    r = client.post("/clerk", headers={"X-Forwarded-For": "1.2.3.4"})
    assert r.status_code == 429


def test_rate_limit_tracks_different_ips_separately(app_with_limit):
    client = TestClient(app_with_limit)
    for ip in ["1.2.3.4", "5.6.7.8"]:
        r = client.post("/clerk", headers={"X-Forwarded-For": ip})
        assert r.status_code == 200
