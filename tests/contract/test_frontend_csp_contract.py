"""Static contract test for frontend Content-Security-Policy in index.html.

Ensures that the CSP meta tag in apps/web/index.html allows the third-party
domains required by Clerk authentication, Google Fonts, and Vite hot-reload.
This test runs without starting any services.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
INDEX_HTML = REPO_ROOT / "apps" / "web" / "index.html"

# Required CSP directives and the values that must be present in each.
CSP_REQUIREMENTS: dict[str, set[str]] = {
    "script-src": {
        "'self'",
        "'unsafe-inline'",
        "https://*.clerk.accounts.dev",
        # Clerk Smart CAPTCHA (Cloudflare Turnstile) loads its challenge script
        # from this origin; without it the CAPTCHA fails to load on sign-up.
        "https://challenges.cloudflare.com",
        "blob:",
    },
    "worker-src": {"'self'", "blob:"},
    "style-src": {"'self'", "'unsafe-inline'", "https://fonts.googleapis.com"},
    "connect-src": {
        "'self'",
        "https://*.fabric4l.io",
        "https://*.clerk.accounts.dev",
        "https://challenges.cloudflare.com",
        "https://clerk-telemetry.com",
    },
    "font-src": {"'self'", "https://fonts.gstatic.com"},
    "img-src": {"'self'", "data:", "https://*.clerk.accounts.dev", "https://img.clerk.com"},
    # Clerk Smart CAPTCHA renders the Turnstile widget inside an iframe served
    # from challenges.cloudflare.com, so it must be an allowed frame source.
    "frame-src": {
        "'self'",
        "https://*.clerk.accounts.dev",
        "https://challenges.cloudflare.com",
    },
}


def _extract_csp_meta(content: str) -> str:
    # Match content="..." where the value may contain single quotes.
    # We capture everything up to the closing double-quote.
    match = re.search(
        r'<meta[^>]+http-equiv=["\']Content-Security-Policy["\'][^>]+content="([^"]*)"',
        content,
        re.IGNORECASE,
    )
    if match:
        return match.group(1)
    # Try reversed attribute order
    match = re.search(
        r'<meta[^>]+content="([^"]*)"[^>]+http-equiv=["\']Content-Security-Policy["\']',
        content,
        re.IGNORECASE,
    )
    if match:
        return match.group(1)
    pytest.fail("CSP meta tag not found in apps/web/index.html")


def _parse_csp_directives(csp: str) -> dict[str, set[str]]:
    directives: dict[str, set[str]] = {}
    # Split on semicolons, respecting that directives themselves are space-separated
    for part in csp.split(";"):
        part = part.strip()
        if not part:
            continue
        tokens = part.split()
        directive = tokens[0]
        values = set(tokens[1:])
        directives[directive] = values
    return directives


@pytest.fixture
def csp_directives() -> dict[str, set[str]]:
    content = INDEX_HTML.read_text(encoding="utf-8")
    csp = _extract_csp_meta(content)
    return _parse_csp_directives(csp)


@pytest.mark.contract_static_no_service
class TestFrontendCspContract:
    def test_csp_meta_tag_exists(self, csp_directives: dict[str, set[str]]) -> None:
        assert "default-src" in csp_directives, "default-src directive is required"

    @pytest.mark.parametrize("directive,required_values", CSP_REQUIREMENTS.items())
    def test_csp_directive_contains_required_values(
        self,
        csp_directives: dict[str, set[str]],
        directive: str,
        required_values: set[str],
    ) -> None:
        assert directive in csp_directives, f"{directive} directive is missing"
        actual_values = csp_directives[directive]
        missing = required_values - actual_values
        assert not missing, f"{directive} missing values: {missing}"

    def test_frame_src_is_not_none(self, csp_directives: dict[str, set[str]]) -> None:
        # frame-src 'none' would break Clerk OAuth popups
        values = csp_directives.get("frame-src", set())
        assert "'none'" not in values, "frame-src must not be 'none'"
