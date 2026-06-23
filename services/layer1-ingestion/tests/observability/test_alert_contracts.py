"""Tests for alert contracts validating required observability signals.

Tests validate that required observability signals exist (metric names + labels):
- Privileged bypass metric emitted with mode label
- Retry events metric emitted with stage and reason labels
- URLs blocked metric emitted with reason label
- Crawl path distribution metric emitted with path label
- Stuck jobs gauge reflects non-terminal job counts
- Health status gauge reflects component health
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch
from prometheus_client import CollectorRegistry

from layer1_ingestion.metrics.prometheus_metrics import (
    PrometheusMetrics,
    MetricsConfig,
    get_metrics,
    initialize_metrics,
)


class TestPrivilegedBypassMetric:
    """Test privileged_db_session_activations_total metric."""

    def test_privileged_bypass_metric_exists(self):
        """privileged_db_session_activations_total metric should exist."""
        config = MetricsConfig()
        metrics = PrometheusMetrics(config)

        assert "privileged_db_session_activations_total" in metrics._metrics

    def test_privileged_bypass_metric_has_mode_label(self):
        """Metric should have mode label."""
        config = MetricsConfig()
        metrics = PrometheusMetrics(config)

        metric = metrics._metrics["privileged_db_session_activations_total"]
        assert "mode" in metric._labelnames

    def test_privileged_bypass_metric_emitted_on_bypass(self):
        """Metric should be emitted when require_tenant=False is used."""
        config = MetricsConfig()
        metrics = PrometheusMetrics(config)

        # Simulate bypass activation
        metrics.increment_privileged_db_session_activation(mode="bypass")

        # Verify metric was incremented
        metric = metrics._metrics["privileged_db_session_activations_total"]
        samples = list(metric.collect())[0].samples
        bypass_samples = [s for s in samples if s.labels.get("mode") == "bypass"]
        assert len(bypass_samples) > 0
        assert bypass_samples[0].value > 0


class TestRetryEventsMetric:
    """Test retry_events_total metric."""

    def test_retry_events_metric_exists(self):
        """retry_events_total metric should exist."""
        config = MetricsConfig()
        metrics = PrometheusMetrics(config)

        assert "retry_events_total" in metrics._metrics

    def test_retry_events_metric_has_stage_and_reason_labels(self):
        """Metric should have stage and reason labels."""
        config = MetricsConfig()
        metrics = PrometheusMetrics(config)

        metric = metrics._metrics["retry_events_total"]
        assert "stage" in metric._labelnames
        assert "reason" in metric._labelnames

    def test_retry_events_metric_emitted_on_retry(self):
        """Metric should be emitted on Celery retry."""
        config = MetricsConfig()
        metrics = PrometheusMetrics(config)

        # Simulate retry event
        metrics.increment_retry_event(stage="compliance_check", reason="stage_failure")

        # Verify metric was incremented
        metric = metrics._metrics["retry_events_total"]
        samples = list(metric.collect())[0].samples
        retry_samples = [
            s
            for s in samples
            if s.labels.get("stage") == "compliance_check"
            and s.labels.get("reason") == "stage_failure"
        ]
        assert len(retry_samples) > 0
        assert retry_samples[0].value > 0


class TestURLsBlockedMetric:
    """Test urls_blocked_total metric."""

    def test_urls_blocked_metric_exists(self):
        """urls_blocked_total metric should exist."""
        config = MetricsConfig()
        metrics = PrometheusMetrics(config)

        assert "urls_blocked_total" in metrics._metrics

    def test_urls_blocked_metric_has_reason_label(self):
        """Metric should have reason label."""
        config = MetricsConfig()
        metrics = PrometheusMetrics(config)

        metric = metrics._metrics["urls_blocked_total"]
        assert "reason" in metric._labelnames

    def test_urls_blocked_metric_emitted_on_block(self):
        """Metric should be emitted when URL is blocked."""
        config = MetricsConfig()
        metrics = PrometheusMetrics(config)

        # Simulate URL block
        metrics.increment_url_blocked(reason="robots_txt")

        # Verify metric was incremented
        metric = metrics._metrics["urls_blocked_total"]
        samples = list(metric.collect())[0].samples
        blocked_samples = [s for s in samples if s.labels.get("reason") == "robots_txt"]
        assert len(blocked_samples) > 0
        assert blocked_samples[0].value > 0


class TestCrawlPathDistributionMetric:
    """Test crawl_path_distribution metric."""

    def test_crawl_path_distribution_metric_exists(self):
        """crawl_path_distribution metric should exist."""
        config = MetricsConfig()
        metrics = PrometheusMetrics(config)

        assert "crawl_path_distribution" in metrics._metrics

    def test_crawl_path_distribution_metric_has_path_label(self):
        """Metric should have path label."""
        config = MetricsConfig()
        metrics = PrometheusMetrics(config)

        metric = metrics._metrics["crawl_path_distribution"]
        assert "path" in metric._labelnames

    def test_crawl_path_distribution_metric_emitted_on_crawl(self):
        """Metric should be emitted on crawl path decision."""
        config = MetricsConfig()
        metrics = PrometheusMetrics(config)

        # Simulate crawl path decision
        metrics.increment_crawl_path(path="fast")

        # Verify metric was incremented
        metric = metrics._metrics["crawl_path_distribution"]
        samples = list(metric.collect())[0].samples
        path_samples = [s for s in samples if s.labels.get("path") == "fast"]
        assert len(path_samples) > 0
        assert path_samples[0].value > 0


class TestStuckJobsGauge:
    """Test stuck_jobs gauge."""

    def test_stuck_jobs_gauge_exists(self):
        """stuck_jobs gauge should exist."""
        config = MetricsConfig()
        metrics = PrometheusMetrics(config)

        assert "stuck_jobs" in metrics._metrics

    def test_stuck_jobs_gauge_has_stage_label(self):
        """Gauge should have stage label."""
        config = MetricsConfig()
        metrics = PrometheusMetrics(config)

        metric = metrics._metrics["stuck_jobs"]
        assert "stage" in metric._labelnames

    def test_stuck_jobs_gauge_reflects_non_terminal_count(self):
        """Gauge should reflect non-terminal job counts."""
        config = MetricsConfig()
        metrics = PrometheusMetrics(config)

        # Simulate stuck jobs by stage
        counts_by_stage = {
            "compliance_check": 5,
            "browser_crawl": 3,
            "ai_extraction": 2,
        }
        metrics.refresh_stuck_jobs(counts_by_stage)

        # Verify gauge was set
        metric = metrics._metrics["stuck_jobs"]
        samples = list(metric.collect())[0].samples

        for stage, expected_count in counts_by_stage.items():
            stage_samples = [s for s in samples if s.labels.get("stage") == stage]
            assert len(stage_samples) > 0
            assert stage_samples[0].value == expected_count


class TestHealthStatusGauge:
    """Test health_status gauge."""

    def test_health_status_gauge_exists(self):
        """health_status gauge should exist."""
        config = MetricsConfig()
        metrics = PrometheusMetrics(config)

        assert "health_status" in metrics._metrics

    def test_health_status_gauge_has_component_label(self):
        """Gauge should have component label."""
        config = MetricsConfig()
        metrics = PrometheusMetrics(config)

        metric = metrics._metrics["health_status"]
        assert "component" in metric._labelnames

    def test_health_status_gauge_initialized_healthy(self):
        """Gauge should be initialized with healthy status (1)."""
        config = MetricsConfig()
        metrics = PrometheusMetrics(config)

        metric = metrics._metrics["health_status"]
        samples = list(metric.collect())[0].samples

        # Check default components are healthy
        for component in ["api", "database", "redis"]:
            component_samples = [s for s in samples if s.labels.get("component") == component]
            assert len(component_samples) > 0
            assert component_samples[0].value == 1

    def test_health_status_gauge_can_be_set_unhealthy(self):
        """Gauge can be set to unhealthy (0)."""
        config = MetricsConfig()
        metrics = PrometheusMetrics(config)

        # Set unhealthy
        metrics.set_health_status(healthy=False, component="api")

        metric = metrics._metrics["health_status"]
        samples = list(metric.collect())[0].samples
        api_samples = [s for s in samples if s.labels.get("component") == "api"]
        assert len(api_samples) > 0
        assert api_samples[0].value == 0


class TestMetricHelpText:
    """Test that metrics have descriptive help text."""

    def test_privileged_bypass_metric_has_help_text(self):
        """Metric should have descriptive help text."""
        config = MetricsConfig()
        metrics = PrometheusMetrics(config)

        metric = metrics._metrics["privileged_db_session_activations_total"]
        assert metric._documentation is not None
        assert len(metric._documentation) > 0

    def test_retry_events_metric_has_help_text(self):
        """Metric should have descriptive help text."""
        config = MetricsConfig()
        metrics = PrometheusMetrics(config)

        metric = metrics._metrics["retry_events_total"]
        assert metric._documentation is not None
        assert len(metric._documentation) > 0

    def test_urls_blocked_metric_has_help_text(self):
        """Metric should have descriptive help text."""
        config = MetricsConfig()
        metrics = PrometheusMetrics(config)

        metric = metrics._metrics["urls_blocked_total"]
        assert metric._documentation is not None
        assert len(metric._documentation) > 0


class TestMetricRegistryIntegration:
    """Test metrics integration with global registry."""

    def test_metrics_initialized_globally(self):
        """Metrics should be initialized globally."""
        # Initialize metrics
        config = MetricsConfig()
        initialize_metrics(config)

        # Verify global metrics instance exists
        metrics = get_metrics()
        assert metrics is not None

    def test_get_metrics_returns_same_instance(self):
        """get_metrics should return the same instance."""
        config = MetricsConfig()
        initialize_metrics(config)

        metrics1 = get_metrics()
        metrics2 = get_metrics()

        assert metrics1 is metrics2


class TestRequiredMetricsContract:
    """Test that all required metrics exist per contract."""

    def test_all_required_metrics_exist(self):
        """All required metrics should exist in the metrics system."""
        config = MetricsConfig()
        metrics = PrometheusMetrics(config)

        required_metrics = [
            "privileged_db_session_activations_total",
            "retry_events_total",
            "urls_blocked_total",
            "crawl_path_distribution",
            "stuck_jobs",
            "health_status",
        ]

        for metric_name in required_metrics:
            assert metric_name in metrics._metrics, f"Required metric {metric_name} not found"

    def test_required_metric_labels_exist(self):
        """All required metrics should have required labels."""
        config = MetricsConfig()
        metrics = PrometheusMetrics(config)

        required_labels = {
            "privileged_db_session_activations_total": ["mode"],
            "retry_events_total": ["stage", "reason"],
            "urls_blocked_total": ["reason"],
            "crawl_path_distribution": ["path"],
            "stuck_jobs": ["stage"],
            "health_status": ["component"],
        }

        for metric_name, expected_labels in required_labels.items():
            metric = metrics._metrics[metric_name]
            for label in expected_labels:
                assert label in metric._labelnames, f"Metric {metric_name} missing label {label}"
