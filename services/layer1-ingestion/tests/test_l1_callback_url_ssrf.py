"""P0-003 acceptance test: L1 callback_url SSRF protection.

Validates that ExecuteTargetRequest blocks SSRF-prone callback URLs.
Uses static source analysis to avoid heavy import chain.
"""

from __future__ import annotations

from pathlib import Path


def _load_main_source() -> str:
    """Read the L1 main.py source file."""
    service_root = Path(__file__).resolve().parents[1] / "src"
    main_file = service_root / "api" / "main.py"
    return main_file.read_text(encoding="utf-8", errors="ignore")


def test_callback_url_has_ssrf_validator():
    """ExecuteTargetRequest must have a field_validator for callback_url."""
    content = _load_main_source()
    assert "@field_validator(\"callback_url\")" in content, (
        "Expected @field_validator('callback_url') in ExecuteTargetRequest"
    )


def test_callback_url_blocks_private_ips():
    """Validator must reject private IP ranges."""
    content = _load_main_source()
    assert "ipaddress.ip_address" in content, "Expected ipaddress check for SSRF"
    assert "is_private" in content, "Expected is_private check"
    assert "is_loopback" in content, "Expected is_loopback check"


def test_callback_url_blocks_localhost():
    """Validator must reject localhost hostnames."""
    content = _load_main_source()
    assert '"localhost"' in content, "Expected localhost rejection"


def test_callback_url_requires_https():
    """Validator must require HTTPS scheme."""
    content = _load_main_source()
    assert 'parsed.scheme != "https"' in content or 'scheme != "https"' in content, (
        "Expected HTTPS scheme enforcement"
    )
