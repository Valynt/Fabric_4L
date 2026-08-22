"""Pytest bootstrap for Layer 2 extraction tests.

JWT_SECRET is set before any app module is imported so that GovernanceMiddleware
initialises with a known secret that matches the test JWT tokens.

The Layer 2 test suite may use a lightweight ``openai`` stub because specific
unit tests bypass client construction and do not exercise the OpenAI SDK. The
repository package namespace, however, must never be stubbed: repository-level
collection imports Layer 3 and Layer 4 tests in the same interpreter, and a
``sys.modules['value_fabric']`` module stub turns the real package namespace
into a non-package. H-04 therefore makes the shared ``value_fabric`` imports a
mandatory collection-time dependency instead of masking them with stubs.
"""
from __future__ import annotations

import os as _os
_os.environ.setdefault("JWT_SECRET", "test-secret-key-for-layer2-tests-32b")
_os.environ.setdefault("ENVIRONMENT", "test")
_os.environ.setdefault("LAYER2_ENV", "test")
_os.environ.setdefault("TESTING", "true")
_os.environ.setdefault("ALLOW_LEGACY_TEST_TENANT_IDS", "true")

import importlib
import sys
import types
from unittest.mock import MagicMock

# ---------------------------------------------------------------------------
# openai stub — AsyncOpenAI is instantiated in EntityDeduplicator.__init__,
# which is bypassed in unit tests, so a bare type stub is sufficient.
# ---------------------------------------------------------------------------
if "openai" not in sys.modules:
    _openai = types.ModuleType("openai")
    _openai.AsyncOpenAI = type("AsyncOpenAI", (), {})
    sys.modules["openai"] = _openai

# ---------------------------------------------------------------------------
# opentelemetry / asyncpg stubs for collection without optional deps
# ---------------------------------------------------------------------------
try:
    import opentelemetry  # noqa: F401
except ImportError:
    pass

import types
import importlib.util

def _make_pkg(name):
    m = types.ModuleType(name)
    m.__path__ = []
    spec = importlib.util.spec_from_loader(name, loader=None)
    spec.submodule_search_locations = []
    m.__spec__ = spec
    sys.modules[name] = m
    return m

# Idempotently ensure opentelemetry stubs exist (another conftest may have created a partial stub)
_otel = sys.modules.get("opentelemetry") or _make_pkg("opentelemetry")
if not hasattr(_otel, "trace"):
    _otel.trace = _make_pkg("opentelemetry.trace")

_exp = sys.modules.get("opentelemetry.exporter") or _make_pkg("opentelemetry.exporter")
_otlp = sys.modules.get("opentelemetry.exporter.otlp") or _make_pkg("opentelemetry.exporter.otlp")
_proto = sys.modules.get("opentelemetry.exporter.otlp.proto") or _make_pkg("opentelemetry.exporter.otlp.proto")
_http = sys.modules.get("opentelemetry.exporter.otlp.proto.http") or _make_pkg("opentelemetry.exporter.otlp.proto.http")
_txe = sys.modules.get("opentelemetry.exporter.otlp.proto.http.trace_exporter") or _make_pkg("opentelemetry.exporter.otlp.proto.http.trace_exporter")
_txe.OTLPSpanExporter = getattr(_txe, "OTLPSpanExporter", type("OTLPSpanExporter", (), {}))

_inst = sys.modules.get("opentelemetry.instrumentation") or _make_pkg("opentelemetry.instrumentation")
if not hasattr(_inst, "fastapi"):
    _inst.fastapi = _make_pkg("opentelemetry.instrumentation.fastapi")
_inst.fastapi.FastAPIInstrumentor = getattr(_inst.fastapi, "FastAPIInstrumentor", type("FastAPIInstrumentor", (), {}))

_sdk = sys.modules.get("opentelemetry.sdk") or _make_pkg("opentelemetry.sdk")
if not hasattr(_sdk, "resources"):
    _sdk.resources = _make_pkg("opentelemetry.sdk.resources")
_sdk.resources.SERVICE_NAME = getattr(_sdk.resources, "SERVICE_NAME", "test")
_sdk.resources.Resource = getattr(_sdk.resources, "Resource", type("Resource", (), {}))
if not hasattr(_sdk, "trace"):
    _sdk.trace = _make_pkg("opentelemetry.sdk.trace")
_sdk.trace.TracerProvider = getattr(_sdk.trace, "TracerProvider", type("TracerProvider", (), {}))

_sdk_trace_exp = sys.modules.get("opentelemetry.sdk.trace.export") or _make_pkg("opentelemetry.sdk.trace.export")
_sdk_trace_exp.BatchSpanProcessor = getattr(_sdk_trace_exp, "BatchSpanProcessor", type("BatchSpanProcessor", (), {}))

try:
    import asyncpg  # noqa: F401
except ImportError:
    _asyncpg_stub = types.ModuleType("asyncpg")
    _asyncpg_stub.__spec__ = importlib.util.spec_from_loader("asyncpg", loader=None)
    sys.modules["asyncpg"] = _asyncpg_stub

# ---------------------------------------------------------------------------
# value_fabric.shared is a mandatory repository package. Import it for an
# actionable collection-time failure if the monorepo bootstrap is broken, but
# never inject a ModuleType stub for the package root.
# ---------------------------------------------------------------------------
try:
    _typed_dict_module = importlib.import_module("value_fabric.shared.models.typed_dict")
except ModuleNotFoundError as exc:  # pragma: no cover - fail-fast bootstrap path
    raise RuntimeError(
        "Layer 2 tests require the real value_fabric.shared package. "
        "Run pytest from the repository root or install tests/requirements-test.txt; "
        "do not stub value_fabric because it breaks repository-level collection."
    ) from exc

if not hasattr(_typed_dict_module, "TypedDictModel"):
    _typed_dict_module.TypedDictModel = type("TypedDictModel", (), {})


# ---------------------------------------------------------------------------
# Test-only tenant kill-switch bypass so route tests run without Redis.
# ---------------------------------------------------------------------------
import pytest  # noqa: E402
from layer2_extraction.api.main import app as _layer2_app  # noqa: E402
from value_fabric.shared.testing.governance import (  # noqa: E402
    patch_governance_middleware_for_tests,
)


@pytest.fixture(autouse=True)
def _patch_governance_middleware_for_tests():
    """Ensure GovernanceMiddleware does not 503 when Redis is unavailable."""
    patch_governance_middleware_for_tests(_layer2_app)
    yield
