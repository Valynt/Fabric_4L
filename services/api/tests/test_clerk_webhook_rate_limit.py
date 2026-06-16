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


def test_client_ip_prefers_first_non_private_x_forwarded_for():
    request = Request(scope={
        "type": "http",
        "headers": [(b"x-forwarded-for", b"203.0.113.1, 10.0.0.1, 192.168.1.1")],
        "client": ("127.0.0.1", 12345),
    })
    assert get_client_ip(request) == "203.0.113.1"


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
