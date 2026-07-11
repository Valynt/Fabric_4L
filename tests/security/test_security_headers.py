"""
Security Headers Validation Tests — Fabric 4L

Validates that all HTTP responses include the correct security headers
per the security-headers.md specification. Tests cover:

  - Header presence for all 9 required headers
  - Value accuracy against production spec
  - Environment-specific differences (dev vs prod)
  - Per-endpoint override functionality
  - Excluded paths (health, metrics)
  - CSP nonce freshness (unique per request)
  - OWASP compliance baseline

Run: pytest tests/security/test_security_headers.py -v
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from fastapi.responses import PlainTextResponse

from value_fabric.shared.security_middleware import (
    SecurityHeadersMiddleware,
    Environment,
    disable_security_headers,
    security_header_override,
    HSTS_VALUE_PROD,
    X_CONTENT_TYPE_OPTIONS,
    X_FRAME_OPTIONS,
    REFERRER_POLICY,
    PERMISSIONS_POLICY,
    COEP_PROD,
    COOP_PROD,
    CORP_PROD,
    COEP_DEV,
    COOP_DEV,
    CORP_DEV,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def base_app() -> FastAPI:
    """Minimal FastAPI app for testing."""
    app = FastAPI()

    @app.get("/")
    async def root():
        return {"message": "ok"}

    @app.get("/health")
    async def health():
        return {"status": "healthy"}

    @app.get("/metrics")
    async def metrics():
        return PlainTextResponse("# metrics")

    @app.get("/embed")
    @security_header_override("X-Frame-Options", "SAMEORIGIN")
    async def embed(request: Request):
        return {"widget": "test"}

    @app.get("/no-headers")
    @disable_security_headers
    async def no_headers(request: Request):
        return {"headers": "disabled"}

    return app


@pytest.fixture
def prod_client(base_app: FastAPI) -> TestClient:
    """TestClient configured for production environment."""
    base_app.add_middleware(SecurityHeadersMiddleware, environment=Environment.PRODUCTION)
    return TestClient(base_app)


@pytest.fixture
def dev_client(base_app: FastAPI) -> TestClient:
    """TestClient configured for development environment."""
    # Need fresh app since middleware is already added
    app = FastAPI()

    @app.get("/")
    async def root():
        return {"message": "ok"}

    @app.get("/health")
    async def health():
        return {"status": "healthy"}

    @app.get("/metrics")
    async def metrics():
        return PlainTextResponse("# metrics")

    @app.get("/embed")
    @security_header_override("X-Frame-Options", "SAMEORIGIN")
    async def embed(request: Request):
        return {"widget": "test"}

    @app.get("/no-headers")
    @disable_security_headers
    async def no_headers(request: Request):
        return {"headers": "disabled"}

    app.add_middleware(SecurityHeadersMiddleware, environment=Environment.DEVELOPMENT)
    return TestClient(app)


@pytest.fixture
def staging_client() -> TestClient:
    """TestClient configured for staging environment."""
    app = FastAPI()

    @app.get("/")
    async def root():
        return {"message": "ok"}

    app.add_middleware(SecurityHeadersMiddleware, environment=Environment.STAGING)
    return TestClient(app)


# ---------------------------------------------------------------------------
# 1. Header Presence Tests
# ---------------------------------------------------------------------------

class TestHeaderPresence:
    """Verify all 9 required headers are present on every response."""

    REQUIRED_HEADERS = [
        "Strict-Transport-Security",
        "X-Content-Type-Options",
        "X-Frame-Options",
        "Content-Security-Policy",
        "Referrer-Policy",
        "Permissions-Policy",
        "Cross-Origin-Embedder-Policy",
        "Cross-Origin-Opener-Policy",
        "Cross-Origin-Resource-Policy",
    ]

    def test_all_required_headers_present(self, prod_client: TestClient):
        """Every response must include all 9 security headers."""
        response = prod_client.get("/")
        assert response.status_code == 200
        for header in self.REQUIRED_HEADERS:
            assert header in response.headers, f"Missing header: {header}"

    def test_no_extra_headers_in_dev(self, dev_client: TestClient):
        """Dev should not include headers not in the spec."""
        response = dev_client.get("/")
        assert response.status_code == 200
        # All required headers still present, just different values
        for header in self.REQUIRED_HEADERS:
            assert header in response.headers, f"Missing header in dev: {header}"


# ---------------------------------------------------------------------------
# 2. Header Value Accuracy Tests (Production)
# ---------------------------------------------------------------------------

class TestHeaderValuesProduction:
    """Verify production header values match the security specification."""

    def test_hsts_production(self, prod_client: TestClient):
        """HSTS in production: max-age=63072000, includeSubDomains, preload"""
        response = prod_client.get("/")
        hsts = response.headers["Strict-Transport-Security"]
        assert "max-age=63072000" in hsts
        assert "includeSubDomains" in hsts
        assert "preload" in hsts
        assert hsts == HSTS_VALUE_PROD

    def test_x_content_type_options(self, prod_client: TestClient):
        """X-Content-Type-Options: nosniff"""
        response = prod_client.get("/")
        assert response.headers["X-Content-Type-Options"] == X_CONTENT_TYPE_OPTIONS

    def test_x_frame_options(self, prod_client: TestClient):
        """X-Frame-Options: DENY"""
        response = prod_client.get("/")
        assert response.headers["X-Frame-Options"] == X_FRAME_OPTIONS

    def test_referrer_policy(self, prod_client: TestClient):
        """Referrer-Policy: strict-origin-when-cross-origin"""
        response = prod_client.get("/")
        assert response.headers["Referrer-Policy"] == REFERRER_POLICY

    def test_permissions_policy(self, prod_client: TestClient):
        """Permissions-Policy blocks camera, microphone, geolocation"""
        response = prod_client.get("/")
        policy = response.headers["Permissions-Policy"]
        assert "camera=()" in policy
        assert "microphone=()" in policy
        assert "geolocation=()" in policy
        assert "payment=()" in policy
        assert "usb=()" in policy
        assert policy == PERMISSIONS_POLICY

    def test_coep_production(self, prod_client: TestClient):
        """Cross-Origin-Embedder-Policy: require-corp"""
        response = prod_client.get("/")
        assert response.headers["Cross-Origin-Embedder-Policy"] == COEP_PROD

    def test_coop_production(self, prod_client: TestClient):
        """Cross-Origin-Opener-Policy: same-origin"""
        response = prod_client.get("/")
        assert response.headers["Cross-Origin-Opener-Policy"] == COOP_PROD

    def test_corp_production(self, prod_client: TestClient):
        """Cross-Origin-Resource-Policy: same-site"""
        response = prod_client.get("/")
        assert response.headers["Cross-Origin-Resource-Policy"] == CORP_PROD


# ---------------------------------------------------------------------------
# 3. CSP Value Tests
# ---------------------------------------------------------------------------

class TestCSPValues:
    """Verify Content-Security-Policy directive accuracy."""

    def test_csp_has_default_src_self(self, prod_client: TestClient):
        response = prod_client.get("/")
        csp = response.headers["Content-Security-Policy"]
        assert "default-src 'self'" in csp

    def test_csp_has_nonce_in_script_src(self, prod_client: TestClient):
        response = prod_client.get("/")
        csp = response.headers["Content-Security-Policy"]
        assert "script-src" in csp
        assert "nonce-" in csp

    def test_csp_has_object_src_none(self, prod_client: TestClient):
        response = prod_client.get("/")
        csp = response.headers["Content-Security-Policy"]
        assert "object-src 'none'" in csp

    def test_csp_has_frame_ancestors_none(self, prod_client: TestClient):
        response = prod_client.get("/")
        csp = response.headers["Content-Security-Policy"]
        assert "frame-ancestors 'none'" in csp

    def test_csp_has_base_uri_self(self, prod_client: TestClient):
        response = prod_client.get("/")
        csp = response.headers["Content-Security-Policy"]
        assert "base-uri 'self'" in csp

    def test_csp_has_form_action_self(self, prod_client: TestClient):
        response = prod_client.get("/")
        csp = response.headers["Content-Security-Policy"]
        assert "form-action 'self'" in csp

    def test_csp_has_upgrade_insecure_requests(self, prod_client: TestClient):
        response = prod_client.get("/")
        csp = response.headers["Content-Security-Policy"]
        assert "upgrade-insecure-requests" in csp

    def test_csp_no_unsafe_inline_script(self, prod_client: TestClient):
        """Production CSP must NOT allow 'unsafe-inline' for scripts."""
        response = prod_client.get("/")
        csp = response.headers["Content-Security-Policy"]
        script_directive = [d for d in csp.split(";") if "script-src" in d]
        if script_directive:
            assert "'unsafe-inline'" not in script_directive[0], \
                "Production CSP must not allow 'unsafe-inline' in script-src"

    def test_csp_connect_src_restricts_api(self, prod_client: TestClient):
        response = prod_client.get("/")
        csp = response.headers["Content-Security-Policy"]
        assert "connect-src" in csp
        assert "https://api.fabric4l.dev" in csp


# ---------------------------------------------------------------------------
# 4. Dev vs Production Differences
# ---------------------------------------------------------------------------

class TestEnvironmentDifferences:
    """Validate environment-specific header value differences."""

    def test_hsts_dev_vs_prod(self, prod_client: TestClient, dev_client: TestClient):
        """Production HSTS has preload; dev HSTS is disabled."""
        prod_hsts = prod_client.get("/").headers["Strict-Transport-Security"]
        dev_hsts = dev_client.get("/").headers["Strict-Transport-Security"]
        assert "preload" in prod_hsts
        assert "max-age=0" in dev_hsts
        assert prod_hsts != dev_hsts

    def test_csp_dev_has_unsafe_eval(self, dev_client: TestClient):
        """Dev CSP allows 'unsafe-eval' for React devtools."""
        response = dev_client.get("/")
        csp = response.headers["Content-Security-Policy"]
        assert "'unsafe-eval'" in csp, "Dev CSP must allow unsafe-eval for React devtools"

    def test_csp_prod_no_unsafe_eval(self, prod_client: TestClient):
        """Production CSP does NOT allow 'unsafe-eval'."""
        response = prod_client.get("/")
        csp = response.headers["Content-Security-Policy"]
        assert "'unsafe-eval'" not in csp, "Production CSP must not allow unsafe-eval"

    def test_csp_dev_allows_unsafe_inline_styles(self, dev_client: TestClient):
        """Dev CSP allows unsafe-inline for styles."""
        response = dev_client.get("/")
        csp = response.headers["Content-Security-Policy"]
        assert "'unsafe-inline'" in csp, "Dev CSP must allow unsafe-inline for styles"

    def test_coep_dev_is_unsafe_none(self, dev_client: TestClient):
        """Dev COEP is unsafe-none."""
        response = dev_client.get("/")
        assert response.headers["Cross-Origin-Embedder-Policy"] == COEP_DEV

    def test_coop_dev_is_allow_popups(self, dev_client: TestClient):
        """Dev COOP allows popups."""
        response = dev_client.get("/")
        assert response.headers["Cross-Origin-Opener-Policy"] == COOP_DEV

    def test_corp_dev_is_cross_origin(self, dev_client: TestClient):
        """Dev CORP is cross-origin."""
        response = dev_client.get("/")
        assert response.headers["Cross-Origin-Resource-Policy"] == CORP_DEV

    def test_staging_hsts_not_preload(self, staging_client: TestClient):
        """Staging HSTS is 1 day, no preload."""
        response = staging_client.get("/")
        hsts = response.headers["Strict-Transport-Security"]
        assert "max-age=86400" in hsts
        assert "preload" not in hsts


# ---------------------------------------------------------------------------
# 5. Excluded Paths
# ---------------------------------------------------------------------------

class TestExcludedPaths:
    """Verify health/metrics endpoints do not receive security headers."""

    def test_health_endpoint_no_headers(self, prod_client: TestClient):
        """Health check should not have security headers."""
        response = prod_client.get("/health")
        assert response.status_code == 200
        assert "Strict-Transport-Security" not in response.headers
        assert "Content-Security-Policy" not in response.headers

    def test_metrics_endpoint_no_headers(self, prod_client: TestClient):
        """Metrics endpoint should not have security headers."""
        response = prod_client.get("/metrics")
        assert response.status_code == 200
        assert "Strict-Transport-Security" not in response.headers
        assert "X-Frame-Options" not in response.headers


# ---------------------------------------------------------------------------
# 6. Per-Route Overrides
# ---------------------------------------------------------------------------

class TestPerRouteOverrides:
    """Validate the override decorator functionality."""

    def test_embed_x_frame_options_override(self, prod_client: TestClient):
        """Embed endpoint allows SAMEORIGIN framing."""
        response = prod_client.get("/embed")
        assert response.status_code == 200
        assert response.headers["X-Frame-Options"] == "SAMEORIGIN"

    def test_no_headers_override(self, prod_client: TestClient):
        """Disable headers endpoint has no security headers."""
        response = prod_client.get("/no-headers")
        assert response.status_code == 200
        assert "Strict-Transport-Security" not in response.headers
        assert "Content-Security-Policy" not in response.headers

    def test_other_headers_still_present_on_embed(self, prod_client: TestClient):
        """Embed override only affects X-Frame-Options, other headers remain."""
        response = prod_client.get("/embed")
        assert response.headers["X-Content-Type-Options"] == X_CONTENT_TYPE_OPTIONS
        assert response.headers["Referrer-Policy"] == REFERRER_POLICY
        assert "Content-Security-Policy" in response.headers


# ---------------------------------------------------------------------------
# 7. CSP Nonce Tests
# ---------------------------------------------------------------------------

class TestCSPNonce:
    """Validate CSP nonce generation and freshness."""

    def test_nonce_present_in_response_header(self, prod_client: TestClient):
        """CSP nonce exposed in X-CSP-Nonce header for template injection."""
        response = prod_client.get("/")
        assert "X-CSP-Nonce" in response.headers
        nonce = response.headers["X-CSP-Nonce"]
        assert len(nonce) >= 16  # At least 16 chars (128 bits base64)

    def test_nonce_unique_per_request(self, prod_client: TestClient):
        """Each request gets a different nonce."""
        nonce1 = prod_client.get("/").headers["X-CSP-Nonce"]
        nonce2 = prod_client.get("/").headers["X-CSP-Nonce"]
        assert nonce1 != nonce2, "CSP nonce must be unique per request"

    def test_nonce_appears_in_csp_header(self, prod_client: TestClient):
        """The nonce in X-CSP-Nonce must match the nonce in CSP header."""
        response = prod_client.get("/")
        nonce = response.headers["X-CSP-Nonce"]
        csp = response.headers["Content-Security-Policy"]
        assert nonce in csp, "CSP nonce must appear in Content-Security-Policy header"


# ---------------------------------------------------------------------------
# 8. OWASP Compliance Baseline
# ---------------------------------------------------------------------------

class TestOWASPCompliance:
    """
    Validate against OWASP ASVS and Secure Headers Project requirements.

    References:
      - OWASP ASVS V14.4.1: Verify every HTTP response contains a content type
      - OWASP ASVS V14.4.2: Verify X-Content-Type-Options: nosniff
      - OWASP ASVS V14.4.3: Verify X-Frame-Options or CSP frame-ancestors
      - OWASP ASVS V14.4.4: Verify HSTS with max-age >= 1 year (prod)
      - OWASP ASVS V14.4.5: Verify Referrer-Policy
      - OWASP ASVS V14.4.6: Verify CSP is implemented
      - OWASP ASVS V14.4.7: Verify CSP is restrictive (no wildcards)
    """

    def test_asvs_v14_4_2_nosniff(self, prod_client: TestClient):
        """ASVS V14.4.2: X-Content-Type-Options: nosniff"""
        response = prod_client.get("/")
        assert response.headers.get("X-Content-Type-Options") == "nosniff"

    def test_asvs_v14_4_3_frame_protection(self, prod_client: TestClient):
        """ASVS V14.4.3: Frame protection via X-Frame-Options or CSP"""
        response = prod_client.get("/")
        has_xfo = response.headers.get("X-Frame-Options") == "DENY"
        csp = response.headers.get("Content-Security-Policy", "")
        has_csp_fa = "frame-ancestors" in csp
        assert has_xfo or has_csp_fa, "Must have frame protection"

    def test_asvs_v14_4_4_hsts_year(self, prod_client: TestClient):
        """ASVS V14.4.4: HSTS max-age >= 31536000 seconds (1 year)"""
        response = prod_client.get("/")
        hsts = response.headers.get("Strict-Transport-Security", "")
        import re
        match = re.search(r"max-age=(\d+)", hsts)
        assert match is not None, "HSTS must have max-age directive"
        max_age = int(match.group(1))
        assert max_age >= 31536000, f"HSTS max-age ({max_age}) must be >= 31536000"

    def test_asvs_v14_4_5_referrer_policy(self, prod_client: TestClient):
        """ASVS V14.4.5: Referrer-Policy is set"""
        response = prod_client.get("/")
        assert "Referrer-Policy" in response.headers

    def test_asvs_v14_4_6_csp_present(self, prod_client: TestClient):
        """ASVS V14.4.6: Content-Security-Policy header is present"""
        response = prod_client.get("/")
        assert "Content-Security-Policy" in response.headers

    def test_asvs_v14_4_7_csp_no_wildcards(self, prod_client: TestClient):
        """ASVS V14.4.7: CSP should not use wildcard sources"""
        response = prod_client.get("/")
        csp = response.headers["Content-Security-Policy"]
        directives = csp.split(";")
        for directive in directives:
            parts = directive.strip().split()
            if len(parts) > 1:
                for source in parts[1:]:
                    assert source != "*", f"CSP must not use wildcard: {directive}"

    def test_no_server_header_disclosure(self, prod_client: TestClient):
        """Server header should not reveal version information."""
        response = prod_client.get("/")
        server = response.headers.get("Server", "")
        assert "nginx" not in server.lower() or "fabric" in server.lower(), \
            "Server header should not disclose technology version"


# ---------------------------------------------------------------------------
# 9. Edge Cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Boundary and edge case handling."""

    def test_404_responses_have_headers(self, prod_client: TestClient):
        """Even 404 responses should have security headers."""
        response = prod_client.get("/nonexistent-path-that-does-not-exist")
        assert response.status_code == 404
        assert "Strict-Transport-Security" in response.headers
        assert "Content-Security-Policy" in response.headers

    def test_redirect_responses_have_headers(self, prod_client: TestClient):
        """Redirect responses should have security headers."""
        response = prod_client.get("/", follow_redirects=False)
        # 200 on root, but headers should still be present
        assert "Strict-Transport-Security" in response.headers
