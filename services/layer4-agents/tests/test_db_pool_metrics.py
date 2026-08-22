from layer4_agents.metrics.prometheus_metrics import MetricsConfig, PrometheusMetrics


def test_db_pool_metrics_emit_values() -> None:
    metrics = PrometheusMetrics(MetricsConfig())
    metrics.set_db_pool_state(pool_size=10, active=8, idle=2)
    metrics.observe_db_pool_wait(0.05)
    metrics.increment_db_pool_timeout()

    rendered = metrics.get_metrics()
    assert "layer4_db_pool_size" in rendered
    assert "layer4_db_pool_active_connections" in rendered
    assert "layer4_db_pool_idle_connections" in rendered
    assert "layer4_db_pool_wait_seconds_bucket" in rendered
    assert "layer4_db_pool_timeouts_total" in rendered
