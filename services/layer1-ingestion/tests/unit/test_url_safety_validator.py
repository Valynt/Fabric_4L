import socket

import pytest

from layer1_ingestion.compliance.url_safety import URLSafetyError, enforce_rebinding_protection, validate_url_safety


def test_rejects_malformed_url():
    with pytest.raises(URLSafetyError) as exc:
        validate_url_safety("not a url")
    assert exc.value.reason_code == "SCHEME_BLOCKED"


def test_rejects_private_ip(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *args, **kwargs: [(None, None, None, None, ("10.0.0.2", 0))])
    with pytest.raises(URLSafetyError) as exc:
        validate_url_safety("https://example.com")
    assert exc.value.reason_code == "IP_RANGE_BLOCKED"


def test_domain_allowlist(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *args, **kwargs: [(None, None, None, None, ("93.184.216.34", 0))])
    with pytest.raises(URLSafetyError) as exc:
        validate_url_safety("https://example.com", allowlist_domains=["allowed.com"])
    assert exc.value.reason_code == "DOMAIN_NOT_ALLOWLISTED"


def test_dns_rebinding_detection(monkeypatch):
    responses = [
        [(None, None, None, None, ("93.184.216.34", 0))],
        [(None, None, None, None, ("93.184.216.99", 0))],
    ]
    monkeypatch.setattr(socket, "getaddrinfo", lambda *args, **kwargs: responses.pop(0))
    result = validate_url_safety("https://example.com")
    with pytest.raises(URLSafetyError) as exc:
        enforce_rebinding_protection(result.normalized_url, result.resolved_ips)
    assert exc.value.reason_code == "DNS_REBINDING_DETECTED"
