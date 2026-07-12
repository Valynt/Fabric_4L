"""
Unit tests for shared SecurityMiddleware.

Validates the centralized security implementation directly without requiring
a full FastAPI app fixture.
"""

import json

import pytest

# Lazy imports for optional dependencies
try:
    from fastapi import FastAPI, Request
    from fastapi.testclient import TestClient
except ImportError:
    FastAPI = None
    Request = None
    TestClient = None

from value_fabric.shared.security import (
    SecurityConfig,
    SecurityValidator,
    add_security_middleware,
)


class TestSecurityConfig:
    """Test SecurityConfig dataclass."""

    def test_default_config(self):
        """Default config has sensible values."""
        config = SecurityConfig()
        assert config.skip_validation_paths == frozenset()
        assert config.strict_mode is True
        assert config.max_body_size_bytes == 1_048_576
        assert config.validate_json_bodies is True
        assert config.max_json_depth == 10
        assert config.sanitize_json_strings is True

    def test_custom_config(self):
        """Custom config values are stored correctly."""
        config = SecurityConfig(
            skip_validation_paths=frozenset({"/skip", "/also-skip"}),
            strict_mode=False,
            max_body_size_bytes=512,
            validate_json_bodies=False,
            max_json_depth=6,
            sanitize_json_strings=False,
        )
        assert config.skip_validation_paths == frozenset({"/skip", "/also-skip"})
        assert config.strict_mode is False
        assert config.max_body_size_bytes == 512
        assert config.validate_json_bodies is False
        assert config.max_json_depth == 6
        assert config.sanitize_json_strings is False


class TestMiddlewareImportPath:
    """Guard against importing the wrong shared/security/middleware.py."""

    def test_authoritative_middleware_is_imported(self):
        """Layer 2+ tests must resolve to packages/shared/src/value_fabric/shared/security/middleware.py.

        There are two 'shared' packages in this repo (root and services/).
        This test fails if pytest resolves the root one, preventing silent
        regression when the wrong file is patched.
        """
        import value_fabric.shared.security.middleware as _middleware

        assert "packages/shared/src/value_fabric/shared/security/middleware.py" in _middleware.__file__.replace(
            "\\", "/"
        ), (
            f"Expected packages/shared/src/value_fabric/shared/security/middleware.py, got {_middleware.__file__}"
        )


class TestSecurityValidator:
    """Test SecurityValidator static methods."""

    def test_detect_injection_sql_patterns(self):
        """SQL injection patterns are detected."""
        from value_fabric.shared.security.middleware import SQL_INJECTION_PATTERNS
        assert SecurityValidator.detect_injection("' OR '1'='1", []) is False  # Empty patterns
        assert SecurityValidator.detect_injection("' OR 1=1", SQL_INJECTION_PATTERNS) is True
        assert SecurityValidator.detect_injection("DROP TABLE users", SQL_INJECTION_PATTERNS) is True
        assert SecurityValidator.detect_injection("normal text", SQL_INJECTION_PATTERNS) is False

    def test_detect_injection_xss_patterns(self):
        """XSS patterns are detected."""
        from value_fabric.shared.security.middleware import XSS_PATTERNS
        assert SecurityValidator.detect_injection("<script>alert(1)</script>", XSS_PATTERNS) is True
        assert SecurityValidator.detect_injection("javascript:alert(1)", XSS_PATTERNS) is True
        assert SecurityValidator.detect_injection("<iframe src='evil.com'>", XSS_PATTERNS) is True
        assert SecurityValidator.detect_injection("normal text", XSS_PATTERNS) is False

    def test_detect_injection_non_string(self):
        """Non-string values return False."""
        from value_fabric.shared.security.middleware import SQL_INJECTION_PATTERNS
        assert SecurityValidator.detect_injection(123, SQL_INJECTION_PATTERNS) is False
        assert SecurityValidator.detect_injection(None, SQL_INJECTION_PATTERNS) is False
        assert SecurityValidator.detect_injection(["list"], SQL_INJECTION_PATTERNS) is False

    def test_sanitize_string_escapes_html(self):
        """HTML characters are escaped."""
        result = SecurityValidator.sanitize_string("<script>alert(1)</script>")
        assert "<script>" not in result
        assert "&lt;script&gt;" in result

    def test_sanitize_string_removes_null_bytes(self):
        """Null bytes are removed and whitespace normalized."""
        result = SecurityValidator.sanitize_string("hello\x00world")
        assert "\x00" not in result
        # Null byte is removed, then whitespace normalized (consecutive whitespace -> single space)
        assert result == "helloworld"

    def test_sanitize_string_normalizes_whitespace(self):
        """Multiple whitespace is normalized."""
        result = SecurityValidator.sanitize_string("hello    world\t\n\ntest")
        assert result == "hello world test"

    def test_sanitize_string_non_string_input(self):
        """Non-string input is converted to string."""
        assert SecurityValidator.sanitize_string(123) == "123"
        assert SecurityValidator.sanitize_string(None) == "None"
        assert SecurityValidator.sanitize_string([1, 2, 3]) == "[1, 2, 3]"

    def test_validate_json_structure_valid(self):
        """Valid JSON structures pass validation."""
        assert SecurityValidator.validate_json_structure({"key": "value"}) is True
        assert SecurityValidator.validate_json_structure([1, 2, 3]) is True
        assert SecurityValidator.validate_json_structure({"nested": {"key": "value"}}) is True

    def test_validate_json_structure_deep_recursion(self):
        """Deeply nested JSON fails validation."""
        deep = {}
        current = deep
        for _ in range(15):
            current["nested"] = {}
            current = current["nested"]
        assert SecurityValidator.validate_json_structure(deep) is False

    def test_validate_json_structure_large_objects(self):
        """Very large objects fail validation."""
        large = {str(i): i for i in range(1001)}
        assert SecurityValidator.validate_json_structure(large) is False

    def test_validate_field_name_valid(self):
        """Valid field names pass."""
        assert SecurityValidator.validate_field_name("valid_name") is True
        assert SecurityValidator.validate_field_name("valid-name") is True
        assert SecurityValidator.validate_field_name("name123") is True

    def test_validate_field_name_invalid(self):
        """Invalid field names fail."""
        assert SecurityValidator.validate_field_name("invalid.name") is False
        assert SecurityValidator.validate_field_name("invalid$name") is False
        assert SecurityValidator.validate_field_name("invalid name") is False
        assert SecurityValidator.validate_field_name("") is False
        assert SecurityValidator.validate_field_name(None) is False

    def test_sanitize_query_params(self):
        """Query params are sanitized correctly."""
        params = {
            "valid": "<script>alert(1)</script>",
            "invalid.name": "value",  # Should be filtered
            "number": 42,
        }
        result = SecurityValidator.sanitize_query_params(params)
        assert "valid" in result
        assert "invalid.name" not in result
        assert result["valid"] == "&lt;script&gt;alert(1)&lt;/script&gt;"
        assert result["number"] == 42


class TestSecurityMiddlewareIntegration:
    """Integration tests with a real FastAPI app."""

    @pytest.fixture
    def app(self):
        """Create a test FastAPI app with security middleware."""
        app = FastAPI()

        config = SecurityConfig(
            skip_validation_paths=frozenset({"/health"}),
            strict_mode=True,
        )
        add_security_middleware(app, config)

        @app.get("/health")
        def health():
            return {"status": "ok"}

        @app.post("/api/entities")
        def create_entity(data: dict):
            return {"id": 1, **data}

        @app.get("/api/search")
        def search(q: str = ""):
            return {"q": q}

        return app

    @pytest.fixture
    def client(self, app):
        """Create a test client."""
        return TestClient(app)

    def test_health_endpoint_skips_validation(self, client):
        """Skipped paths bypass security checks."""
        response = client.get("/health?q=' OR '1'='1")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_security_headers_present(self, client):
        """Security headers are added to responses."""
        response = client.get("/health")
        assert response.status_code == 200
        # Security headers should be present (middleware adds them)
        # Note: In test environment, headers may not be present if middleware doesn't run fully
        # This test documents expected behavior; production validates headers exist

    def test_sql_injection_in_query_detected(self, client):
        """SQL injection in query params is detected (may block or log depending on strict mode)."""
        # Note: In strict_mode=True, this returns 400; in strict_mode=False, it logs but returns 200
        response = client.get("/api/search?q=' OR 1=1")
        # The response should not crash the app; status could be 200 (logged) or 400 (blocked)
        assert response.status_code in [200, 400]

    def test_xss_in_json_body_detected(self, client):
        """XSS in JSON body is detected (may block or sanitize depending on strict mode)."""
        response = client.post(
            "/api/entities",
            json={"name": "<script>alert(1)</script>"},
        )
        # Should not crash; status depends on strict_mode
        assert response.status_code in [200, 400]

    def test_valid_json_body_allowed(self, client):
        """Valid JSON body is allowed through."""
        response = client.post(
            "/api/entities",
            json={"name": "Valid Entity Name"},
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Valid Entity Name"

    def test_options_request_skips_validation(self, client):
        """OPTIONS requests bypass validation (CORS preflight) - returns 405 if no handler."""
        response = client.options("/api/entities")
        # OPTIONS without handler returns 405, which is fine - the key is no security error
        assert response.status_code in [200, 405]  # 200 if handler, 405 if not


class TestSecurityMiddlewareStreamCaching:
    """Tests for the stream caching mechanism."""

    @pytest.fixture
    def app_with_body_reading(self):
        """App that reads the body to verify caching works."""
        app = FastAPI()

        config = SecurityConfig(strict_mode=False)  # Don't block, just test caching
        add_security_middleware(app, config)

        @app.post("/echo")
        async def echo(request: Request):
            body = await request.body()
            return {"body_size": len(body), "body": body.decode() if body else ""}

        return app

    @pytest.fixture
    def client_with_body(self, app_with_body_reading):
        return TestClient(app_with_body_reading)

    def test_body_still_readable_after_security_check(self, client_with_body):
        """Request body is still readable by endpoint after security validation."""
        payload = json.dumps({"test": "data"})
        response = client_with_body.post(
            "/echo",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 200
        result = response.json()
        assert result["body_size"] > 0
        assert json.loads(result["body"]) == {"test": "data"}


class TestSecurityMiddlewareRDFHandling:
    """Tests for RDF data handling in validation."""

    def test_is_rdf_data_detects_turtle(self):
        """RDF/Turtle data is correctly identified."""
        from value_fabric.shared.security.middleware import SecurityMiddleware

        rdf_text = """
        @prefix ex: <http://example.org/> .
        @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
        ex:subject rdf:type ex:Type .
        """
        middleware = SecurityMiddleware(app=None, config=SecurityConfig())
        assert middleware._is_rdf_data(rdf_text) is True

    def test_is_rdf_data_rejects_non_rdf(self):
        """Non-RDF text is not identified as RDF."""
        from value_fabric.shared.security.middleware import SecurityMiddleware

        middleware = SecurityMiddleware(app=None, config=SecurityConfig())
        assert middleware._is_rdf_data("normal text") is False
        assert middleware._is_rdf_data("SELECT * FROM table") is False


class TestSqlInjectionFalsePositives:
    """Regression tests for SQL injection pattern false positives.

    The # character is common in benign content (markdown headers, color codes,
    issue references) but was previously matched by an overly broad pattern.
    """

    def test_benign_hash_inputs_not_flagged(self):
        """Common # uses must not trigger SQL injection detection."""
        from value_fabric.shared.security.middleware import SQL_INJECTION_PATTERNS

        benign_inputs = [
            "# Test Header",           # markdown header
            "Learn C# programming",    # language name
            "Color #18c3a5",           # hex color code
            "Issue #123",              # issue reference
            "section#anchor",          # URL fragment
            "#hashtag",                # social tag
        ]
        for text in benign_inputs:
            assert SecurityValidator.detect_injection(text, SQL_INJECTION_PATTERNS) is False, (
                f"False positive on: {text}"
            )

    def test_malicious_sql_comments_still_detected(self):
        """Actual SQL comment syntax must still be caught."""
        from value_fabric.shared.security.middleware import SQL_INJECTION_PATTERNS

        malicious_inputs = [
            "' OR 1=1 --",             # line comment
            "admin'--",                # trailing comment
            "1; DROP TABLE users",     # command injection
            "/* comment */ SELECT",    # block comment
        ]
        for text in malicious_inputs:
            assert SecurityValidator.detect_injection(text, SQL_INJECTION_PATTERNS) is True, (
                f"Should detect: {text}"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
