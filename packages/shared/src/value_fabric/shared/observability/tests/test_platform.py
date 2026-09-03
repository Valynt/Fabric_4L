from __future__ import annotations

import builtins
import sys
import types
from collections.abc import Iterator

import pytest
from value_fabric.shared.observability.platform import (
    ObservabilityContext,
    PlatformTelemetry,
    bind_context,
    clear_context,
    configure_platform,
    correlation_fields,
    get_context,
    instrument_fastapi_app,
)


def _reset_otel_tracer_provider() -> None:
    """Undo the process-wide TracerProvider once-lock so tests stay isolated."""
    try:
        from opentelemetry import trace
    except ImportError:
        return
    trace._TRACER_PROVIDER = None  # type: ignore[attr-defined]
    once = getattr(trace, "_TRACER_PROVIDER_SET_ONCE", None)
    if once is not None:
        once._done = False


@pytest.fixture(autouse=True)
def _reset_observability_context() -> Iterator[None]:
    clear_context()
    _reset_otel_tracer_provider()
    yield
    clear_context()
    _reset_otel_tracer_provider()


def test_configure_platform_is_noop_without_otlp_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    result = configure_platform("layer4-agents", layer="l4", service_version="1.2.0")
    assert isinstance(result, PlatformTelemetry)
    assert result.provider is None
    assert result.service_name == "layer4-agents"
    assert result.layer == "l4"


def test_configure_platform_respects_explicit_empty_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4318")
    result = configure_platform("layer4-agents", endpoint="")
    # Empty string is falsy — fail closed rather than exporting to a guessed host.
    assert result.provider is None


def test_bind_context_and_correlation_fields_expose_request_and_trace() -> None:
    bound = bind_context(
        request_id="req-1",
        trace_id="a" * 32,
        span_id="b" * 16,
        tenant_id="tenant-a",
    )
    assert isinstance(bound, ObservabilityContext)
    assert get_context().request_id == "req-1"
    fields = correlation_fields()
    assert fields["request_id"] == "req-1"
    assert fields["trace_id"] == "a" * 32
    assert fields["span_id"] == "b" * 16
    assert fields["tenant_id"] == "tenant-a"


def test_correlation_fields_empty_when_unbound() -> None:
    assert correlation_fields() == {}


def test_instrument_fastapi_app_noops_when_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[object] = []

    class _Instrumentor:
        @staticmethod
        def instrument_app(app: object) -> None:
            calls.append(app)

    fake = types.ModuleType("opentelemetry.instrumentation.fastapi")
    fake.FastAPIInstrumentor = _Instrumentor
    monkeypatch.setitem(sys.modules, "opentelemetry.instrumentation.fastapi", fake)

    applied = instrument_fastapi_app(object(), enabled=False)
    assert calls == []
    assert applied is False


def test_instrument_fastapi_app_instruments_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[object] = []

    class _Instrumentor:
        @staticmethod
        def instrument_app(app: object) -> None:
            calls.append(app)

    fake = types.ModuleType("opentelemetry.instrumentation.fastapi")
    fake.FastAPIInstrumentor = _Instrumentor
    monkeypatch.setitem(sys.modules, "opentelemetry.instrumentation.fastapi", fake)

    app = object()
    applied = instrument_fastapi_app(app, enabled=True)
    assert calls == [app]
    assert applied is True


def test_instrument_fastapi_app_noops_when_instrumentor_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(sys.modules, "opentelemetry.instrumentation.fastapi", None)
    applied = instrument_fastapi_app(object(), enabled=True)
    assert applied is False


def test_instrument_fastapi_app_fails_closed_when_instrumentor_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _Instrumentor:
        @staticmethod
        def instrument_app(app: object) -> None:
            raise RuntimeError("instrumentation failed")

    fake = types.ModuleType("opentelemetry.instrumentation.fastapi")
    fake.FastAPIInstrumentor = _Instrumentor
    monkeypatch.setitem(sys.modules, "opentelemetry.instrumentation.fastapi", fake)

    applied = instrument_fastapi_app(object(), enabled=True)
    assert applied is False


def test_configure_platform_is_noop_when_otel_sdk_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_import = builtins.__import__

    def _blocked(
        name: str,
        globals: object = None,
        locals: object = None,
        fromlist: tuple[str, ...] = (),
        level: int = 0,
    ) -> object:
        if name.startswith("opentelemetry"):
            raise ImportError("simulated missing otel sdk")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", _blocked)
    result = configure_platform(
        "layer4-agents",
        endpoint="http://otel-collector:4318",
    )
    assert result.provider is None
    assert result.service_name == "layer4-agents"


def test_configure_platform_does_not_require_sdk_on_import() -> None:
    from value_fabric.shared import observability as obs

    tracer = obs.get_tracer("value_fabric.shared.observability.tests")
    span = tracer.start_span("platform-client")
    assert span is not None
    span.end()


class _DummyExporter:
    def __init__(self, *, endpoint: str) -> None:
        self.endpoint = endpoint

    def export(self, spans: object) -> int:
        return 0

    def shutdown(self, timeout_millis: int = 0) -> bool:
        return True

    def force_flush(self, timeout_millis: int = 0) -> bool:
        return True


def _stub_otlp_exporter(monkeypatch: pytest.MonkeyPatch) -> None:
    exporter_mod = pytest.importorskip(
        "opentelemetry.exporter.otlp.proto.http.trace_exporter"
    )
    monkeypatch.setattr(exporter_mod, "OTLPSpanExporter", _DummyExporter)


def test_configure_platform_installs_provider_when_endpoint_and_sdk_present(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    otel = pytest.importorskip("opentelemetry")
    pytest.importorskip("opentelemetry.sdk.trace")
    _stub_otlp_exporter(monkeypatch)
    monkeypatch.setenv("OTEL_SAMPLE_RATIO", "0.25")

    provider = None
    try:
        result = configure_platform(
            "layer4-agents",
            layer="l4",
            service_version="1.2.0",
            endpoint="http://otel-collector:4318",
        )
        provider = result.provider
        assert provider is not None
        assert result.service_name == "layer4-agents"
        assert otel.trace.get_tracer_provider() is provider
        attributes = dict(provider.resource.attributes)
        assert attributes["service.name"] == "layer4-agents"
        assert attributes["service.namespace"] == "fabric4l"
        assert attributes["service.layer"] == "l4"
        assert attributes["service.version"] == "1.2.0"
        assert result.sample_ratio == pytest.approx(0.25)
    finally:
        shutdown = getattr(provider, "shutdown", None)
        if callable(shutdown):
            shutdown()


def test_configure_platform_invalid_sample_ratio_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pytest.importorskip("opentelemetry")
    pytest.importorskip("opentelemetry.sdk.trace")
    _stub_otlp_exporter(monkeypatch)
    monkeypatch.setenv("OTEL_SAMPLE_RATIO", "not-a-number")

    result = configure_platform(
        "layer4-agents",
        endpoint="http://otel-collector:4318",
    )
    assert result.provider is not None
    assert result.sample_ratio == pytest.approx(0.01)


def test_configure_platform_fails_closed_when_exporter_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pytest.importorskip("opentelemetry")
    pytest.importorskip("opentelemetry.sdk.trace")
    exporter_mod = pytest.importorskip(
        "opentelemetry.exporter.otlp.proto.http.trace_exporter"
    )

    class _BoomExporter:
        def __init__(self, *, endpoint: str) -> None:
            raise RuntimeError("collector unavailable")

    monkeypatch.setattr(exporter_mod, "OTLPSpanExporter", _BoomExporter)

    result = configure_platform(
        "layer4-agents",
        endpoint="http://otel-collector:4318",
    )
    assert result.provider is None
    assert result.service_name == "layer4-agents"


def test_configure_platform_reuses_installed_provider_instead_of_overriding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    otel = pytest.importorskip("opentelemetry")
    pytest.importorskip("opentelemetry.sdk.trace")
    _stub_otlp_exporter(monkeypatch)

    first = configure_platform(
        "layer4-agents",
        layer="l4",
        endpoint="http://otel-collector:4318",
    )
    second = configure_platform(
        "layer5-ground-truth",
        layer="l5",
        endpoint="http://otel-collector:4318",
    )
    installed = otel.trace.get_tracer_provider()
    assert first.provider is not None
    assert second.provider is first.provider
    assert installed is first.provider


def test_correlation_fields_use_active_span_when_unbound() -> None:
    otel = pytest.importorskip("opentelemetry")
    pytest.importorskip("opentelemetry.sdk.trace")
    from opentelemetry.sdk.trace import TracerProvider

    previous = otel.trace.get_tracer_provider()
    provider = TracerProvider()
    otel.trace.set_tracer_provider(provider)
    try:
        tracer = otel.trace.get_tracer("platform-tests")
        with tracer.start_as_current_span("corr") as span:
            ctx = span.get_span_context()
            fields = correlation_fields()
        assert fields["trace_id"] == format(ctx.trace_id, "032x")
        assert fields["span_id"] == format(ctx.span_id, "016x")
        assert fields["request_id"] == format(ctx.trace_id, "032x")
    finally:
        otel.trace.set_tracer_provider(previous)
        provider.shutdown()
