"""P0-003 acceptance tests: L1 callback_url SSRF protection.

Validates that ExecuteTargetRequest blocks SSRF-prone callback URLs.

These are functional tests that instantiate the Pydantic model directly so that
logical bugs in the validator (e.g. a try/except that silently swallows the
raise) are caught — pure source-analysis tests would not detect such regressions.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

# Ensure the service source is on the path when running from the repo root.
_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from layer1_ingestion.api.main import ExecuteTargetRequest  # noqa: E402, I001


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make(callback_url: str) -> None:
    """Attempt to build an ExecuteTargetRequest with the given callback_url.

    Raises pydantic.ValidationError when the URL is rejected.
    """
    ExecuteTargetRequest(callback_url=callback_url)


# ---------------------------------------------------------------------------
# Allowed URLs
# ---------------------------------------------------------------------------

def test_valid_https_external_url_is_accepted():
    req = ExecuteTargetRequest(callback_url="https://example.com/webhook")
    assert req.callback_url == "https://example.com/webhook"


def test_none_callback_url_is_accepted():
    req = ExecuteTargetRequest(callback_url=None)
    assert req.callback_url is None


# ---------------------------------------------------------------------------
# Scheme enforcement
# ---------------------------------------------------------------------------

def test_http_scheme_rejected():
    with pytest.raises(ValidationError, match="HTTPS scheme"):
        _make("http://example.com/webhook")


def test_ftp_scheme_rejected():
    with pytest.raises(ValidationError, match="HTTPS scheme"):
        _make("ftp://example.com/webhook")


def test_file_scheme_rejected():
    with pytest.raises(ValidationError, match="HTTPS scheme"):
        _make("file:///etc/passwd")


# ---------------------------------------------------------------------------
# Localhost / loopback blocking
# ---------------------------------------------------------------------------

def test_localhost_hostname_rejected():
    with pytest.raises(ValidationError, match="localhost"):
        _make("https://localhost/steal")


def test_127_0_0_1_rejected():
    with pytest.raises(ValidationError, match="localhost"):
        _make("https://127.0.0.1/steal")


def test_ipv6_loopback_rejected():
    with pytest.raises(ValidationError, match="localhost"):
        _make("https://[::1]/steal")


# ---------------------------------------------------------------------------
# Private IP range blocking (the previously broken branch)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("private_url", [
    "https://10.0.0.1/internal",
    "https://10.255.255.255/internal",
    "https://172.16.0.1/internal",
    "https://172.31.255.255/internal",
    "https://192.168.1.1/internal",
    "https://192.168.255.254/internal",
])
def test_private_ip_ranges_rejected(private_url: str):
    with pytest.raises(ValidationError, match="private or reserved"):
        _make(private_url)


def test_link_local_ip_rejected():
    with pytest.raises(ValidationError, match="private or reserved"):
        _make("https://169.254.1.1/not-metadata-but-still-link-local")


def test_unspecified_ip_rejected():
    with pytest.raises(ValidationError, match="localhost"):
        _make("https://0.0.0.0/internal")


# ---------------------------------------------------------------------------
# Cloud metadata endpoint blocking
# ---------------------------------------------------------------------------

def test_aws_metadata_ip_rejected():
    with pytest.raises(ValidationError):
        _make("https://169.254.169.254/latest/meta-data/iam/security-credentials/")


def test_gcp_metadata_hostname_rejected():
    with pytest.raises(ValidationError, match="cloud metadata"):
        _make("https://metadata.google.internal/computeMetadata/v1/")


def test_metadata_internal_hostname_rejected():
    with pytest.raises(ValidationError, match="cloud metadata"):
        _make("https://metadata.internal/secret")


# ---------------------------------------------------------------------------
# Source-analysis guard: ensure the try/except/else structure is present
# (regression guard against reverting to the broken pattern)
# ---------------------------------------------------------------------------

def test_validator_uses_try_except_else_not_bare_pass():
    """The validator must use try/except/else, not the pattern that swallows raises."""
    service_root = Path(__file__).resolve().parents[1] / "src"
    schema_file = (
        service_root
        / "layer1_ingestion"
        / "api"
        / "schemas"
        / "target_schemas.py"
    )
    content = schema_file.read_text(encoding="utf-8", errors="ignore")
    # The broken pattern raises ValueError inside the try block and catches it.
    # The fixed pattern uses else: after except ValueError.
    assert "except ValueError:" in content, "Expected except ValueError in validator"
    # Confirm the raise for private IPs is NOT inside the try block by checking
    # that 'is_private' appears AFTER an 'else:' line (i.e. in the else branch).
    try_pos = content.index("except ValueError:")
    else_pos = content.index("else:", try_pos)
    private_pos = content.index("is_private", else_pos)
    assert private_pos > else_pos, (
        "is_private check must be inside the else: branch, not the try: block. "
        "The validator likely reverted to the broken pattern that swallows the raise."
    )
