"""Regression coverage for Layer 1 callback URL SSRF controls."""

from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
L1_MAIN = REPO_ROOT / "services/layer1-ingestion/src/layer1_ingestion/api/main.py"


def test_l1_ssrf_blocklist_includes_cloud_metadata_endpoints() -> None:
    source = L1_MAIN.read_text(encoding="utf-8")

    for endpoint in (
        "169.254.169.254",
        "169.254.170.2",
        "100.100.100.200",
        "192.0.0.254",
        "fd00:ec2::254",
        "metadata.google.internal",
        "metadata.internal",
    ):
        assert endpoint in source


def test_l1_ssrf_rejects_metadata_tld_patterns() -> None:
    source = L1_MAIN.read_text(encoding="utf-8")

    assert 'endswith(".metadata")' in source
    assert "cloud metadata endpoints" in source

