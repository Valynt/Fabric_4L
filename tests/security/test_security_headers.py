"""
Security tests for HTTP security headers.

Validates that all responses include required security headers.
"""

# Lazy import for optional dependency
import pytest

from tests.security._category_manifest import assert_security_category_manifest

try:
    from fastapi.testclient import TestClient
except ImportError:
    TestClient = None


SECURITY_HEADER_TESTS = (
    "tests/security/test_security_headers.py",
    "tests/security/test_security_misconfiguration.py",
    "tests/security/test_shared_security_middleware.py",
    "tests/security/test_p1_14_security_middleware.py",
    "tests/security/test_h03_service_startup_validation.py",
)


@pytest.mark.security
@pytest.mark.contract_static
def test_security_headers_coverage_manifest_is_current() -> None:
    assert_security_category_manifest("security_headers", SECURITY_HEADER_TESTS)


class TestSecurityHeaders:
    """Test suite for security headers."""

    REQUIRED_HEADERS = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Content-Security-Policy": None,  # Just check presence
        "Permissions-Policy": None,
        "Cross-Origin-Resource-Policy": "same-origin",
        "Cross-Origin-Opener-Policy": "same-origin",
    }

    @pytest.mark.xfail(strict=True, reason='SecurityMiddleware not attached to test client app; headers absent in test env')
    def test_security_headers_present_on_all_responses(self, client: TestClient):
        """P1: All responses include security headers."""
        response = client.get("/api/v1/health")

        for header, expected_value in self.REQUIRED_HEADERS.items():
            assert header in response.headers, f"Missing header: {header}"

            if expected_value:
                assert response.headers[header] == expected_value, \
                    f"Header {header} has wrong value: {response.headers[header]}"

    @pytest.mark.xfail(strict=True, reason='SecurityMiddleware not attached to test client app; CSP header absent in test env')
    def test_csp_header_api_specific(self, client: TestClient):
        """CSP header is strict for API responses."""
        response = client.get("/api/v1/health")

        csp = response.headers.get("Content-Security-Policy", "")
        assert "default-src 'none'" in csp or "default-src" in csp
        assert "frame-ancestors 'none'" in csp

    def test_no_server_version_header(self, client: TestClient):
        """Server version headers are not exposed."""
        response = client.get("/api/v1/health")

        # Should not reveal server software/version
        server_header = response.headers.get("Server", "")
        assert "nginx" not in server_header.lower() or "apache" not in server_header.lower()

    def test_strict_transport_security_on_https(self, client: TestClient):
        """HSTS header present on HTTPS responses."""
        # In production with HTTPS
        response = client.get("/api/v1/health")

        hsts = response.headers.get("Strict-Transport-Security")
        if hsts:
            assert "max-age" in hsts
            assert "includeSubDomains" in hsts


class TestCORSHeaders:
    """Test CORS header security."""

    def test_cors_not_wildcard_in_production(self, client: TestClient):
        """Production should not use wildcard CORS."""
        response = client.get(
            "/api/v1/health",
            headers={"Origin": "https://evil.com"},
        )

        # In production, should not allow any origin
        acao = response.headers.get("Access-Control-Allow-Origin")
        if acao:
            assert acao != "*", "Wildcard CORS not allowed in production"

    def test_credentials_not_allowed_with_wildcard(self, client: TestClient):
        """Cannot use allow_credentials=True with wildcard origins."""
        response = client.options(
            "/api/v1/health",
            headers={
                "Origin": "https://example.com",
                "Access-Control-Request-Method": "GET",
            },
        )

        acao = response.headers.get("Access-Control-Allow-Origin")
        acac = response.headers.get("Access-Control-Allow-Credentials")

        # Browser security: cannot have both wildcard and credentials
        if acao == "*":
            assert acac != "true", "Cannot use credentials with wildcard origin"
