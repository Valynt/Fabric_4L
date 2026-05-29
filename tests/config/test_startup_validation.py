"""
Startup and Control Hardening Tests (Suite 10).

Verifies that production deployments fail fast when critical security
controls are misconfigured, preventing silent degradation of tenant
isolation, authentication, or audit capabilities.

These tests catch the class of failures that tests often miss:
- Missing Redis URL when Redis is required
- Wildcard CORS in production
- Missing JWT issuer/audience or signing config
- Missing audit sink or required dependency
- Startup summary reports active control mode correctly

Test Strategy:
- Mock environment variables to simulate misconfigurations
- Attempt to initialize application components
- Assert that startup fails with clear error messages
- Verify control mode reporting is accurate
"""

import os
import pytest
from unittest.mock import patch, MagicMock
from typing import Any


# ═══════════════════════════════════════════════════════════════════════════
# Test Suite: Production Environment Validation
# ═══════════════════════════════════════════════════════════════════════════


class TestProductionRedisRequirement:
    """Verify Redis is required in production mode."""
    
    @pytest.mark.asyncio
    async def test_prod_boot_fails_with_missing_redis_url(self):
        """Production boot must fail if REDIS_URL is missing.
        
        Rationale: Rate limiting and cache isolation depend on Redis.
        Missing Redis in prod could silently disable tenant-scoped rate limits.
        """
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "REDIS_URL": "",  # Missing
            "JWT_SECRET": "test-secret",
            "DATABASE_URL": "postgresql://test",
        }, clear=True):
            # Import after env is patched
            with pytest.raises(ValueError, match="REDIS_URL.*required.*production"):
                from value_fabric.shared.rate_limiting.tenant_rate_limiter import validate_redis_config
                validate_redis_config()
    
    @pytest.mark.asyncio
    async def test_prod_boot_fails_with_invalid_redis_url(self):
        """Production boot must fail if REDIS_URL is malformed.
        
        Rationale: Malformed URL could cause silent fallback to in-memory cache,
        breaking tenant isolation in multi-worker deployments.
        """
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "REDIS_URL": "not-a-valid-url",
            "JWT_SECRET": "test-secret",
        }, clear=True):
            with pytest.raises(ValueError, match="Invalid REDIS_URL"):
                from value_fabric.shared.rate_limiting.tenant_rate_limiter import validate_redis_config
                validate_redis_config()
    
    @pytest.mark.asyncio
    async def test_dev_mode_allows_missing_redis_with_warning(self):
        """Development mode should warn but not fail if Redis is missing.
        
        Rationale: Developers should be able to run locally without Redis,
        but must be warned about degraded behavior.
        """
        with patch.dict(os.environ, {
            "ENVIRONMENT": "development",
            "REDIS_URL": "",
        }, clear=True):
            with patch("logging.Logger.warning") as mock_warning:
                from value_fabric.shared.rate_limiting.tenant_rate_limiter import validate_redis_config
                # Should not raise, but should warn
                try:
                    validate_redis_config()
                except ValueError:
                    pytest.fail("Development mode should not fail on missing Redis")
                
                # Verify warning was logged
                assert mock_warning.called
                warning_msg = str(mock_warning.call_args)
                assert "Redis" in warning_msg or "memory" in warning_msg.lower()


class TestProductionCORSValidation:
    """Verify CORS is properly restricted in production."""
    
    def test_prod_boot_fails_with_wildcard_cors(self):
        """Production boot must fail if CORS allows all origins.
        
        Rationale: Wildcard CORS (*) in production allows any website to
        make authenticated requests, bypassing same-origin policy.
        """
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "CORS_ORIGINS": "*",
            "JWT_SECRET": "test-secret",
        }, clear=True):
            with pytest.raises(ValueError, match="CORS.*wildcard.*production"):
                from value_fabric.shared.security.config import validate_cors_config
                validate_cors_config()
    
    def test_prod_boot_fails_with_http_cors_origin(self):
        """Production boot must fail if CORS allows HTTP origins.
        
        Rationale: HTTP origins in production expose tokens to MITM attacks.
        """
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "CORS_ORIGINS": "http://example.com,https://app.example.com",
            "JWT_SECRET": "test-secret",
        }, clear=True):
            with pytest.raises(ValueError, match="HTTP.*CORS.*production"):
                from value_fabric.shared.security.config import validate_cors_config
                validate_cors_config()
    
    def test_prod_accepts_valid_https_cors_origins(self):
        """Production should accept properly configured HTTPS CORS origins."""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "CORS_ORIGINS": "https://app.example.com,https://admin.example.com",
            "JWT_SECRET": "test-secret",
        }, clear=True):
            from value_fabric.shared.security.config import validate_cors_config
            # Should not raise
            validate_cors_config()
    
    def test_dev_mode_allows_wildcard_cors_with_warning(self):
        """Development mode should warn but allow wildcard CORS."""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "development",
            "CORS_ORIGINS": "*",
        }, clear=True):
            with patch("logging.Logger.warning") as mock_warning:
                from value_fabric.shared.security.config import validate_cors_config
                # Should not raise
                validate_cors_config()
                
                # Verify warning was logged
                assert mock_warning.called
                warning_msg = str(mock_warning.call_args)
                assert "CORS" in warning_msg or "wildcard" in warning_msg.lower()


class TestProductionJWTConfiguration:
    """Verify JWT configuration is complete in production."""
    
    def test_prod_boot_fails_with_missing_jwt_secret(self):
        """Production boot must fail if JWT_SECRET is missing.
        
        Rationale: Missing JWT secret means tokens cannot be verified,
        allowing unauthenticated access.
        """
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "JWT_SECRET": "",
            "REDIS_URL": "redis://localhost:6379",
        }, clear=True):
            with pytest.raises(ValueError, match="JWT_SECRET.*required.*production"):
                from value_fabric.shared.identity.dependencies import validate_jwt_config
                validate_jwt_config()
    
    def test_prod_boot_fails_with_weak_jwt_secret(self):
        """Production boot must fail if JWT_SECRET is too short.
        
        Rationale: Weak secrets are vulnerable to brute force attacks.
        """
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "JWT_SECRET": "short",  # Too short
            "REDIS_URL": "redis://localhost:6379",
        }, clear=True):
            with pytest.raises(ValueError, match="JWT_SECRET.*at least 32"):
                from value_fabric.shared.identity.dependencies import validate_jwt_config
                validate_jwt_config()
    
    def test_prod_boot_fails_with_missing_jwt_issuer(self):
        """Production boot must fail if JWT_ISSUER is missing.
        
        Rationale: Missing issuer allows tokens from any source to be accepted.
        """
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "JWT_SECRET": "a" * 32,
            "JWT_ISSUER": "",
            "REDIS_URL": "redis://localhost:6379",
        }, clear=True):
            with pytest.raises(ValueError, match="JWT_ISSUER.*required.*production"):
                from value_fabric.shared.identity.dependencies import validate_jwt_config
                validate_jwt_config()
    
    def test_prod_boot_fails_with_missing_jwt_audience(self):
        """Production boot must fail if JWT_AUDIENCE is missing.
        
        Rationale: Missing audience allows tokens intended for other services
        to be accepted.
        """
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "JWT_SECRET": "a" * 32,
            "JWT_ISSUER": "https://auth.example.com",
            "JWT_AUDIENCE": "",
            "REDIS_URL": "redis://localhost:6379",
        }, clear=True):
            with pytest.raises(ValueError, match="JWT_AUDIENCE.*required.*production"):
                from value_fabric.shared.identity.dependencies import validate_jwt_config
                validate_jwt_config()
    
    def test_prod_accepts_valid_jwt_config(self):
        """Production should accept properly configured JWT settings."""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "JWT_SECRET": "a" * 32,
            "JWT_ISSUER": "https://auth.example.com",
            "JWT_AUDIENCE": "https://api.example.com",
            "REDIS_URL": "redis://localhost:6379",
        }, clear=True):
            from value_fabric.shared.identity.dependencies import validate_jwt_config
            # Should not raise
            validate_jwt_config()


class TestProductionAuditConfiguration:
    """Verify audit sink is configured in production."""
    
    @pytest.mark.asyncio
    async def test_prod_boot_fails_with_missing_audit_sink(self):
        """Production boot must fail if audit sink is not configured.
        
        Rationale: Missing audit sink means privileged operations are not
        logged, violating compliance requirements.
        """
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "AUDIT_SINK_URL": "",
            "JWT_SECRET": "a" * 32,
            "REDIS_URL": "redis://localhost:6379",
        }, clear=True):
            with pytest.raises(ValueError, match="AUDIT_SINK.*required.*production"):
                from value_fabric.shared.audit.emitter import validate_audit_config
                validate_audit_config()
    
    @pytest.mark.asyncio
    async def test_prod_boot_fails_if_audit_sink_unreachable(self):
        """Production boot must fail if audit sink is unreachable.
        
        Rationale: Unreachable audit sink means events will be lost,
        creating compliance gaps.
        """
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "AUDIT_SINK_URL": "https://audit.example.com/events",
            "AUDIT_SINK_TIMEOUT": "5",
            "JWT_SECRET": "a" * 32,
            "REDIS_URL": "redis://localhost:6379",
        }, clear=True):
            with patch("httpx.AsyncClient.post") as mock_post:
                mock_post.side_effect = Exception("Connection refused")
                
                with pytest.raises(ValueError, match="Audit sink.*unreachable"):
                    from value_fabric.shared.audit.emitter import validate_audit_config
                    await validate_audit_config()
    
    @pytest.mark.asyncio
    async def test_dev_mode_allows_missing_audit_sink_with_warning(self):
        """Development mode should warn but allow missing audit sink."""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "development",
            "AUDIT_SINK_URL": "",
        }, clear=True):
            with patch("logging.Logger.warning") as mock_warning:
                from value_fabric.shared.audit.emitter import validate_audit_config
                # Should not raise
                await validate_audit_config()
                
                # Verify warning was logged
                assert mock_warning.called
                warning_msg = str(mock_warning.call_args)
                assert "audit" in warning_msg.lower()


class TestStartupControlModeReporting:
    """Verify startup summary reports active control mode correctly."""
    
    def test_startup_summary_reports_production_mode(self):
        """Startup summary must clearly indicate production mode is active.
        
        Rationale: Operators need to verify production controls are enabled.
        """
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "JWT_SECRET": "a" * 32,
            "JWT_ISSUER": "https://auth.example.com",
            "JWT_AUDIENCE": "https://api.example.com",
            "REDIS_URL": "redis://localhost:6379",
            "AUDIT_SINK_URL": "https://audit.example.com",
            "CORS_ORIGINS": "https://app.example.com",
        }, clear=True):
            from value_fabric.shared.security.config import get_startup_summary
            summary = get_startup_summary()
            
            assert summary["environment"] == "production"
            assert summary["redis_enabled"] is True
            assert summary["audit_enabled"] is True
            assert summary["cors_mode"] == "restricted"
            assert summary["jwt_validation"] == "strict"
    
    def test_startup_summary_reports_development_mode(self):
        """Startup summary must clearly indicate development mode is active."""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "development",
            "REDIS_URL": "",
            "AUDIT_SINK_URL": "",
            "CORS_ORIGINS": "*",
        }, clear=True):
            from value_fabric.shared.security.config import get_startup_summary
            summary = get_startup_summary()
            
            assert summary["environment"] == "development"
            assert summary["redis_enabled"] is False
            assert summary["audit_enabled"] is False
            assert summary["cors_mode"] == "permissive"
            assert "WARNING" in summary.get("warnings", [])
    
    def test_startup_summary_lists_degraded_controls(self):
        """Startup summary must list any degraded or disabled controls.
        
        Rationale: Operators need to know which controls are not active.
        """
        with patch.dict(os.environ, {
            "ENVIRONMENT": "staging",
            "REDIS_URL": "",  # Degraded
            "AUDIT_SINK_URL": "https://audit.example.com",
            "CORS_ORIGINS": "https://app.example.com",
        }, clear=True):
            from value_fabric.shared.security.config import get_startup_summary
            summary = get_startup_summary()
            
            degraded = summary.get("degraded_controls", [])
            assert "redis" in [c.lower() for c in degraded]
            assert "rate_limiting" in [c.lower() for c in degraded]


# ═══════════════════════════════════════════════════════════════════════════
# Test Suite: Database Connection Validation
# ═══════════════════════════════════════════════════════════════════════════


class TestProductionDatabaseConfiguration:
    """Verify database is properly configured in production."""
    
    def test_prod_boot_fails_with_missing_database_url(self):
        """Production boot must fail if DATABASE_URL is missing.
        
        Rationale: Missing database URL means application cannot start.
        """
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "DATABASE_URL": "",
            "JWT_SECRET": "a" * 32,
            "REDIS_URL": "redis://localhost:6379",
        }, clear=True):
            with pytest.raises(ValueError, match="DATABASE_URL.*required"):
                from value_fabric.shared.security.config import validate_database_config
                validate_database_config()
    
    def test_prod_boot_fails_with_sqlite_database(self):
        """Production boot must fail if using SQLite.
        
        Rationale: SQLite does not support RLS or multi-tenant isolation.
        """
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "DATABASE_URL": "sqlite:///./test.db",
            "JWT_SECRET": "a" * 32,
            "REDIS_URL": "redis://localhost:6379",
        }, clear=True):
            with pytest.raises(ValueError, match="SQLite.*not supported.*production"):
                from value_fabric.shared.security.config import validate_database_config
                validate_database_config()
    
    def test_prod_boot_fails_with_missing_sslmode(self):
        """Production boot must fail if DATABASE_URL omits sslmode.
        
        Rationale: TLS mode must be explicit to fail closed on transport security.
        """
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "DATABASE_URL": "postgresql://user:pass@localhost:5432/db",  # No sslmode
            "JWT_SECRET": "a" * 32,
            "REDIS_URL": "redis://localhost:6379",
        }, clear=True):
            with pytest.raises(ValueError, match="sslmode=require or stronger"):
                from value_fabric.shared.security.config import validate_database_config
                validate_database_config()

    @pytest.mark.parametrize("sslmode", ["require", "verify-ca", "verify-full"])
    def test_prod_boot_accepts_approved_sslmodes(self, sslmode: str):
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "DATABASE_URL": f"postgresql://user:pass@db.internal:5432/db?sslmode={sslmode}",
            "JWT_SECRET": "a" * 32,
            "REDIS_URL": "redis://localhost:6379",
        }, clear=True):
            from value_fabric.shared.security.config import validate_database_config
            validate_database_config()

    def test_prod_boot_fails_if_database_url_sync_missing_sslmode(self):
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "DATABASE_URL": "postgresql://user:pass@db.internal:5432/db?sslmode=require",
            "DATABASE_URL_SYNC": "postgresql://user:pass@db.internal:5432/db_sync",
            "JWT_SECRET": "a" * 32,
            "REDIS_URL": "redis://localhost:6379",
        }, clear=True):
            with pytest.raises(ValueError, match="DATABASE_URL_SYNC.*sslmode=require or stronger"):
                from value_fabric.shared.security.config import validate_database_config
                validate_database_config()

    def test_prod_boot_accepts_sslmode_query_key_case_insensitive(self):
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "DATABASE_URL": "postgresql://user:pass@db.internal:5432/db?SSLMODE=verify-full",
            "JWT_SECRET": "a" * 32,
            "REDIS_URL": "redis://localhost:6379",
        }, clear=True):
            from value_fabric.shared.security.config import validate_database_config
            validate_database_config()


# ═══════════════════════════════════════════════════════════════════════════
# Negative Path Scenarios
# ═══════════════════════════════════════════════════════════════════════════


class TestNegativePathStartupScenarios:
    """Test startup behavior under adverse conditions."""
    
    def test_conflicting_environment_variables(self):
        """Startup must fail if environment variables conflict.
        
        Example: ENVIRONMENT=production but DEBUG=true
        """
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "DEBUG": "true",
            "JWT_SECRET": "a" * 32,
            "REDIS_URL": "redis://localhost:6379",
        }, clear=True):
            with pytest.raises(ValueError, match="DEBUG.*production"):
                from value_fabric.shared.security.config import validate_environment_config
                validate_environment_config()
    
    def test_startup_with_all_controls_disabled(self):
        """Startup must fail if all security controls are disabled in production.
        
        Rationale: This indicates a catastrophic misconfiguration.
        """
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "REDIS_URL": "",
            "AUDIT_SINK_URL": "",
            "JWT_SECRET": "",
            "CORS_ORIGINS": "*",
        }, clear=True):
            with pytest.raises(ValueError, match="All security controls.*disabled"):
                from value_fabric.shared.security.config import validate_all_controls
                validate_all_controls()
    
    def test_startup_validation_runs_before_server_start(self):
        """Validation must run during import/init, not on first request.
        
        Rationale: Failing on first request means misconfigured app is running.
        """
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "REDIS_URL": "",
        }, clear=True):
            # Validation should fail during import
            with pytest.raises(ValueError):
                # This import should trigger validation
                import services.layer4_agents.src.main
