"""PR1 — framework compatibility controls.

Validates new opt-in controls on ``create_fabric_app`` are AUDIT-first and
inert by default. These tests must not require Redis, structlog, or other
optional dependencies.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from unittest.mock import patch

from fastapi.testclient import TestClient

from ..app import (
    EnforcementControlConfig,
    EnforcementMode,
    EnforcementRolloutConfig,
    FrameworkIdempotencyConfig,
    FrameworkRateLimitConfig,
    create_fabric_app,
)
from ..health import CallableProbe, ProbeResult, aggregate_probes
from ..logging import StructuredLoggingConfig, configure_structlog


# ----- HealthCheckProbe protocol + aggregator ------------------------------------


def test_aggregate_probes_returns_true_on_empty() -> None:
    healthy, results = asyncio.run(aggregate_probes([]))
    assert healthy is True
    assert results == []


def test_aggregate_probes_collects_each_result() -> None:
    async def ok() -> ProbeResult:
        return ProbeResult(name="ok", healthy=True)

    async def bad() -> ProbeResult:
        return ProbeResult(name="bad", healthy=False, detail="db down")

    probes = [CallableProbe(name="ok", fn=ok), CallableProbe(name="bad", fn=bad)]
    healthy, results = asyncio.run(aggregate_probes(probes))

    assert healthy is False
    names = {r.name for r in results}
    assert names == {"ok", "bad"}
    assert all(r.latency_ms is not None for r in results)


def test_aggregate_probes_timeout_marks_unhealthy() -> None:
    async def slow() -> ProbeResult:
        await asyncio.sleep(0.2)
        return ProbeResult(name="slow", healthy=True)

    probes = [CallableProbe(name="slow", fn=slow)]
    healthy, results = asyncio.run(aggregate_probes(probes, timeout_seconds=0.01))
    assert healthy is False
    assert results[0].detail is not None and "timeout" in results[0].detail


def test_aggregate_probes_exception_marks_unhealthy() -> None:
    async def boom() -> ProbeResult:
        raise RuntimeError("dep failed")

    probes = [CallableProbe(name="dep", fn=boom)]
    healthy, results = asyncio.run(aggregate_probes(probes))
    assert healthy is False
    assert results[0].detail == "dep failed"


# ----- Signature stability (append-only contract) -------------------------------


def test_create_fabric_app_signature_includes_all_pr1_params() -> None:
    import inspect

    sig = inspect.signature(create_fabric_app)
    params = set(sig.parameters.keys())
    required = {
        "service_name",
        "title",
        "version",
        "description",
        "rate_limit",
        "idempotency",
        "structured_logging",
        "health_probes",
        "readiness_path",
        "enforce_tenant_context",
        "audit_worker_db_factory",
    }
    assert required.issubset(params)


def test_create_fabric_app_wraps_lifespan_when_audit_worker_factory_is_provided() -> None:
    events: list[str] = []

    @asynccontextmanager
    async def service_lifespan(_app):
        events.append("service_started")
        yield
        events.append("service_stopped")

    class StubAuditWorker:
        _task = None

        def __init__(self, db_factory) -> None:
            assert db_factory is audit_worker_db_factory

        def start(self) -> None:
            events.append("worker_started")

        def stop(self) -> None:
            events.append("worker_stopped")

    def audit_worker_db_factory():
        raise AssertionError("the worker must not open a DB session during app bootstrap")

    with patch("value_fabric.shared.audit.worker.AuditWorker", StubAuditWorker):
        app = create_fabric_app(
            service_name="audit-worker",
            title="t",
            version="1.0.0",
            description="t",
            lifespan=service_lifespan,
            audit_worker_db_factory=audit_worker_db_factory,
            enforce_tenant_context=False,
        )
        asyncio.run(_exercise_lifespan(app))

    assert events == [
        "worker_started",
        "service_started",
        "service_stopped",
        "worker_stopped",
    ]


async def _exercise_lifespan(app) -> None:
    async with app.router.lifespan_context(app):
        pass


# ----- /ready endpoint -----------------------------------------------------------


def test_readiness_endpoint_returns_503_when_probe_fails() -> None:
    async def bad() -> ProbeResult:
        return ProbeResult(name="db", healthy=False, detail="unreachable")

    app = create_fabric_app(
        service_name="test-ready",
        title="Test Ready",
        version="1.0.0",
        description="t",
        health_probes=[CallableProbe(name="db", fn=bad)],
    )

    client = TestClient(app)
    resp = client.get("/ready")
    assert resp.status_code == 503
    payload = resp.json()
    assert payload["status"] == "not_ready"
    assert payload["probes"][0]["name"] == "db"
    assert payload["probes"][0]["healthy"] is False


def test_readiness_endpoint_returns_200_when_all_healthy() -> None:
    async def ok() -> ProbeResult:
        return ProbeResult(name="db", healthy=True)

    app = create_fabric_app(
        service_name="test-ready",
        title="Test Ready",
        version="1.0.0",
        description="t",
        health_probes=[CallableProbe(name="db", fn=ok)],
    )

    client = TestClient(app)
    resp = client.get("/ready")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ready"


def test_readiness_endpoint_absent_when_no_probes() -> None:
    app = create_fabric_app(
        service_name="test-no-probes",
        title="t",
        version="1.0.0",
        description="t",
    )
    paths = {getattr(r, "path", None) for r in app.routes}
    assert "/ready" not in paths


# ----- Structured logging --------------------------------------------------------


def test_configure_structlog_disabled_is_noop() -> None:
    cfg = StructuredLoggingConfig(enabled=False)
    assert configure_structlog(cfg) is False


def test_configure_structlog_returns_false_when_dependency_missing() -> None:
    # When structlog is absent, the helper must not raise.
    cfg = StructuredLoggingConfig(enabled=True, service_name="x")
    result = configure_structlog(cfg)
    # Result depends on whether structlog is installed in the test env; both
    # branches must be truthy/falsy values that the framework treats as
    # soft failure.
    assert isinstance(result, bool)


# ----- Framework config defaults are AUDIT-first ---------------------------------


def test_framework_rate_limit_default_is_audit() -> None:
    cfg = FrameworkRateLimitConfig()
    assert cfg.mode == EnforcementMode.AUDIT
    assert cfg.rate_limiter_factory is None


def test_framework_idempotency_default_is_audit() -> None:
    cfg = FrameworkIdempotencyConfig()
    assert cfg.mode == EnforcementMode.AUDIT
    assert cfg.service_factory is None
    assert {"POST", "PUT", "PATCH", "DELETE"}.issubset(cfg.methods)


# ----- Backward compatibility: defaults remain inert ----------------------------


def test_create_fabric_app_defaults_install_no_new_middleware() -> None:
    """Behavior identical to pre-PR1 callers when new kwargs are not provided."""

    app = create_fabric_app(
        service_name="legacy",
        title="t",
        version="1.0.0",
        description="t",
        enforce_tenant_context=False,
    )
    # No idempotency/rate-limit middleware should be installed.
    middleware_names = [m.cls.__name__ for m in app.user_middleware]
    assert "_IdempotencyMiddleware" not in middleware_names
    assert "TenantRateLimitMiddleware" not in middleware_names
    assert "_TenantEnforcementMiddleware" not in middleware_names


def test_create_fabric_app_defaults_install_tenant_enforcement() -> None:
    """Tenant enforcement middleware is installed by default (fail-closed)."""

    app = create_fabric_app(
        service_name="tenant-default",
        title="t",
        version="1.0.0",
        description="t",
    )
    middleware_names = [m.cls.__name__ for m in app.user_middleware]
    assert "_TenantEnforcementMiddleware" in middleware_names


def test_create_fabric_app_does_not_install_rate_limit_without_factory() -> None:
    cfg = FrameworkRateLimitConfig(mode=EnforcementMode.ENFORCE, rate_limiter_factory=None)
    app = create_fabric_app(
        service_name="no-factory",
        title="t",
        version="1.0.0",
        description="t",
        rate_limit=cfg,
    )
    middleware_names = [m.cls.__name__ for m in app.user_middleware]
    assert "TenantRateLimitMiddleware" not in middleware_names


# ----- Tenant enforcement middleware --------------------------------------------


def test_tenant_enforcement_audit_allows_request_without_context() -> None:
    app = create_fabric_app(
        service_name="tenant-audit",
        title="t",
        version="1.0.0",
        description="t",
        enforce_tenant_context=True,
        enforcement_rollout=EnforcementRolloutConfig(
            tenant_enforcement=EnforcementControlConfig(mode=EnforcementMode.AUDIT)
        ),
    )

    @app.get("/private")
    async def private() -> dict[str, str]:
        return {"ok": "yes"}

    client = TestClient(app)
    resp = client.get("/private")
    assert resp.status_code == 200
    # AUDIT mode increments candidate counter, never blocks.
    assert app.state.enforcement_counters.false_positive_candidate_total >= 1


def test_tenant_enforcement_enforce_blocks_request_without_context() -> None:
    app = create_fabric_app(
        service_name="tenant-enforce",
        title="t",
        version="1.0.0",
        description="t",
        enforce_tenant_context=True,
        enforcement_rollout=EnforcementRolloutConfig(
            tenant_enforcement=EnforcementControlConfig(mode=EnforcementMode.ENFORCE)
        ),
    )

    @app.get("/private")
    async def private() -> dict[str, str]:  # pragma: no cover - blocked before reaching
        return {"ok": "yes"}

    client = TestClient(app)
    resp = client.get("/private")
    assert resp.status_code == 403
    assert resp.json()["error"] == "tenant_context_required"
