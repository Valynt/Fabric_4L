import socket

import pytest

from src.compliance.url_safety import URLSafetyError, validate_url_safety


@pytest.mark.security
def test_blocks_localhost(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *args, **kwargs: [(None, None, None, None, ("127.0.0.1", 0))])
    with pytest.raises(URLSafetyError) as exc:
        validate_url_safety("http://localhost")
    assert exc.value.reason_code == "IP_RANGE_BLOCKED"


@pytest.mark.security
def test_blocks_metadata_ip(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *args, **kwargs: [(None, None, None, None, ("169.254.169.254", 0))])
    with pytest.raises(URLSafetyError) as exc:
        validate_url_safety("http://metadata.google.internal")
    assert exc.value.reason_code == "IP_RANGE_BLOCKED"


@pytest.mark.security
def test_blocks_ipv6_loopback(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *args, **kwargs: [(None, None, None, None, ("::1", 0))])
    with pytest.raises(URLSafetyError) as exc:
        validate_url_safety("https://example.com")
    assert exc.value.reason_code == "IP_RANGE_BLOCKED"
