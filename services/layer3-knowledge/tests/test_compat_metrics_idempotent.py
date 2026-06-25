from __future__ import annotations

"""Regression test for duplicate prometheus counter registration in compat_metrics."""

import importlib
import importlib.util
import sys
import types
from pathlib import Path

import pytest

try:
    from prometheus_client import Counter as _PromCounter
except Exception:  # pragma: no cover
    _PromCounter = None

pytestmark = [
    pytest.mark.unit,
    pytest.mark.skipif(_PromCounter is None, reason="prometheus_client not available"),
]

SERVICES_DIR = Path(__file__).parents[1] / "src" / "services"
COMPAT_METRICS_PATH = SERVICES_DIR / "compat_metrics.py"


def _load_module_under_package(module_file: Path, package_name: str):
    module_name = f"{package_name}.{module_file.stem}"
    spec = importlib.util.spec_from_file_location(module_name, module_file)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _import_under_name(name: str):
    """Import compat_metrics under a synthetic package name so it executes fresh."""
    package = types.ModuleType(name)
    package.__path__ = [str(SERVICES_DIR)]
    sys.modules[name] = package

    # Relative import `from . import compat_policy` needs the dependency under
    # the synthetic package namespace. Load it directly to avoid touching the
    # real `services` package __init__.
    _load_module_under_package(SERVICES_DIR / "compat_policy.py", name)

    return _load_module_under_package(COMPAT_METRICS_PATH, name)


def test_compat_metrics_counters_are_singleton_per_process():
    first = _import_under_name("synthetic_services_first")
    second = _import_under_name("synthetic_services_second")

    assert first._ROUTE_COUNTER is second._ROUTE_COUNTER
    assert first._FIELD_COUNTER is second._FIELD_COUNTER

    first.record_deprecated_route_hit("/test", tenant_id="tenant-1", app_client="app-1")
    route_labels = first._ROUTE_COUNTER.labels(
        route="/test", tenant_id="tenant-1", app_client="app-1"
    )
    assert route_labels._value.get() == 1

    second.record_deprecated_route_hit("/test", tenant_id="tenant-1", app_client="app-1")
    assert route_labels._value.get() == 2

    first.record_deprecated_legacy_field_usage(
        "legacy_field", tenant_id="tenant-1", app_client="app-1"
    )
    field_labels = second._FIELD_COUNTER.labels(
        field="legacy_field", tenant_id="tenant-1", app_client="app-1"
    )
    assert field_labels._value.get() == 1
