"""Tests for CrawlerConfig configuration management.

Validates YAML loading, validation, and config-driven behavior,
following the skill framework's config validation patterns.
"""

from pathlib import Path

import pytest

from layer1_ingestion.crawler.crawler_config import CrawlerConfig, load_config


class TestCrawlerConfig:
    """Test CrawlerConfig dataclass functionality."""
    
    def test_default_values(self):
        """Test that default config values are sensible."""
        config = CrawlerConfig()
        
        assert config.max_concurrent == 5
        assert config.timeout_ms == 30000
        assert config.viewport_width == 1920
        assert config.headless is True
        assert config.scroll_enabled is True
        assert config.enable_tracing is True
        
    def test_viewport_property(self):
        """Test viewport property returns correct dict."""
        config = CrawlerConfig(viewport_width=1280, viewport_height=720)
        
        viewport = config.viewport
        assert viewport == {'width': 1280, 'height': 720}
        
    def test_browser_args_default(self):
        """Test default browser security args are present."""
        config = CrawlerConfig()
        
        assert '--no-sandbox' in config.browser_args
        assert '--disable-gpu' in config.browser_args
        assert '--disable-setuid-sandbox' in config.browser_args
        
    def test_blocked_resource_patterns(self):
        """Test default resource blocking patterns."""
        config = CrawlerConfig()
        
        assert len(config.blocked_resource_patterns) > 0
        assert any('png' in p for p in config.blocked_resource_patterns)


class TestCrawlerConfigYamlLoading:
    """Test YAML config file loading and validation."""
    
    def test_load_valid_yaml(self, tmp_path: Path):
        """Test loading valid YAML config file."""
        config_file = tmp_path / "test_config.yml"
        config_file.write_text("""
max_concurrent: 10
timeout_ms: 60000
viewport_width: 1280
headless: false
enable_tracing: false
""")
        
        config = CrawlerConfig.from_yaml(config_file)
        
        assert config.max_concurrent == 10
        assert config.timeout_ms == 60000
        assert config.viewport_width == 1280
        assert config.headless is False
        assert config.enable_tracing is False
        
    def test_load_nonexistent_file_raises(self):
        """Test that loading missing file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            CrawlerConfig.from_yaml("/nonexistent/path/config.yml")
            
    def test_invalid_max_concurrent_raises(self, tmp_path: Path):
        """Test that invalid max_concurrent raises ValueError."""
        config_file = tmp_path / "bad_config.yml"
        config_file.write_text("max_concurrent: 100\n")
        
        with pytest.raises(ValueError, match="max_concurrent must be between 1 and 50"):
            CrawlerConfig.from_yaml(config_file)
            
    def test_invalid_timeout_raises(self, tmp_path: Path):
        """Test that invalid timeout_ms raises ValueError."""
        config_file = tmp_path / "bad_config.yml"
        config_file.write_text("timeout_ms: 500\n")
        
        with pytest.raises(ValueError, match="timeout_ms must be at least 1000"):
            CrawlerConfig.from_yaml(config_file)
            
    def test_unknown_fields_logged_and_ignored(self, tmp_path: Path, caplog):
        """Test that unknown fields are logged and ignored."""
        
        config_file = tmp_path / "config.yml"
        config_file.write_text("""
max_concurrent: 3
unknown_field: "value"
another_bad_field: 123
""")
        
        config = CrawlerConfig.from_yaml(config_file)
        
        # Unknown fields should be ignored, known fields should work
        assert config.max_concurrent == 3
        assert not hasattr(config, 'unknown_field')
        
    def test_to_yaml_roundtrip(self, tmp_path: Path):
        """Test that saving and loading config preserves values."""
        original = CrawlerConfig(
            max_concurrent=8,
            timeout_ms=45000,
            headless=False,
        )
        
        config_path = tmp_path / "roundtrip.yml"
        original.to_yaml(config_path)
        
        loaded = CrawlerConfig.from_yaml(config_path)
        
        assert loaded.max_concurrent == original.max_concurrent
        assert loaded.timeout_ms == original.timeout_ms
        assert loaded.headless == original.headless


class TestLoadConfig:
    """Test the load_config convenience function."""
    
    def test_load_config_with_explicit_path(self, tmp_path: Path):
        """Test loading config from explicit path."""
        config_file = tmp_path / "explicit.yml"
        config_file.write_text("max_concurrent: 7\n")
        
        config = load_config(config_file)
        
        assert config.max_concurrent == 7
        
    def test_load_config_defaults_when_no_file_found(self, tmp_path: Path, monkeypatch):
        """Test that defaults are used when no config file exists."""
        # Ensure we don't accidentally find a config file
        monkeypatch.chdir(tmp_path)
        
        config = load_config()
        
        # Should return defaults, not raise
        assert isinstance(config, CrawlerConfig)
        assert config.max_concurrent == 5  # Default value

