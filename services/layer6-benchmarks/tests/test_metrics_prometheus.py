"""Unit tests for Prometheus metrics collection."""

import pytest
from prometheus_client import CollectorRegistry

<<<<<<< HEAD
from layer6_benchmarks.metrics.prometheus_metrics import (
=======
from value_fabric.layer6.metrics.prometheus_metrics import (
>>>>>>> ab2ac2c2 (```)
    MetricsConfig,
    MetricsMiddleware,
    PrometheusMetrics,
)


class TestMetricsConfig:
    def test_default_config_has_registry_and_buckets(self) -> None:
        cfg = MetricsConfig()
        assert cfg.enabled is True
        assert cfg.registry is not None
        assert isinstance(cfg.default_buckets, list)
        assert all(isinstance(b, float) for b in cfg.default_buckets)


class TestPrometheusMetrics:
    @pytest.fixture
    def metrics(self) -> PrometheusMetrics:
        return PrometheusMetrics(MetricsConfig(registry=CollectorRegistry()))

    def test_status_class_groups_by_hundreds(self) -> None:
        assert PrometheusMetrics._status_class(200) == "2xx"
        assert PrometheusMetrics._status_class(404) == "4xx"
        assert PrometheusMetrics._status_class(500) == "5xx"
        assert PrometheusMetrics._status_class(301) == "3xx"
        assert PrometheusMetrics._status_class("418") == "4xx"

    def test_disabled_metrics_noop(self) -> None:
        disabled = PrometheusMetrics(
            MetricsConfig(enabled=False, registry=CollectorRegistry())
        )
        # Should not raise.
        disabled.increment_requests_total(method="GET", route="/", status_code=200)
        disabled.observe_request_duration(duration=0.1, method="GET", route="/")
        disabled.increment_dataset_comparisons(industry="tech", outcome="success")
        disabled.set_health_status(True, service="layer6-benchmarks")
        disabled.set_build_info(version="1.0.0", build_sha="abc")
        assert disabled.get_metrics() == ""

    def test_set_health_status_sets_gauge(self, metrics: PrometheusMetrics) -> None:
        metrics.set_health_status(True, service="layer6-benchmarks")
        text = metrics.get_metrics()
        assert 'layer6_health_status{service="layer6-benchmarks"} 1.0' in text

    def test_set_build_info_updates_info(self, metrics: PrometheusMetrics) -> None:
        metrics.set_build_info(version="1.2.3", build_sha="deadbeef")
        text = metrics.get_metrics()
        assert "layer6_build_info" in text
        assert "1.2.3" in text
        assert "deadbeef" in text

    def test_increment_requests_total_increments_counter(
        self, metrics: PrometheusMetrics
    ) -> None:
        metrics.increment_requests_total(method="GET", route="/health", status_code=200)
        text = metrics.get_metrics()
        assert "layer6_requests_total{" in text
        assert 'method="GET"' in text
        assert 'route="/health"' in text
        assert 'status_class="2xx"' in text

    def test_observe_request_duration_records_histogram(
        self, metrics: PrometheusMetrics
    ) -> None:
        metrics.observe_request_duration(duration=0.25, method="POST", route="/compare")
        text = metrics.get_metrics()
        assert "layer6_request_duration_seconds_bucket" in text
        assert "layer6_request_duration_seconds_count" in text

    def test_increment_dataset_comparisons_increments_counter(
        self, metrics: PrometheusMetrics
    ) -> None:
        metrics.increment_dataset_comparisons(industry="manufacturing", outcome="success")
        text = metrics.get_metrics()
        assert (
            'layer6_dataset_comparisons_total{industry="manufacturing",outcome="success"} 1.0'
            in text
        )

    def test_get_metrics_returns_prometheus_text(self, metrics: PrometheusMetrics) -> None:
        text = metrics.get_metrics()
        assert isinstance(text, str)
        assert text.startswith("# HELP")


class TestMetricsMiddleware:
    def test_normalize_path_without_normalizer(self) -> None:
        metrics = PrometheusMetrics(MetricsConfig(registry=CollectorRegistry()))
        middleware = MetricsMiddleware(metrics)
        # Force normalizer to None by patching.
        middleware._normalizer = None
        assert middleware._normalize_path("/health/") == "/health"
        assert middleware._normalize_path("") == "/"
        assert middleware._normalize_path("/") == "/"

    def test_normalize_path_strips_trailing_slash(self) -> None:
        metrics = PrometheusMetrics(MetricsConfig(registry=CollectorRegistry()))
        middleware = MetricsMiddleware(metrics)
        middleware._normalizer = None
        assert middleware._normalize_path("/v1/benchmarks/datasets/") == "/v1/benchmarks/datasets"

    def test_normalize_path_returns_root_for_empty(self) -> None:
        metrics = PrometheusMetrics(MetricsConfig(registry=CollectorRegistry()))
        middleware = MetricsMiddleware(metrics)
        middleware._normalizer = None
        assert middleware._normalize_path("") == "/"
