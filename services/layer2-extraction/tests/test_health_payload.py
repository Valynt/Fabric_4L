from __future__ import annotations

from types import SimpleNamespace

import pytest

from layer2_extraction.api.routes import health


class _FakeLayer3Client:
    def __init__(self, healthy: bool = True) -> None:
        self.healthy = healthy
        self.closed = False

    async def health_check(self) -> bool:
        return self.healthy

    async def close(self) -> None:
        self.closed = True


class _FakeMetrics:
    def __init__(self) -> None:
        self.config = SimpleNamespace(enabled=False)
        self.health_calls: list[tuple[bool, str]] = []

    def set_health_status(self, healthy: bool, *, component: str) -> None:
        self.health_calls.append((healthy, component))


@pytest.mark.asyncio
async def test_build_health_payload_reports_healthy_layer3_dependency() -> None:
    client = _FakeLayer3Client(healthy=True)
    metrics = _FakeMetrics()

    payload = await health.build_health_payload(
        app_start_time=0,
        metrics=metrics,
        layer3_client_factory=lambda: client,
        psutil_module=None,
        skip_layer3_probe=False,
    )

    assert payload["status"] == "healthy"
    assert payload["service"] == "layer2-extraction"
    assert payload["dependencies"] == [
        {
            "name": "layer3_knowledge",
            "status": "healthy",
            "required": True,
            "reason": None,
            "error": None,
        }
    ]
    assert client.closed is True
    assert metrics.health_calls == [(True, "api"), (True, "layer3")]


@pytest.mark.asyncio
async def test_build_health_payload_preserves_release_smoke_skip_contract() -> None:
    metrics = _FakeMetrics()

    payload = await health.build_health_payload(
        app_start_time=0,
        metrics=metrics,
        layer3_client_factory=lambda: _FakeLayer3Client(healthy=True),
        psutil_module=None,
        skip_layer3_probe=True,
    )

    assert payload["status"] == "degraded"
    assert payload["dependencies"] == [
        {
            "name": "layer3_knowledge",
            "status": "degraded",
            "required": True,
            "reason": "layer3_probe_skipped",
            "error": health.LAYER3_SKIP_ERROR,
        }
    ]
    assert metrics.health_calls == [(False, "api"), (False, "layer3")]


@pytest.mark.asyncio
async def test_build_health_payload_reports_layer3_exception_without_leaking_details() -> None:
    class BrokenLayer3Client:
        async def health_check(self) -> bool:
            raise RuntimeError("internal connection detail")

    payload = await health.build_health_payload(
        app_start_time=0,
        metrics=None,
        layer3_client_factory=BrokenLayer3Client,
        psutil_module=None,
        skip_layer3_probe=False,
    )

    assert payload["status"] == "degraded"
    assert payload["dependencies"] == [
        {
            "name": "layer3_knowledge",
            "status": "unhealthy",
            "required": True,
            "reason": "dependency_probe_error",
            "error": "Layer 3 health check failed",
        }
    ]


@pytest.mark.asyncio
async def test_layer3_dependency_status_preserves_internal_skip_reason() -> None:
    dependency, healthy = await health.layer3_dependency_status(
        skip_layer3_probe=True,
        layer3_client_factory=lambda: _FakeLayer3Client(healthy=True),
    )

    assert healthy is False
    assert dependency == {
        "name": "layer3_knowledge",
        "status": "degraded",
        "response_time_ms": None,
        "error": health.LAYER3_SKIP_ERROR,
        "failure_reason": "layer3_probe_skipped",
    }


@pytest.mark.asyncio
async def test_layer3_dependency_status_preserves_internal_error_code() -> None:
    class BrokenLayer3Client:
        async def health_check(self) -> bool:
            raise RuntimeError("internal connection detail")

    dependency, healthy = await health.layer3_dependency_status(
        skip_layer3_probe=False,
        layer3_client_factory=BrokenLayer3Client,
    )

    assert healthy is False
    assert dependency == {
        "name": "layer3_knowledge",
        "status": "unhealthy",
        "response_time_ms": None,
        "error": "Layer 3 health check failed",
        "error_code": "L3_HEALTH_CHECK_ERROR",
        "failure_reason": "dependency_probe_error",
    }


def test_collect_metrics_counts_is_defensive_for_malformed_registry() -> None:
    malformed_metrics = SimpleNamespace(config=SimpleNamespace(enabled=True), _metrics={"requests_total": object()})

    assert health.collect_metrics_counts(malformed_metrics) == (0, 0)
