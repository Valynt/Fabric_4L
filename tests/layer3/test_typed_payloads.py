from datetime import UTC, datetime

import pytest

from layer3_knowledge.analytics.manager import AnalyticsConfig, AnalyticsEvent, AnalyticsManager
from layer3_knowledge.security.monitor import SecurityConfig, SecurityEvent, SecurityMonitor
from layer3_knowledge.security.query_validator import ValidationFinding, ValidationSeverity


def test_validation_finding_to_dict_shape() -> None:
    finding = ValidationFinding(
        severity=ValidationSeverity.ERROR,
        message="missing tenant scope",
        line_number=4,
        pattern="MATCH (e:Entity {id: $id})",
        suggestion="add tenant_id",
    )

    payload = finding.to_dict()

    assert payload["severity"] == "error"
    assert isinstance(payload["line_number"], int)
    assert set(payload.keys()) == {"severity", "message", "line_number", "pattern", "suggestion"}


def test_security_event_to_dict_shape() -> None:
    event = SecurityEvent(
        event_id="evt-1",
        timestamp=datetime.now(UTC),
        event_type="request",
        source_ip="127.0.0.1",
        user_id="u1",
        api_key_id="k1",
        endpoint="/v1/entities",
        method="GET",
        user_agent="pytest",
        request_size=32,
        response_size=64,
        status_code=200,
        response_time_ms=5.4,
        request_headers={"x": "1"},
        request_body=None,
        response_headers={"content-type": "application/json"},
    )

    payload = event.to_dict()

    assert payload["event_id"] == "evt-1"
    assert isinstance(payload["tags"], list)
    assert isinstance(payload["request_headers"], dict)


@pytest.mark.asyncio
async def test_security_summary_shape() -> None:
    monitor = SecurityMonitor(SecurityConfig())
    summary = await monitor.get_security_summary()

    assert set(summary.keys()) == {
        "stats",
        "blocked_ips",
        "blocked_users",
        "active_signatures",
        "recent_alerts",
        "alert_levels",
    }
    assert set(summary["alert_levels"].keys()) == {"low", "medium", "high", "critical"}


def test_analytics_event_to_dict_shape() -> None:
    event = AnalyticsEvent(
        event_id="evt-2",
        timestamp=datetime.now(UTC),
        event_type="request",
        user_id="u1",
        api_key_id="k1",
        endpoint="/v1/query",
        method="POST",
        status_code=201,
        response_time_ms=10.2,
        request_size_bytes=100,
        response_size_bytes=200,
        user_agent="pytest",
        ip_address="127.0.0.1",
        request_id="req-1",
    )
    payload = event.to_dict()
    assert payload["status_code"] == 201
    assert isinstance(payload["tags"], dict)


@pytest.mark.asyncio
async def test_analytics_summary_and_empty_dashboard_payload_shape() -> None:
    manager = AnalyticsManager(AnalyticsConfig())
    summary = await manager.get_metrics_summary()
    dashboard = await manager.get_dashboard_data("missing")

    assert set(summary.keys()) == {
        "total_requests",
        "total_errors",
        "success_rate",
        "throughput_rps",
        "unique_users",
        "unique_api_keys",
        "avg_response_time",
        "top_endpoints",
    }
    assert dashboard == {"dashboard": None, "data": None, "generated_at": None}
