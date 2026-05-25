"""Pytest configuration for Layer 1 Ingestion tests."""

from __future__ import annotations

import importlib.util
import os
import sys
import types
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock

# Patch SQLite dialect to understand PostgreSQL JSONB (used by models)
# so that in-memory SQLite engines work in tests.
from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler  # noqa: E402


def _visit_jsonb(self, type_, **kw):
    return self.visit_JSON(type_, **kw)


SQLiteTypeCompiler.visit_JSONB = _visit_jsonb

# Stub optional heavy deps before any imports that transitively require them
try:
    import opentelemetry  # noqa: F401
except ImportError:
    pass


def _make_pkg(name: str) -> ModuleType:
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
_otel.trace.Span = getattr(_otel.trace, "Span", type("Span", (), {}))
_otel.trace.SpanContext = getattr(_otel.trace, "SpanContext", type("SpanContext", (), {}))
_otel.trace.Status = getattr(_otel.trace, "Status", type("Status", (), {}))
_otel.trace.StatusCode = getattr(_otel.trace, "StatusCode", type("StatusCode", (), {}))

_otel_sdk = sys.modules.get("opentelemetry.sdk") or _make_pkg("opentelemetry.sdk")
if not hasattr(_otel_sdk, "resources"):
    _otel_sdk.resources = _make_pkg("opentelemetry.sdk.resources")
_otel_sdk.resources.Resource = getattr(_otel_sdk.resources, "Resource", type("Resource", (), {}))

if not hasattr(_otel_sdk, "trace"):
    _otel_sdk.trace = _make_pkg("opentelemetry.sdk.trace")
_otel_sdk.trace.TracerProvider = getattr(_otel_sdk.trace, "TracerProvider", type("TracerProvider", (), {}))

_otel_sdk_trace_exp = sys.modules.get("opentelemetry.sdk.trace.export") or _make_pkg("opentelemetry.sdk.trace.export")
_otel_sdk_trace_exp.BatchSpanProcessor = getattr(_otel_sdk_trace_exp, "BatchSpanProcessor", type("BatchSpanProcessor", (), {}))
_otel_sdk_trace_exp.ConsoleSpanExporter = getattr(_otel_sdk_trace_exp, "ConsoleSpanExporter", type("ConsoleSpanExporter", (), {}))

_otel_grpc = sys.modules.get("opentelemetry.exporter.otlp.proto.grpc.trace_exporter") or _make_pkg("opentelemetry.exporter.otlp.proto.grpc.trace_exporter")
_otel_grpc.OTLPSpanExporter = getattr(_otel_grpc, "OTLPSpanExporter", type("OTLPSpanExporter", (), {}))

try:
    import psycopg2  # noqa: F401
except ImportError:
    sys.modules["psycopg2"] = MagicMock()

# Add src directory to Python path for imports
src_path = str(Path(__file__).parent.parent / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Add parent directory (services) so shared.* packages are importable
shared_root = str(Path(__file__).parent.parent.parent)
if shared_root not in sys.path:
    sys.path.insert(0, shared_root)

# Ensure PYTHONPATH includes src for subprocesses
os.environ["PYTHONPATH"] = src_path + os.pathsep + shared_root + os.pathsep + os.environ.get("PYTHONPATH", "")
os.environ["CORS_ORIGINS"] = '["http://localhost:3000"]'

