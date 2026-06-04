"""Tests for OpenTelemetry instrumentation and metrics.

Validates tracing setup, span creation, and metrics collection,
following the Layer 4 agent tracing patterns mentioned in AGENTS.md.
"""

from unittest.mock import MagicMock, patch

import pytest

from layer1_ingestion.crawler.telemetry import (
    CrawlMetrics,
    get_tracer,
    init_telemetry,
    start_batch_span,
    start_crawl_span,
    trace_method,
)


class TestInitTelemetry:
    """Test telemetry initialization."""
    
    @patch('layer1_ingestion.crawler.telemetry.trace')
    @patch('layer1_ingestion.crawler.telemetry.TracerProvider')
    @patch('layer1_ingestion.crawler.telemetry.BatchSpanProcessor')
    def test_init_creates_provider(self, mock_processor, mock_provider, mock_trace):
        """Test that init_telemetry creates and sets tracer provider."""
        mock_provider_instance = MagicMock()
        mock_provider.return_value = mock_provider_instance
        
        result = init_telemetry(
            service_name="test-service",
            service_version="1.0.0",
            attributes={"custom.attr": "value"}
        )
        
        # Verify provider was created with resource
        mock_provider.assert_called_once()
        mock_trace.set_tracer_provider.assert_called_once_with(mock_provider_instance)
        assert result == mock_provider_instance
        
    @patch('layer1_ingestion.crawler.telemetry.trace')
    def test_get_tracer_returns_instance(self, mock_trace):
        """Test that get_tracer returns a tracer."""
        mock_tracer = MagicMock()
        mock_trace.get_tracer.return_value = mock_tracer
        
        # Reset global _tracer to force re-initialization
        import layer1_ingestion.crawler.telemetry as telemetry
        telemetry._tracer = None
        
        result = get_tracer()
        
        mock_trace.get_tracer.assert_called()
        assert result == mock_tracer


class TestCrawlMetrics:
    """Test CrawlMetrics metrics collection."""
    
    def test_initial_metrics(self):
        """Test that initial metrics are zero."""
        metrics = CrawlMetrics()
        
        assert metrics.crawl_count == 0
        assert metrics.error_count == 0
        assert metrics.error_rate == 0.0
        assert metrics.avg_duration_ms == 0.0
        
    def test_record_successful_crawl(self):
        """Test recording a successful crawl."""
        metrics = CrawlMetrics()
        
        metrics.record_crawl(
            duration_ms=1500,
            success=True,
            blocked_resources=5,
            rate_limited=False,
        )
        
        assert metrics.crawl_count == 1
        assert metrics.error_count == 0
        assert metrics.error_rate == 0.0
        assert metrics.avg_duration_ms == 1500.0
        
    def test_record_failed_crawl(self):
        """Test recording a failed crawl."""
        metrics = CrawlMetrics()
        
        metrics.record_crawl(
            duration_ms=5000,
            success=False,
            blocked_resources=0,
            rate_limited=True,
        )
        
        assert metrics.crawl_count == 1
        assert metrics.error_count == 1
        assert metrics.error_rate == 1.0
        assert metrics.rate_limit_rate == 1.0
        
    def test_avg_duration_calculation(self):
        """Test average duration calculation across multiple crawls."""
        metrics = CrawlMetrics()
        
        metrics.record_crawl(duration_ms=1000, success=True)
        metrics.record_crawl(duration_ms=2000, success=True)
        metrics.record_crawl(duration_ms=3000, success=True)
        
        assert metrics.crawl_count == 3
        assert metrics.avg_duration_ms == 2000.0
        
    def test_to_dict_export(self):
        """Test metrics export to dictionary."""
        metrics = CrawlMetrics()
        metrics.record_crawl(duration_ms=1000, success=True, blocked_resources=3)
        
        result = metrics.to_dict()
        
        assert result["count"] == 1
        assert result["errors"] == 0
        assert result["blocked_resources"] == 3
        assert "avg_duration_ms" in result
        
    def test_error_rate_calculation(self):
        """Test error rate calculation with mixed results."""
        metrics = CrawlMetrics()
        
        # 2 successes, 2 failures
        for i in range(4):
            metrics.record_crawl(duration_ms=1000, success=(i % 2 == 0))
            
        assert metrics.error_rate == 0.5
        assert metrics.crawl_count == 4


class TestStartCrawlSpan:
    """Test crawl span context managers."""
    
    @patch('layer1_ingestion.crawler.telemetry.get_tracer')
    def test_start_crawl_span_yields_span(self, mock_get_tracer):
        """Test that start_crawl_span yields the span."""
        mock_span = MagicMock()
        mock_tracer = MagicMock()
        mock_tracer.start_as_current_span.return_value.__enter__ = MagicMock(return_value=mock_span)
        mock_tracer.start_as_current_span.return_value.__exit__ = MagicMock(return_value=False)
        mock_get_tracer.return_value = mock_tracer
        
        with start_crawl_span("https://example.com", "crawl_url") as span:
            assert span == mock_span
            
    @patch('layer1_ingestion.crawler.telemetry.get_tracer')
    def test_span_records_exception_on_error(self, mock_get_tracer):
        """Test that span records exception when error occurs."""
        mock_span = MagicMock()
        mock_tracer = MagicMock()
        mock_tracer.start_as_current_span.return_value.__enter__ = MagicMock(return_value=mock_span)
        mock_tracer.start_as_current_span.return_value.__exit__ = MagicMock(return_value=False)
        mock_get_tracer.return_value = mock_tracer
        
        with pytest.raises(ValueError):
            with start_crawl_span("https://example.com", "crawl_url"):
                raise ValueError("Test error")
                
        # Verify span recorded exception
        mock_span.set_status.assert_called()


class TestStartBatchSpan:
    """Test batch crawl span context managers."""
    
    @patch('layer1_ingestion.crawler.telemetry.get_tracer')
    def test_start_batch_span_sets_attributes(self, mock_get_tracer):
        """Test that batch span sets batch_size attribute."""
        mock_span = MagicMock()
        mock_tracer = MagicMock()
        mock_tracer.start_as_current_span.return_value.__enter__ = MagicMock(return_value=mock_span)
        mock_tracer.start_as_current_span.return_value.__exit__ = MagicMock(return_value=False)
        mock_get_tracer.return_value = mock_tracer
        
        with start_batch_span(10, "crawl_urls"):
            pass
            
        # Verify batch size was set
        mock_tracer.start_as_current_span.assert_called_once()
        call_kwargs = mock_tracer.start_as_current_span.call_args[1]
        assert call_kwargs["attributes"]["crawl.batch_size"] == 10


class TestTraceMethodDecorator:
    """Test the trace_method decorator."""
    
    @patch('layer1_ingestion.crawler.telemetry.get_tracer')
    def test_decorator_adds_span(self, mock_get_tracer):
        """Test that decorator adds tracing to methods."""
        mock_span = MagicMock()
        mock_tracer = MagicMock()
        mock_tracer.start_as_current_span.return_value.__enter__ = MagicMock(return_value=mock_span)
        mock_tracer.start_as_current_span.return_value.__exit__ = MagicMock(return_value=False)
        mock_get_tracer.return_value = mock_tracer
        
        class TestClass:
            @trace_method("test_operation")
            async def test_method(self, value):
                return value * 2
                
        obj = TestClass()
        result = obj.test_method(5)
        
        # Async test needs to be awaited, so we just check the decorator was applied
        import asyncio
        result = asyncio.run(obj.test_method(5))
        assert result == 10

