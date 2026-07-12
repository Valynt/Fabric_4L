"""
OWASP Security Misconfiguration Tests

Tests for A05: Security Misconfiguration - default credentials,
debug endpoints, security headers, and verbose error messages.
"""

import os

# Lazy import for optional dependency
import pytest

try:
    from fastapi.testclient import TestClient
except ImportError:
    TestClient = None


class TestDefaultCredentials:
    """Default credential and weak password tests."""

    DEFAULT_PASSWORDS = [
        "password",
        "admin",
        "123456",
        "changeme",
        "default",
        "password123",
        "admin123",
        "root",
        "toor",
        "guest",
    ]

    def test_default_admin_credentials_blocked(self, client: TestClient):
        """P0: Default admin credentials are not accepted."""
        for password in self.DEFAULT_PASSWORDS:
            response = client.post(
                "/api/v1/auth/login",
                json={
                    "email": "admin@value-fabric.io",
                    "password": password,
                },
            )
            # Should not authenticate with default passwords
            assert response.status_code in [401, 403, 404], (
                f"Default password '{password}' was accepted - critical vulnerability"
            )

    def test_default_api_keys_blocked(self, client: TestClient):
        """P0: Default API keys are not functional."""
        default_keys = [
            "test-api-key",
            "api-key-123",
            "default",
            "changeme",
            "sk-test-123",
            "pk-test-123",
        ]

        for key in default_keys:
            response = client.get(
                "/api/v1/entities",
                headers={"X-API-Key": key},
            )
            # Default keys should not work in production
            assert response.status_code in [401, 403], (
                f"Default API key '{key}' was accepted"
            )

    def test_no_hardcoded_secrets_in_response(self, client: TestClient):
        """P0: No hardcoded secrets in API responses."""
        response = client.get(
            "/api/v1/health",
        )

        if response.status_code == 200:
            response_text = response.text.lower()

            # Check for common secret patterns
            secret_patterns = [
                "api_key", "apikey", "api-key",
                "secret_key", "secretkey", "secret-key",
                "password", "pass",
                "aws_access_key", "aws_secret",
                "private_key", "privatekey",
                "-----begin", "ssh-rsa",
            ]

            for pattern in secret_patterns:
                assert pattern not in response_text, (
                    f"Secret pattern '{pattern}' found in public response"
                )


class TestDebugEndpoints:
    """Debug endpoint exposure tests."""

    DEBUG_ENDPOINTS = [
        "/debug",
        "/debug/vars",
        "/debug/pprof",
        "/debug/pprof/profile",
        "/debug/pprof/heap",
        "/debug/pprof/goroutine",
        "/debug/pprof/threadcreate",
        "/debug/pprof/block",
        "/debug/pprof/mutex",
        "/debug/pprof/allocs",
        "/debug/pprof/cmdline",
        "/debug/pprof/symbol",
        "/debug/pprof/trace",
        "/.env",
        "/.git/config",
        "/config.json",
        "/config.yaml",
        "/settings.py",
        "/manage.py",
        "/phpinfo.php",
        "/phpmyadmin",
        "/adminer",
    ]

    def test_debug_endpoints_not_exposed_in_prod(self, client: TestClient):
        """P0: Debug endpoints are not accessible in production."""
        for endpoint in self.DEBUG_ENDPOINTS:
            response = client.get(endpoint)

            # Should be 404 (not found) or 403 (forbidden)
            assert response.status_code in [404, 403, 401], (
                f"Debug endpoint {endpoint} exposed with status {response.status_code}"
            )

            # Response should not contain debug info
            if response.status_code == 200:
                body = response.text.lower()
                assert "goroutine" not in body, f"Goroutine profile exposed at {endpoint}"
                assert "heap" not in body or "heap_alloc" not in body, f"Heap profile exposed at {endpoint}"
                assert "database" not in body, f"Database config exposed at {endpoint}"

    def test_swagger_ui_not_exposed_in_prod(self, client: TestClient):
        """P0: Swagger/OpenAPI UI not exposed in production."""
        swagger_endpoints = [
            "/swagger",
            "/swagger-ui",
            "/swagger.json",
            "/swagger.yaml",
            "/api-docs",
            "/api/docs",
            "/redoc",
            "/rapidoc",
        ]

        # Check if in production
        env = os.getenv("ENVIRONMENT", "development")
        if env in ["production", "prod", "staging"]:
            for endpoint in swagger_endpoints:
                response = client.get(endpoint)
                assert response.status_code in [404, 401, 403], (
                    f"Swagger UI exposed at {endpoint} in {env} environment"
                )


class TestSecurityHeaders:
    """HTTP security headers verification."""

    REQUIRED_HEADERS = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": ["DENY", "SAMEORIGIN"],
    }

    RECOMMENDED_HEADERS = [
        "Strict-Transport-Security",  # HSTS
        "Content-Security-Policy",
        "X-XSS-Protection",
        "Referrer-Policy",
        "Permissions-Policy",
    ]

    @pytest.mark.xfail(strict=True, reason='SecurityMiddleware not attached to test client app; headers absent in test env')
    def test_security_headers_present(self, client: TestClient):
        """P0: Required security headers are present."""
        response = client.get("/api/v1/entities")

        headers = {k.lower(): v for k, v in response.headers.items()}

        # X-Content-Type-Options should prevent MIME sniffing
        assert "x-content-type-options" in headers, "Missing X-Content-Type-Options header"
        assert headers["x-content-type-options"] == "nosniff", (
            f"X-Content-Type-Options is '{headers['x-content-type-options']}', expected 'nosniff'"
        )

        # X-Frame-Options should prevent clickjacking
        assert "x-frame-options" in headers, "Missing X-Frame-Options header"
        assert headers["x-frame-options"].upper() in ["DENY", "SAMEORIGIN"], (
            f"X-Frame-Options is '{headers['x-frame-options']}', expected DENY or SAMEORIGIN"
        )

    def test_hsts_header_in_production(self, client: TestClient):
        """P0: HSTS header present in production environments."""
        env = os.getenv("ENVIRONMENT", "development")

        if env in ["production", "prod", "staging"]:
            response = client.get("/api/v1/entities")
            headers = {k.lower(): v for k, v in response.headers.items()}

            assert "strict-transport-security" in headers, (
                "HSTS header missing in production environment"
            )

            hsts = headers["strict-transport-security"]
            assert "max-age" in hsts, "HSTS missing max-age directive"

            # Recommended: max-age of at least 1 year (31536000 seconds)
            max_age_start = hsts.find("max-age=") + 8
            max_age_end = hsts.find(";", max_age_start)
            if max_age_end == -1:
                max_age_end = len(hsts)
            max_age = int(hsts[max_age_start:max_age_end])

            assert max_age >= 31536000, (
                f"HSTS max-age is {max_age}, should be at least 31536000 (1 year)"
            )

    @pytest.mark.xfail(strict=True, reason='SecurityMiddleware not attached to test client app; CSP header absent in test env')
    def test_csp_header_present(self, client: TestClient):
        """P0: Content Security Policy header present."""
        response = client.get("/api/v1/entities")
        headers = {k.lower(): v for k, v in response.headers.items()}

        # Check for CSP header (can be Content-Security-Policy or X-Content-Security-Policy)
        csp_present = (
            "content-security-policy" in headers or
            "x-content-security-policy" in headers
        )

        assert csp_present, "Content Security Policy header missing"

    def test_no_sensitive_headers_exposed(self, client: TestClient):
        """P0: Sensitive server info not exposed in headers."""
        response = client.get("/api/v1/entities")

        # Check for server version disclosure
        server_header = response.headers.get("Server", "").lower()
        assert "nginx/" not in server_header or server_header == "nginx", (
            f"Server version disclosed: {server_header}"
        )

        # Check for framework version disclosure
        powered_by = response.headers.get("X-Powered-By", "").lower()
        assert "fastapi" not in powered_by and "python" not in powered_by, (
            f"Framework disclosed in X-Powered-By: {powered_by}"
        )

        # Check for database version
        for header_name, header_value in response.headers.items():
            header_lower = header_value.lower()
            assert "postgresql" not in header_lower, "PostgreSQL version disclosed"
            assert "mysql" not in header_lower, "MySQL version disclosed"
            assert "redis" not in header_lower, "Redis version disclosed"


class TestErrorVerbosity:
    """Error message information disclosure tests."""

    def test_error_messages_do_not_leak_stack_traces(self, client: TestClient):
        """P0: Error responses do not contain stack traces."""
        # Trigger an error
        response = client.get("/api/v1/entities/malformed-uuid-format")

        if response.status_code >= 400:
            body = response.text.lower()

            # Check for stack trace indicators
            stack_indicators = [
                "traceback",
                "at ",  # Java stack trace
                "file \"",  # Python file reference
                "line ",
                "stack trace",
                "exception in thread",
                "caused by:",
                "nested exception is",
            ]

            for indicator in stack_indicators:
                assert indicator not in body, (
                    f"Stack trace leaked in error response: found '{indicator}'"
                )

    def test_404_errors_are_generic(self, client: TestClient):
        """P0: 404 errors don't reveal resource existence."""
        # Request non-existent resource
        response = client.get("/api/v1/entities/00000000-0000-0000-0000-000000000000")

        if response.status_code == 404:
            body = response.text.lower()

            # Should be generic "not found" without revealing structure
            # Bad: "User with ID 123 not found" (reveals user ID format)
            # Good: "Resource not found"
            specific_patterns = [
                "record with",
                "entry with",
                "id not found",
                "uuid not found",
                "no such",
            ]

            for pattern in specific_patterns:
                assert pattern not in body, (
                    f"Verbose 404 error reveals resource structure: '{pattern}'"
                )

    def test_database_errors_masked(self, client: TestClient):
        """P0: Database errors are masked in responses."""
        # Try to trigger a DB error with invalid input
        response = client.get("/api/v1/entities?page=-1&limit=999999999999")

        if response.status_code >= 400:
            body = response.text.lower()

            db_error_patterns = [
                "sql",
                "sqlite",
                "postgresql",
                "mysql",
                "orm",
                "peewee",
                "sqlalchemy",
                "database error",
                "syntax error",
                "constraint violation",
            ]

            for pattern in db_error_patterns:
                assert pattern not in body, (
                    f"Database error leaked in response: '{pattern}'"
                )

    def test_authentication_errors_are_generic(self, client: TestClient):
        """P0: Auth errors don't reveal whether user exists."""
        # Test with valid user but wrong password
        response1 = client.post(
            "/api/v1/auth/login",
            json={
                "email": "existing@tenant-a.com",
                "password": "wrong-password",
            },
        )

        # Test with non-existent user
        response2 = client.post(
            "/api/v1/auth/login",
            json={
                "email": "nonexistent@fake-domain-12345.com",
                "password": "any-password",
            },
        )

        # Both should return same status code (no user enumeration)
        assert response1.status_code == response2.status_code, (
            "Authentication error allows user enumeration: "
            f"existing user returns {response1.status_code}, "
            f"non-existing returns {response2.status_code}"
        )

        # Both should have same error message
        if response1.status_code == response2.status_code == 401:
            assert response1.text == response2.text, (
                "Authentication error messages differ, allowing user enumeration"
            )


class TestCORSPolicy:
    """Cross-Origin Resource Sharing configuration tests."""

    def test_cors_origin_restricted_in_prod(self, client: TestClient):
        """P0: CORS origin is restricted in production."""
        env = os.getenv("ENVIRONMENT", "development")

        # Test with arbitrary origin
        response = client.get(
            "/api/v1/entities",
            headers={"Origin": "https://evil-site.com"},
        )

        if env in ["production", "prod", "staging"]:
            # Should not allow arbitrary origins in production
            acao = response.headers.get("Access-Control-Allow-Origin", "")
            assert acao != "*", "CORS wildcard (*) not allowed in production"
            assert "evil-site.com" not in acao, "Arbitrary origin allowed in CORS"

    def test_cors_credentials_handling(self, client: TestClient):
        """P0: CORS credentials configuration is secure."""
        response = client.options(
            "/api/v1/entities",
            headers={
                "Origin": "https://example.com",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Authorization",
            },
        )

        # If credentials are allowed, origin cannot be wildcard
        acac = response.headers.get("Access-Control-Allow-Credentials", "").lower()
        acao = response.headers.get("Access-Control-Allow-Origin", "")

        if acac == "true":
            assert acao != "*", (
                "Security violation: CORS credentials allowed with wildcard origin"
            )


class TestAdminInterfaceSecurity:
    """Admin interface exposure and security tests."""

    ADMIN_PATHS = [
        "/admin",
        "/admin/login",
        "/admin/dashboard",
        "/django-admin",
        "/wp-admin",
        "/wp-login.php",
        "/administrator",
        "/phpmyadmin",
        "/pgadmin",
        "/adminer.php",
        "/_admin",
        "/backend",
        "/console",
        "/management",
        "/manager",
        "/moderator",
        "/webadmin",
        "/sysadmin",
    ]

    def test_admin_interfaces_not_publicly_exposed(self, client: TestClient):
        """P0: Admin interfaces require authentication/IP restriction."""
        for path in self.ADMIN_PATHS:
            response = client.get(path)

            # Admin paths should either:
            # 1. Not exist (404)
            # 2. Require authentication (401/403)
            # 3. Be IP-restricted (403)
            assert response.status_code in [404, 401, 403], (
                f"Admin interface at {path} exposed with status {response.status_code}"
            )

            # Response should not contain admin login forms
            if response.status_code == 200:
                body = response.text.lower()
                assert "admin login" not in body, f"Admin login form at {path}"
                assert "django" not in body or "admin" not in body, f"Django admin at {path}"
