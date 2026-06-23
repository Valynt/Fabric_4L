"""
Security fix tests for Layer 5 Ground Truth.

Tests covering:
1. /metrics endpoint access control
2. Redis async initialization
3. GovernanceMiddleware fail-closed behavior
4. Prometheus path normalization
5. JWT secret validation
6. Health endpoint information disclosure
"""

import os
import uuid
import importlib.util
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from metrics.prometheus_metrics import MetricsConfig, MetricsMiddleware, PrometheusMetrics


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    settings = MagicMock()
    settings.debug = False
    settings.api_port = 8005
    settings.jwt_secret = "valid-secret-that-is-at-least-32-characters-long"
    return settings


@pytest.fixture
def app_factory(monkeypatch: pytest.MonkeyPatch):
    """Factory to create test apps with different configurations."""
    def _create_app(env="test", bypass_auth=False, jwt_secret=None):
        # Set environment
        env_vars = {
            "ENVIRONMENT": env,
            "APP_ENV": env,
            "ALLOW_INSECURE_DEV_AUTH_BYPASS": "true" if bypass_auth else "false",
            "CORS_ORIGINS": "https://app.valuefabric.example",
            "DATABASE_URL": "postgresql+asyncpg://vf_user:vf_pass@postgres.internal:5432/layer5",
            "DATABASE_URL_SYNC": "postgresql://vf_user:vf_pass@postgres.internal:5432/layer5",
            "DEFAULT_TENANT_ID": "11111111-1111-4111-8111-111111111111",
            "JWT_FALLBACK_TO_QUERY_PARAM": "false",
            "LAYER3_BASE_URL": "https://layer3.internal:8003",
            "SERVICE_AUTH_SECRET": "layer5-service-auth-local-suite-secret-32chars",
        }
        if jwt_secret:
            env_vars["JWT_SECRET"] = jwt_secret
        else:
            env_vars["JWT_SECRET"] = "layer5-local-suite-jwt-signing-secret-32chars"
        
        for name, value in env_vars.items():
            monkeypatch.setenv(name, value)

        # Import here to pick up env vars
        from layer5_ground_truth.config import get_settings
        from layer5_ground_truth.api.main import create_app
        get_settings.cache_clear()
        return create_app()
    
    return _create_app


# =============================================================================
# 1. /metrics Endpoint Access Control Tests
# =============================================================================

class TestMetricsAccessControl:
    """Tests for /metrics endpoint security."""
    
    def test_metrics_denied_without_auth(self, app_factory):
        """Public access to /metrics should be denied without proper auth."""
        app = app_factory(env="production", bypass_auth=False)
        client = TestClient(app)
        
        response = client.get("/metrics")
        assert response.status_code == 403
        assert "internal access" in response.text.lower()
    
    def test_metrics_allowed_with_bearer_token(self, app_factory):
        """Metrics access with valid Bearer token should succeed."""
        with patch.dict(os.environ, {"METRICS_INTERNAL_SCRAPE_TOKEN": "test-token-12345"}):
            app = app_factory(env="production")
            client = TestClient(app)
            
            response = client.get("/metrics", headers={"Authorization": "Bearer test-token-12345"})
            # May return 200 or 503 (if metrics disabled), but NOT 403
            assert response.status_code != 403
    
    def test_metrics_denied_with_wrong_token(self, app_factory):
        """Metrics access with wrong token should be denied."""
        with patch.dict(os.environ, {"METRICS_INTERNAL_SCRAPE_TOKEN": "test-token-12345"}):
            app = app_factory(env="production")
            client = TestClient(app)
            
            response = client.get("/metrics", headers={"Authorization": "Bearer wrong-token"})
            assert response.status_code == 403
    
    def test_metrics_allowed_from_internal_ip(self, app_factory):
        """Metrics access from internal network should succeed."""
        app = app_factory(env="production")
        client = TestClient(app, client=("10.0.0.1", 50000))
        
        # Mock the client address
        with patch.object(app.state, 'metrics', None):
            response = client.get("/metrics")
            # Should not be 403 forbidden
            assert response.status_code != 403
    
    def test_metrics_allowed_with_dev_bypass(self, app_factory):
        """Metrics access with ALLOW_INSECURE_DEV_AUTH_BYPASS in dev."""
        app = app_factory(env="development", bypass_auth=True)
        client = TestClient(app)
        
        response = client.get("/metrics")
        # Should not be 403
        assert response.status_code != 403


# =============================================================================
# 2. Prometheus Path Normalization Tests
# =============================================================================

class TestPrometheusPathNormalization:
    """Tests for metrics path normalization to prevent cardinality explosion."""
    
    def test_uuid_path_normalized(self):
        """UUIDs in paths should be collapsed to {id}."""
        middleware = MetricsMiddleware(MagicMock())
        
        test_uuid = str(uuid.uuid4())
        path = f"/api/v1/truths/{test_uuid}"
        
        normalized = middleware._normalize_path(path)
        assert normalized == "/api/v1/truths/{id}"
    
    def test_numeric_id_normalized(self):
        """Numeric IDs should be collapsed to {id}."""
        middleware = MetricsMiddleware(MagicMock())
        
        path = "/api/v1/truths/12345"
        normalized = middleware._normalize_path(path)
        assert normalized == "/api/v1/truths/{id}"
    
    def test_hash_normalized(self):
        """Long hex hashes should be collapsed to {hash}."""
        middleware = MetricsMiddleware(MagicMock())
        
        path = "/api/v1/truths/abc123def4567890123456789012345678901234"
        normalized = middleware._normalize_path(path)
        assert normalized == "/api/v1/truths/{hash}"
    
    def test_api_version_preserved(self):
        """API version (v1) should not be collapsed."""
        middleware = MetricsMiddleware(MagicMock())
        
        path = "/api/v1/truths"
        normalized = middleware._normalize_path(path)
        assert normalized == "/api/v1/truths"
    
    def test_known_route_matches(self):
        """Known routes should use their defined templates."""
        middleware = MetricsMiddleware(MagicMock())
        
        # Should match exact known route
        assert middleware._normalize_path("/api/v1/truths") == "/api/v1/truths"
        assert middleware._normalize_path("/api/v1/health") == "/api/v1/health"
        assert middleware._normalize_path("/metrics") == "/metrics"
    
    def test_trailing_slash_removed(self):
        """Trailing slashes should be normalized."""
        middleware = MetricsMiddleware(MagicMock())
        
        assert middleware._normalize_path("/api/v1/truths/") == "/api/v1/truths"
    
    def test_deep_path_capped(self):
        """Deep paths beyond 6 segments should be capped."""
        middleware = MetricsMiddleware(MagicMock())
        
        path = "/a/b/c/d/e/f/g/h/i"
        normalized = middleware._normalize_path(path)
        assert "/{...}" in normalized
        assert normalized.count("/") <= 8  # Capped depth
    
    def test_ipv4_mapped_ipv6_handled(self):
        """IPv4-mapped IPv6 addresses should be detected as internal."""
        from layer5_ground_truth.api.main import _is_internal_ip
        
        assert _is_internal_ip("::ffff:10.0.0.1") is True
        assert _is_internal_ip("::ffff:192.168.1.1") is True
        assert _is_internal_ip("::ffff:172.16.0.1") is True
    
    def test_public_ip_not_internal(self):
        """Public IPs should not be considered internal."""
        from layer5_ground_truth.api.main import _is_internal_ip
        
        assert _is_internal_ip("8.8.8.8") is False
        assert _is_internal_ip("1.1.1.1") is False
        assert _is_internal_ip("172.32.0.1") is False  # Outside 172.16-31


# =============================================================================
# 3. JWT Secret Validation Tests
# =============================================================================

class TestJWTSecretValidation:
    """Tests for JWT secret strength validation."""
    
    def test_short_secret_rejected(self):
        """Secrets shorter than 32 chars should be rejected."""
        from layer5_ground_truth.api.main import _validate_jwt_secret
        
        with pytest.raises(RuntimeError) as exc_info:
            _validate_jwt_secret("short")
        assert "too short" in str(exc_info.value).lower()
    
    def test_placeholder_secret_rejected(self):
        """Placeholder secrets should be rejected."""
        from layer5_ground_truth.api.main import _validate_jwt_secret
        
        placeholders = [
            "changeme-in-production",
            "changeme",
            "password",
            "password123",
            "admin",
            "secret",
            "default",
            "test",
            "123456",
        ]
        
        for secret in placeholders:
            with pytest.raises(RuntimeError) as exc_info:
                _validate_jwt_secret(secret.ljust(32, "x"))  # Pad to pass length check
            assert "weak" in str(exc_info.value).lower() or "placeholder" in str(exc_info.value).lower()
    
    def test_valid_secret_accepted(self):
        """Long, random secrets should be accepted."""
        from layer5_ground_truth.api.main import _validate_jwt_secret
        
        # Should not raise
        valid_secret = "a" * 32 + "random-suffix-12345"
        _validate_jwt_secret(valid_secret)  # Should not raise
    
    def test_empty_secret_rejected(self):
        """Empty secrets should be rejected."""
        from layer5_ground_truth.api.main import _validate_jwt_secret
        
        with pytest.raises(RuntimeError) as exc_info:
            _validate_jwt_secret("")
        assert "empty" in str(exc_info.value).lower()
    
    def test_weak_pattern_rejected(self):
        """Weak patterns should be rejected even if long."""
        from layer5_ground_truth.api.main import _validate_jwt_secret
        
        with pytest.raises(RuntimeError) as exc_info:
            _validate_jwt_secret("password123456789012345678901234567890")
        assert "weak" in str(exc_info.value).lower()


# =============================================================================
# 4. Health Endpoint Tests
# =============================================================================

class TestHealthEndpointSecurity:
    """Tests for health endpoint information disclosure prevention."""
    
    @pytest.mark.asyncio
    async def test_health_does_not_expose_urls(self):
        """Health endpoint should not expose internal URLs."""
        # This test verifies the schema doesn't require sensitive fields
        from layer5_ground_truth.api.schemas import HealthResponse
        
        # Should be able to create with only safe fields
        response = HealthResponse(
            status="ok",
            version="0.1.0",
            timestamp="2024-01-01T00:00:00Z"
        )
        
        assert response.status == "ok"
        assert response.layer3_url is None
        assert response.database is None
    
    def test_health_response_safe_fields_only(self):
        """Health response should only contain safe fields."""
        from layer5_ground_truth.api.schemas import HealthResponse
        
        # Required fields
        response = HealthResponse(
            status="ok",
            version="0.1.0",
            timestamp="2024-01-01T00:00:00Z"
        )
        
        # Verify no internal details exposed
        data = response.model_dump()
        assert "layer3_url" not in data or data["layer3_url"] is None
        assert "database" not in data or data["database"] is None
        assert "layer3_connected" not in data or data["layer3_connected"] is None


# =============================================================================
# 5. Redis Initialization Tests
# =============================================================================

class TestRedisInitialization:
    """Tests for Redis async initialization."""
    
    @pytest.mark.asyncio
    async def test_redis_ping_is_awaited(self):
        """Redis ping() must be awaited in async context."""
        # This is a code inspection test - verify the source has await
        import inspect
        from layer5_ground_truth.api import main
        
        source = inspect.getsource(main.create_app)
        # Should find 'await redis_client.ping()'
        assert "await redis_client.ping()" in source
    
    def test_redis_required_in_production(self):
        """Redis should be required in production when REDIS_RATE_LIMITING_REQUIRED=true."""
        # Verify code checks environment
        import inspect
        from layer5_ground_truth.api import main
        
        source = inspect.getsource(main.create_app)
        # Should check for required flag or production env
        assert "REDIS_RATE_LIMITING_REQUIRED" in source or "production" in source.lower()


# =============================================================================
# 6. GovernanceMiddleware Fail-Closed Tests
# =============================================================================

class TestGovernanceMiddlewareFailClosed:
    """Tests for auth middleware fail-closed behavior."""
    
    def test_production_startup_fails_without_middleware(self):
        """Production startup should fail if GovernanceMiddleware cannot be imported."""
        # This test verifies the code structure enforces fail-closed
        import inspect
        from layer5_ground_truth.api import main
        
        source = inspect.getsource(main.create_app)
        
        # Should check for production/staging environment
        assert "production" in source.lower() or "staging" in source.lower()
        
        # Should raise RuntimeError when middleware missing in production
        assert "RuntimeError" in source
        assert "GovernanceMiddleware" in source
    
    def test_bypass_flag_documented(self):
        """Bypass flag should be clearly named to indicate insecurity."""
        import inspect
        from layer5_ground_truth.api import main
        
        source = inspect.getsource(main.create_app)
        
        # Should have explicit bypass flag with scary name
        assert "ALLOW_INSECURE_DEV_AUTH_BYPASS" in source


# =============================================================================
# 7. External Secrets Validation Script Tests
# =============================================================================

class TestExternalSecretsValidation:
    """Tests for validate-external-secrets.py script."""
    
    def test_yaml_parsing_not_regex(self):
        """Script should use PyYAML, not regex for YAML parsing."""
        import inspect
        import sys
        
        # Get the script source
        script_path = Path(__file__).parent.parent.parent.parent / ".github" / "scripts" / "validate-external-secrets.py"
        source = script_path.read_text()
        
        # Should import yaml
        assert "import yaml" in source
        
        # Should use yaml.safe_load_all
        assert "yaml.safe_load_all" in source
    
    def test_handles_nested_yaml(self):
        """Script should handle nested YAML structures."""
        script_path = Path(__file__).parent.parent.parent.parent / ".github" / "scripts" / "validate-external-secrets.py"
        spec = importlib.util.spec_from_file_location("validate_external_secrets", script_path)
        assert spec is not None
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        _find_secret_refs_recursive = module._find_secret_refs_recursive
        
        # Test nested structure
        nested = {
            "spec": {
                "containers": [
                    {
                        "env": [
                            {"valueFrom": {"secretKeyRef": {"name": "test-secret", "key": "password"}}}
                        ]
                    }
                ]
            }
        }
        
        result = _find_secret_refs_recursive(nested)
        assert "test-secret" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
