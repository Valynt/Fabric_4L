from fastapi import HTTPException
from fastapi.testclient import TestClient

from ..app import (
    EnforcementControlConfig,
    EnforcementMode,
    EnforcementRolloutConfig,
    ExceptionHandlerRegistrationMode,
    create_fabric_app,
    install_metrics_middleware,
    record_enforcement_decision,
    register_health_endpoint,
)


def test_create_fabric_app_applies_shared_defaults() -> None:
    app = create_fabric_app(
        service_name="test-service",
        title="Test Service",
        version="1.0.0",
        description="test app",
        cors_policy={
            "allow_origins": ["https://example.com"],
            "allow_credentials": True,
            "allow_methods": ["*"],
            "allow_headers": ["*"],
        },
    )

    @app.get("/ok")
    async def ok() -> dict[str, str]:
        return {"service": app.state.service_name}

    @app.get("/boom")
    async def boom() -> None:
        raise HTTPException(status_code=400, detail="bad request")

    client = TestClient(app)

    ok_response = client.get("/ok", headers={"Origin": "https://example.com"})
    assert ok_response.status_code == 200
    assert ok_response.json() == {"service": "test-service"}
    assert ok_response.headers["access-control-allow-credentials"] == "true"
    assert ok_response.headers["access-control-allow-origin"] == "https://example.com"
    assert "x-request-id" in ok_response.headers

    error_response = client.get("/boom")
    assert error_response.status_code == 400
    payload = error_response.json()
    assert "error" in payload
    assert payload["error"]["code"] == "VALIDATION_ERROR"
    assert "x-request-id" in error_response.headers


def test_register_health_endpoint_uses_service_defaults() -> None:
    app = create_fabric_app(
        service_name="test-health-service",
        title="Test Health Service",
        version="1.0.0",
        description="test app",
    )
    register_health_endpoint(app, service_name="test-health-service")

    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["service"] == "test-health-service"
    assert payload["status"] == "ok"
    assert "timestamp" in payload


def test_install_metrics_middleware_sets_state_and_wraps_requests() -> None:
    app = create_fabric_app(
        service_name="test-metrics-service",
        title="Test Metrics Service",
        version="1.0.0",
        description="test app",
    )

    class Recorder:
        seen_paths: list[str]

        def __init__(self) -> None:
            self.seen_paths = []

    from starlette.middleware.base import BaseHTTPMiddleware

    class Middleware(BaseHTTPMiddleware):
        def __init__(self, app, metrics: Recorder) -> None:
            super().__init__(app)
            self.metrics = metrics

        async def dispatch(self, request, call_next):
            self.metrics.seen_paths.append(request.url.path)
            response = await call_next(request)
            response.headers["x-metrics-installed"] = "true"
            return response

    metrics = Recorder()
    install_metrics_middleware(app, metrics=metrics, middleware_factory=Middleware)
    install_metrics_middleware(app, metrics=metrics, middleware_factory=Middleware)

    @app.get("/ok")
    async def ok() -> dict[str, str]:
        return {"status": "ok"}

    client = TestClient(app)
    response = client.get("/ok")

    assert response.status_code == 200
    assert response.headers["x-metrics-installed"] == "true"
    assert app.state.metrics is metrics
    assert metrics.seen_paths == ["/ok"]


def test_health_endpoint_is_marked_as_enforcement_opt_out() -> None:
    app = create_fabric_app(
        service_name="test-health-service",
        title="Test Health Service",
        version="1.0.0",
        description="test app",
    )
    register_health_endpoint(app, service_name="test-health-service")

    route = next(
        route for route in app.routes if getattr(route, "path", "") == "/health"
    )
    endpoint = route.endpoint
    assert getattr(endpoint, "_vf_enforcement_opt_out", False) is True


def test_record_enforcement_decision_audit_mode_does_not_block() -> None:
    app = create_fabric_app(
        service_name="test-enforcement",
        title="Test Enforcement",
        version="1.0.0",
        description="test app",
        enforcement_rollout=EnforcementRolloutConfig(
            tenant_enforcement=EnforcementControlConfig(mode=EnforcementMode.AUDIT)
        ),
    )

    allowed = record_enforcement_decision(
        app,
        control="tenant_enforcement",
        violation="missing_tenant_context",
        route="/v1/private",
        tenant_id="tenant-a",
        actor_id="actor-a",
    )

    assert allowed is True
    assert app.state.enforcement_counters.false_positive_candidate_total == 1
    assert app.state.enforcement_counters.blocked_total == 0


def test_record_enforcement_decision_enforce_mode_blocks() -> None:
    app = create_fabric_app(
        service_name="test-enforcement",
        title="Test Enforcement",
        version="1.0.0",
        description="test app",
        enforcement_rollout=EnforcementRolloutConfig(
            tenant_enforcement=EnforcementControlConfig(mode=EnforcementMode.ENFORCE)
        ),
    )

    allowed = record_enforcement_decision(
        app,
        control="tenant_enforcement",
        violation="missing_tenant_context",
        route="/v1/private",
        tenant_id="tenant-a",
        actor_id="actor-a",
    )

    assert allowed is False
    assert app.state.enforcement_counters.blocked_total == 1


def test_record_enforcement_decision_route_opt_out_increments_bypass() -> None:
    app = create_fabric_app(
        service_name="test-enforcement",
        title="Test Enforcement",
        version="1.0.0",
        description="test app",
    )

    allowed = record_enforcement_decision(
        app,
        control="idempotency",
        violation="replay_near_miss",
        route="/health",
        tenant_id=None,
        actor_id="system",
    )

    assert allowed is True
    assert app.state.enforcement_counters.bypass_total == 1


def test_create_fabric_app_hook_defaults_are_inert() -> None:
    app = create_fabric_app(
        service_name="test-hooks",
        title="Test Hooks",
        version="1.0.0",
        description="test app",
    )

    assert hasattr(app.state, "service_name")


def test_create_fabric_app_executes_middleware_and_health_hooks_when_provided() -> None:
    calls: list[str] = []

    def pre_core_hook(app) -> None:
        calls.append("pre")
        app.state.pre_hook = True

    def post_core_hook(app) -> None:
        calls.append("post")
        app.state.post_hook = True

    def health_hook(app) -> None:
        calls.append("health")
        app.state.health_hook = True

    app = create_fabric_app(
        service_name="test-hooks",
        title="Test Hooks",
        version="1.0.0",
        description="test app",
        pre_core_middleware_hook=pre_core_hook,
        post_core_middleware_hook=post_core_hook,
        health_readiness_augmentation_hook=health_hook,
    )

    assert calls == ["pre", "post", "health"]
    assert app.state.pre_hook is True
    assert app.state.post_hook is True
    assert app.state.health_hook is True


def test_create_fabric_app_exception_handler_registration_mode_skip() -> None:
    app = create_fabric_app(
        service_name="test-exception-modes",
        title="Test Exception Modes",
        version="1.0.0",
        description="test app",
        exception_handler_registration_mode=ExceptionHandlerRegistrationMode.SKIP,
    )

    @app.get("/boom")
    async def boom() -> None:
        raise HTTPException(status_code=400, detail="bad request")

    client = TestClient(app)
    response = client.get("/boom")

    assert response.status_code == 400
    assert response.json() == {"detail": "bad request"}


def test_security_middleware_adds_hsts_header() -> None:
    from value_fabric.shared.security import SecurityConfig, add_security_middleware

    app = create_fabric_app(
        service_name="test-hsts",
        title="Test HSTS",
        version="1.0.0",
        description="test app",
        enforce_tenant_context=False,
    )
    add_security_middleware(app, config=SecurityConfig(enable_hsts=True))

    @app.get("/ok")
    async def ok() -> dict[str, str]:
        return {"status": "ok"}

    client = TestClient(app)
    response = client.get("/ok")

    assert response.status_code == 200
    assert (
        response.headers["Strict-Transport-Security"]
        == "max-age=31536000; includeSubDomains"
    )


def test_security_middleware_omits_hsts_when_disabled() -> None:
    from value_fabric.shared.security import SecurityConfig, add_security_middleware

    app = create_fabric_app(
        service_name="test-no-hsts",
        title="Test No HSTS",
        version="1.0.0",
        description="test app",
        enforce_tenant_context=False,
    )
    add_security_middleware(app, config=SecurityConfig(enable_hsts=False))

    @app.get("/ok")
    async def ok() -> dict[str, str]:
        return {"status": "ok"}

    client = TestClient(app)
    response = client.get("/ok")

    assert response.status_code == 200
    assert "Strict-Transport-Security" not in response.headers
