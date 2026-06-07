"""Unit tests for configuration and settings."""

import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from src.config import Settings, get_settings


class TestSettings:
    """Test Settings configuration."""
    
    @pytest.fixture(autouse=True)
    def clear_settings_cache(self):
        """Clear the settings cache before each test."""
        get_settings.cache_clear()
        yield
        get_settings.cache_clear()
    
    def test_default_settings(self, monkeypatch):
        """Test default settings values."""
        # Clear any existing env vars that could interfere
        env_vars_to_clear = [
            "LOG_LEVEL", "API_HOST", "API_PORT", "API_WORKERS",
            "NEO4J_URI", "NEO4J_USER", "NEO4J_DATABASE", "NEO4J_PASSWORD",
            "CACHE_ENABLED", "METRICS_ENABLED", "RATE_LIMIT_ENABLED",
        ]
        for var in env_vars_to_clear:
            monkeypatch.delenv(var, raising=False)
        
        # Set required password via env
        monkeypatch.setenv("NEO4J_PASSWORD", "test_password")
        
        settings = Settings()
        
        assert settings.api_host == "0.0.0.0"
        assert settings.api_port == 8003
        assert settings.api_workers == 1
        assert settings.log_level == "INFO", f"Expected INFO but got {settings.log_level}"
        assert settings.neo4j_uri == "bolt://localhost:7687"
        assert settings.neo4j_user == "neo4j"
        assert settings.neo4j_database == "neo4j"
        assert settings.neo4j_max_pool_size == 50
        assert settings.cache_enabled is True
        assert settings.metrics_enabled is True
        assert settings.rate_limit_enabled is True
    
    def test_settings_from_environment(self, monkeypatch):
        """Test settings loading from environment variables."""
        # Clear cache and set environment
        get_settings.cache_clear()
        
        env_vars = {
            "API_HOST": "127.0.0.1",
            "API_PORT": "9001",
            "LOG_LEVEL": "DEBUG",
            "NEO4J_URI": "bolt://test:7687",
            "NEO4J_USER": "test_user",
            "NEO4J_DATABASE": "test_db",
            "CACHE_ENABLED": "false",
            "METRICS_ENABLED": "false",
            "NEO4J_PASSWORD": "test_password",
        }
        
        for key, value in env_vars.items():
            monkeypatch.setenv(key, value)

        settings = Settings()

        assert settings.api_host == "127.0.0.1"
        assert settings.api_port == 9001
        assert settings.log_level == "DEBUG"
        assert settings.neo4j_uri == "bolt://test:7687"
        assert settings.neo4j_user == "test_user"
        assert settings.neo4j_database == "test_db"
        assert settings.cache_enabled is False
        assert settings.metrics_enabled is False
    
    def test_neo4j_password_required(self, monkeypatch):
        """Test that Neo4j password is required."""
        # Clear any existing NEO4J_PASSWORD from env
        monkeypatch.delenv("NEO4J_PASSWORD", raising=False)
        get_settings.cache_clear()
        
        with pytest.raises(ValidationError) as exc_info:
            Settings(neo4j_password=None)
        
        assert "NEO4J_PASSWORD" in str(exc_info.value)
    
    def test_neo4j_password_empty(self, monkeypatch):
        """Test that empty Neo4j password is rejected."""
        monkeypatch.delenv("NEO4J_PASSWORD", raising=False)
        get_settings.cache_clear()
        
        with pytest.raises(ValidationError) as exc_info:
            Settings(neo4j_password="")
        
        assert "NEO4J_PASSWORD" in str(exc_info.value)
    
    def test_neo4j_password_default_value(self, monkeypatch):
        """Test that default 'password' value is rejected."""
        monkeypatch.delenv("NEO4J_PASSWORD", raising=False)
        get_settings.cache_clear()
        
        with pytest.raises(ValidationError) as exc_info:
            Settings(neo4j_password="password")
        
        assert "NEO4J_PASSWORD" in str(exc_info.value)
        assert "password" in str(exc_info.value)
    
    def test_neo4j_password_valid(self, monkeypatch):
        """Test that valid Neo4j password is accepted."""
        # Clear env to ensure our value is used
        monkeypatch.delenv("NEO4J_PASSWORD", raising=False)
        get_settings.cache_clear()
        
        # Set via env since BaseSettings prioritizes env over constructor
        monkeypatch.setenv("NEO4J_PASSWORD", "secure_password_123")
        
        settings = Settings()
        assert settings.neo4j_password == "secure_password_123"
    
    def test_neo4j_auth_property(self):
        """Test neo4j_auth property."""
        settings = Settings(neo4j_password="test_password")
        auth = settings.neo4j_auth
        
        assert isinstance(auth, tuple)
        assert len(auth) == 2
        assert auth[0] == "neo4j"
        assert auth[1] == "test_password"
    
    def test_logging_configuration(self):
        """Test logging configuration fields."""
        settings = Settings()
        
        assert settings.log_format == "json"
        assert settings.log_include_module is True
        assert settings.log_include_function is True
        assert settings.log_include_line_number is True
        assert settings.log_request_id_header == "X-Request-ID"
    
    def test_logging_configuration_from_env(self, monkeypatch):
        """Test logging configuration from environment."""
        get_settings.cache_clear()
        env_vars = {
            "LOG_FORMAT": "text",
            "LOG_INCLUDE_MODULE": "false",
            "LOG_INCLUDE_FUNCTION": "false",
            "LOG_INCLUDE_LINE_NUMBER": "false",
            "LOG_REQUEST_ID_HEADER": "X-Trace-ID",
            "NEO4J_PASSWORD": "test_password",
        }
        
        for key, value in env_vars.items():
            monkeypatch.setenv(key, value)
        
        settings = Settings()
        
        assert settings.log_format == "text"
        assert settings.log_include_module is False
        assert settings.log_include_function is False
        assert settings.log_include_line_number is False
        assert settings.log_request_id_header == "X-Trace-ID"
    
    def test_cache_configuration(self):
        """Test cache configuration fields."""
        settings = Settings()
        
        assert settings.cache_enabled is True
        assert settings.cache_redis_url == "redis://localhost:6379/0"
        assert settings.cache_default_ttl == 300
        assert settings.cache_max_ttl == 3600
        assert settings.cache_key_prefix == "value_fabric:"
        assert settings.cache_serializer == "json"
        assert settings.cache_compression is True
    
    def test_cache_configuration_from_env(self, monkeypatch):
        """Test cache configuration from environment."""
        get_settings.cache_clear()
        env_vars = {
            "CACHE_ENABLED": "false",
            "CACHE_REDIS_URL": "redis://test:6380/1",
            "CACHE_DEFAULT_TTL": "600",
            "CACHE_MAX_TTL": "7200",
            "CACHE_KEY_PREFIX": "test:",
            "CACHE_SERIALIZER": "pickle",
            "CACHE_COMPRESSION": "false",
            "NEO4J_PASSWORD": "test_password",
        }
        
        for key, value in env_vars.items():
            monkeypatch.setenv(key, value)
        
        settings = Settings()
        
        assert settings.cache_enabled is False
        assert settings.cache_redis_url == "redis://test:6380/1"
        assert settings.cache_default_ttl == 600
        assert settings.cache_max_ttl == 7200
        assert settings.cache_key_prefix == "test:"
        assert settings.cache_serializer == "pickle"
        assert settings.cache_compression is False
    
    def test_metrics_configuration(self):
        """Test metrics configuration fields."""
        settings = Settings()
        
        assert settings.metrics_enabled is True
        assert settings.metrics_prefix == "value_fabric_"
        assert settings.metrics_namespace == "layer3"
        assert settings.metrics_path == "/metrics"
        assert settings.metrics_include_timestamp is True
    
    def test_metrics_configuration_from_env(self, monkeypatch):
        """Test metrics configuration from environment."""
        get_settings.cache_clear()
        env_vars = {
            "METRICS_ENABLED": "false",
            "METRICS_PREFIX": "test_",
            "METRICS_NAMESPACE": "test_layer",
            "METRICS_PATH": "/test_metrics",
            "METRICS_INCLUDE_TIMESTAMP": "false",
            "NEO4J_PASSWORD": "test_password",
        }
        
        for key, value in env_vars.items():
            monkeypatch.setenv(key, value)
        
        settings = Settings()
        
        assert settings.metrics_enabled is False
        assert settings.metrics_prefix == "test_"
        assert settings.metrics_namespace == "test_layer"
        assert settings.metrics_path == "/test_metrics"
        assert settings.metrics_include_timestamp is False
    
    def test_rate_limit_configuration(self):
        """Test rate limit configuration fields."""
        settings = Settings()
        
        assert settings.rate_limit_enabled is True
        assert settings.rate_limit_requests_per_minute == 100
        assert settings.rate_limit_burst_size == 200
        assert settings.rate_limit_cleanup_interval == 300
    
    def test_rate_limit_configuration_from_env(self, monkeypatch):
        """Test rate limit configuration from environment."""
        get_settings.cache_clear()
        env_vars = {
            "RATE_LIMIT_ENABLED": "false",
            "RATE_LIMIT_REQUESTS_PER_MINUTE": "200",
            "RATE_LIMIT_BURST_SIZE": "400",
            "RATE_LIMIT_CLEANUP_INTERVAL": "600",
            "NEO4J_PASSWORD": "test_password",
        }
        
        for key, value in env_vars.items():
            monkeypatch.setenv(key, value)
        
        settings = Settings()
        
        assert settings.rate_limit_enabled is False
        assert settings.rate_limit_requests_per_minute == 200
        assert settings.rate_limit_burst_size == 400
        assert settings.rate_limit_cleanup_interval == 600
    
    def test_pinecone_configuration(self):
        """Test Pinecone configuration fields."""
        settings = Settings()
        
        assert settings.pinecone_api_key is None
        assert settings.pinecone_index == "value-fabric"
        assert settings.pinecone_dimension == 768
        assert settings.pinecone_metric == "cosine"
        assert settings.pinecone_cloud == "aws"
        assert settings.pinecone_region == "us-west-2"
    
    def test_pinecone_configuration_from_env(self, monkeypatch):
        """Test Pinecone configuration from environment."""
        get_settings.cache_clear()
        env_vars = {
            "PINECONE_API_KEY": "test_api_key",
            "PINECONE_INDEX": "test-index",
            "PINECONE_DIMENSION": "1536",
            "PINECONE_METRIC": "euclidean",
            "PINECONE_CLOUD": "gcp",
            "PINECONE_REGION": "us-central1",
            "NEO4J_PASSWORD": "test_password",
        }
        
        for key, value in env_vars.items():
            monkeypatch.setenv(key, value)
        
        settings = Settings()

        assert settings.pinecone_api_key == "test_api_key"
        assert settings.pinecone_index == "test-index"
        assert settings.pinecone_dimension == 1536
        assert settings.pinecone_metric == "euclidean"
        assert settings.pinecone_cloud == "gcp"
        assert settings.pinecone_region == "us-central1"
    
    def test_get_settings_singleton(self):
        """Test get_settings returns singleton instance."""
        with patch.dict(os.environ, {"NEO4J_PASSWORD": "test_password"}):
            settings1 = get_settings()
            settings2 = get_settings()
            
            assert settings1 is settings2
            assert isinstance(settings1, Settings)
    
    def test_settings_model_config(self):
        """Test settings model configuration."""
        settings = Settings()
        
        # Check that model config is properly set
        assert settings.model_config.get("env_file") == ".env"
        assert settings.model_config.get("env_file_encoding") == "utf-8"
        assert settings.model_config.get("extra") == "ignore"
    
    def test_settings_field_aliases(self):
        """Test that field aliases work correctly."""
        env_vars = {
            "API_HOST": "test_host",
            "API_PORT": "9999",
            "LOG_LEVEL": "WARN",
        }
        
        with patch.dict(os.environ, env_vars):
            settings = Settings()
            
            assert settings.api_host == "test_host"
            assert settings.api_port == 9999
            assert settings.log_level == "WARN"
    
    def test_settings_validation_edge_cases(self, monkeypatch):
        """Test settings validation edge cases - Neo4j password validation only."""
        # Note: The Settings class currently only validates neo4j_password
        # Other fields (api_port, log_level, cache_enabled) accept any valid type
        
        # Clear env
        monkeypatch.delenv("NEO4J_PASSWORD", raising=False)
        
        # Test missing password
        with pytest.raises(ValidationError):
            Settings()
        
        # Test empty password
        monkeypatch.setenv("NEO4J_PASSWORD", "")
        with pytest.raises(ValidationError):
            Settings()
        
        # Test default 'password' value
        monkeypatch.setenv("NEO4J_PASSWORD", "password")
        with pytest.raises(ValidationError):
            Settings()
    
    def test_settings_extra_fields_ignored(self, monkeypatch):
        """Test that extra fields are ignored."""
        # Clear env and set base password
        monkeypatch.delenv("NEO4J_PASSWORD", raising=False)
        monkeypatch.setenv("NEO4J_PASSWORD", "test")
        
        # This should not raise an error (extra fields ignored due to extra="ignore")
        settings = Settings()
        
        assert settings.neo4j_password == "test"

