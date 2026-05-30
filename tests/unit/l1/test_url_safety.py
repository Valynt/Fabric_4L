"""Unit tests for Layer 1 URL safety validation (P0-004)."""

from __future__ import annotations

import pytest

from layer1_ingestion.compliance.url_safety import (
    URLSafetyError,
    URLSafetyResult,
    _is_blocked_ip,
    validate_url_safety,
)

pytestmark = [pytest.mark.unit]


class TestURLSafetyBlockedIPs:
    """Internal IP ranges must be blocked for SSRF protection."""

    @pytest.mark.parametrize(
        "ip,expected",
        [
            ("127.0.0.1", True),
            ("::1", True),
            ("10.0.0.1", True),
            ("192.168.1.1", True),
            ("169.254.1.1", True),
            ("224.0.0.1", True),
            ("0.0.0.0", True),
            ("8.8.8.8", False),
            ("1.1.1.1", False),
        ],
    )
    def test_is_blocked_ip(self, ip: str, expected: bool) -> None:
        assert _is_blocked_ip(ip) is expected


class TestURLSafetyValidation:
    """URL safety gate rejects unsafe URLs and accepts safe ones."""

    def test_rejects_file_scheme(self) -> None:
        with pytest.raises(URLSafetyError) as exc_info:
            validate_url_safety("file:///etc/passwd")
        assert exc_info.value.reason_code == "SCHEME_BLOCKED"

    def test_rejects_ftp_scheme(self) -> None:
        with pytest.raises(URLSafetyError) as exc_info:
            validate_url_safety("ftp://example.com")
        assert exc_info.value.reason_code == "SCHEME_BLOCKED"

    def test_rejects_blocked_port(self) -> None:
        with pytest.raises(URLSafetyError) as exc_info:
            validate_url_safety("http://example.com:8080", allowed_ports={80, 443})
        assert exc_info.value.reason_code == "PORT_BLOCKED"

    def test_rejects_domain_not_in_allowlist(self) -> None:
        with pytest.raises(URLSafetyError) as exc_info:
            validate_url_safety(
                "https://evil.com",
                allowlist_domains=["trusted.com"],
            )
        assert exc_info.value.reason_code == "DOMAIN_NOT_ALLOWLISTED"

    def test_accepts_allowlist_domain(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "layer1_ingestion.compliance.url_safety._resolve_ips",
            lambda hostname: ("1.1.1.1",),
        )
        result = validate_url_safety(
            "https://app.trusted.com/path",
            allowlist_domains=["trusted.com"],
        )
        assert isinstance(result, URLSafetyResult)
        assert result.hostname == "app.trusted.com"

    def test_accepts_allowlist_parent_domain(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "layer1_ingestion.compliance.url_safety._resolve_ips",
            lambda hostname: ("1.1.1.1",),
        )
        result = validate_url_safety(
            "https://sub.trusted.com/path",
            allowlist_domains=["trusted.com"],
        )
        assert isinstance(result, URLSafetyResult)
        assert result.hostname == "sub.trusted.com"

    def test_normalizes_trailing_dot(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "layer1_ingestion.compliance.url_safety._resolve_ips",
            lambda hostname: ("1.1.1.1",),
        )
        result = validate_url_safety(
            "https://example.com./path",
        )
        assert result.hostname == "example.com"

    def test_defaults_to_https_port_443(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "layer1_ingestion.compliance.url_safety._resolve_ips",
            lambda hostname: ("1.1.1.1",),
        )
        result = validate_url_safety("https://example.com/path")
        assert result.port == 443
        assert result.scheme == "https"

    def test_defaults_to_http_port_80(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "layer1_ingestion.compliance.url_safety._resolve_ips",
            lambda hostname: ("1.1.1.1",),
        )
        result = validate_url_safety("http://example.com/path")
        assert result.port == 80
        assert result.scheme == "http"

    def test_explicit_port_preserved(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "layer1_ingestion.compliance.url_safety._resolve_ips",
            lambda hostname: ("1.1.1.1",),
        )
        result = validate_url_safety("https://example.com:8443/path", allowed_ports={8443})
        assert result.port == 8443

    def test_returns_resolved_ips(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "layer1_ingestion.compliance.url_safety._resolve_ips",
            lambda hostname: ("1.1.1.1", "2.2.2.2"),
        )
        result = validate_url_safety("https://example.com")
        assert len(result.resolved_ips) > 0

    def test_raises_on_empty_scheme(self) -> None:
        with pytest.raises(URLSafetyError) as exc_info:
            validate_url_safety("://no-scheme")
        assert exc_info.value.reason_code == "SCHEME_BLOCKED"

    def test_raises_on_empty_hostname(self) -> None:
        with pytest.raises(URLSafetyError) as exc_info:
            validate_url_safety("http:///path")
        assert exc_info.value.reason_code == "MALFORMED_URL"

    def test_result_is_frozen_dataclass(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "layer1_ingestion.compliance.url_safety._resolve_ips",
            lambda hostname: ("1.1.1.1",),
        )
        result = validate_url_safety("https://example.com")
        with pytest.raises(AttributeError):
            result.port = 9999


class TestURLSafetyResult:
    """URLSafetyResult exposes expected fields."""

    def test_result_attributes(self) -> None:
        result = validate_url_safety("https://example.com:8443/api", allowed_ports={8443})
        assert result.scheme == "https"
        assert result.port == 8443
        assert result.hostname == "example.com"
        assert result.normalized_url == "https://example.com:8443/api"
