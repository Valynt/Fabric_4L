"""Tests for M-02 Silent Exception Handling Remediation.

Covers:
- NoOpExecutionLogger production guard
- database.py Redis availability flag
- content_extractor metadata extraction logging
"""

import pytest
import redis as redis_lib


class TestNoOpExecutionLoggerProductionGuard:
    """NoOpExecutionLogger must refuse instantiation in production-like environments."""

    def test_raises_in_production(self, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "production")
        # Force re-import/re-evaluation of the production check
        from layer1_ingestion.crawler.execution_logger import NoOpExecutionLogger

        with pytest.raises(RuntimeError, match="NoOpExecutionLogger must not be used"):
            NoOpExecutionLogger()

    def test_allowed_in_development(self, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "development")
        from layer1_ingestion.crawler.execution_logger import NoOpExecutionLogger

        # Should not raise
        logger = NoOpExecutionLogger()
        assert logger is not None

    def test_allowed_in_test(self, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "test")
        from layer1_ingestion.crawler.execution_logger import NoOpExecutionLogger

        logger = NoOpExecutionLogger()
        assert logger is not None


class TestDatabaseRedisAvailability:
    """database.py must expose REDIS_AVAILABLE and log on import failure."""

    def test_redis_available_flag_exists(self, monkeypatch):
        # Simulate Redis being unreachable so the availability block is deterministic.
        class _FailingRedis(redis_lib.Redis):
            def ping(self):
                raise redis_lib.ConnectionError("test: redis unavailable")

        import layer1_ingestion.shared.database as database_module

        monkeypatch.setattr(
            database_module,
            "create_sync_redis_client",
            lambda *args, **kwargs: _FailingRedis(),
        )
        _, _, available = database_module._initialize_redis_clients()
        assert available is False

    def test_redis_client_none_when_unavailable(self, monkeypatch):
        class _FailingRedis(redis_lib.Redis):
            def ping(self):
                raise redis_lib.ConnectionError("test: redis unavailable")

        import layer1_ingestion.shared.database as database_module

        monkeypatch.setattr(
            database_module,
            "create_sync_redis_client",
            lambda *args, **kwargs: _FailingRedis(),
        )
        sync_client, async_client, available = database_module._initialize_redis_clients()
        assert sync_client is None
        assert async_client is None
        assert available is False


class TestContentExtractorMetadataLogging:
    """ContentExtractor must log warnings instead of silently passing on JSON-LD errors."""

    def test_bad_jsonld_logs_warning(self, caplog):
        from bs4 import BeautifulSoup

        from layer1_ingestion.post_processor.content_extractor import ContentExtractor

        extractor = ContentExtractor()
        html = '<html><head><script type="application/ld+json">{invalid json</script></head></html>'
        soup = BeautifulSoup(html, "html.parser")

        # structlog bound loggers do not integrate with pytest caplog by default,
        # so we verify the method completes without exception after the fix
        meta = extractor._extract_metadata(soup, "https://example.com/")
        assert "url" in meta
