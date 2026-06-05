"""Functional regression coverage for Layer 1 cloud metadata SSRF controls."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from layer1_ingestion.api.main import ExecuteTargetRequest
from layer1_ingestion.compliance.url_safety import URLSafetyError, validate_url_safety


@pytest.mark.security
@pytest.mark.parametrize(
    ("url", "resolved_ip"),
    [
        ("http://169.254.169.254/latest/meta-data/", "169.254.169.254"),
        ("http://169.254.170.2/v2/metadata", "169.254.170.2"),
        ("http://100.100.100.200/latest/meta-data/", "100.100.100.200"),
        ("http://192.0.0.254/opc/v1/instance/", "192.0.0.254"),
        ("http://[fd00:ec2::254]/latest/meta-data/", "fd00:ec2::254"),
        ("http://metadata.google.internal/computeMetadata/v1/", "169.254.169.254"),
        ("http://metadata.internal/secret", "169.254.169.254"),
    ],
)
def test_l1_url_safety_blocks_cloud_metadata_endpoints(
    monkeypatch: pytest.MonkeyPatch,
    url: str,
    resolved_ip: str,
) -> None:
    monkeypatch.setattr(
        "layer1_ingestion.compliance.url_safety._resolve_ips",
        lambda _hostname: (resolved_ip,),
    )

    with pytest.raises(URLSafetyError) as exc_info:
        validate_url_safety(url)

    assert exc_info.value.reason_code == "IP_RANGE_BLOCKED"


@pytest.mark.security
@pytest.mark.parametrize(
    "callback_url",
    [
        "https://metadata.google.internal/computeMetadata/v1/",
        "https://metadata.internal/secret",
        "https://service.metadata/secret",
    ],
)
def test_l1_callback_url_rejects_cloud_metadata_hostnames(callback_url: str) -> None:
    with pytest.raises(ValidationError, match="cloud metadata"):
        ExecuteTargetRequest(callback_url=callback_url)


@pytest.mark.security
def test_l1_url_safety_allows_public_https_when_dns_resolves_publicly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "layer1_ingestion.compliance.url_safety._resolve_ips",
        lambda _hostname: ("1.1.1.1",),
    )

    result = validate_url_safety("https://example.com/webhook")

    assert result.hostname == "example.com"
    assert result.resolved_ips == ("1.1.1.1",)
