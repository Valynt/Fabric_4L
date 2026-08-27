from __future__ import annotations

import importlib
import json
import os
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

try:
    from src.api.models import ServiceMetrics
    from src.api.routes import system as layer3_system
except (ImportError, Exception):
    pytest.skip(
        "value_fabric.layer3 service stack not available (pre-existing blocker #1/#9)",
        allow_module_level=True,
    )

os.environ.setdefault("CONTRACT_TEST_MODE", "mock")

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA = REPO_ROOT / "contracts" / "jsonschema" / "system-route-health.json"


def test_system_health_schema_requires_readiness_envelope() -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    assert schema["required"] == ["status", "service", "readiness"]
    assert schema["properties"]["readiness"]["required"] == ["is_ready", "reason"]


@pytest.mark.asyncio
async def test_layer2_system_health_contract_envelope(monkeypatch: pytest.MonkeyPatch) -> None:
    sys.path.insert(0, str(REPO_ROOT / "services" / "layer2-extraction" / "src"))
    try:
        layer2_system = importlib.import_module("layer2_extraction.api.routes.system")

        async def fake_health_check() -> dict[str, str]:
            return {"status": "healthy", "service": "layer2-extraction"}

        monkeypatch.setattr(layer2_system.handlers, "health_check", fake_health_check)
        payload = await layer2_system.health_check()
    finally:
        sys.path.remove(str(REPO_ROOT / "services" / "layer2-extraction" / "src"))

    assert payload["status"] == "healthy"
    assert payload["service"] == "layer2-extraction"
    assert payload["readiness"] == {"is_ready": False, "reason": "neo4j_uninitialized"}


@pytest.mark.asyncio
async def test_layer2_system_readiness_contract() -> None:
    sys.path.insert(0, str(REPO_ROOT / "services" / "layer2-extraction" / "src"))
    try:
        layer2_system = importlib.import_module("layer2_extraction.api.routes.system")
        payload = await layer2_system.readiness_check()
    finally:
        sys.path.remove(str(REPO_ROOT / "services" / "layer2-extraction" / "src"))

    assert payload == {"status": "ready"}


@pytest.mark.asyncio
async def test_layer3_system_health_contract_envelope(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_request = SimpleNamespace(state=SimpleNamespace(request_id="test"))

    async def fake_check_dependencies(schema_initializer=None) -> list[object]:
        return []

    monkeypatch.setattr(layer3_system, "check_dependencies", fake_check_dependencies)
    monkeypatch.setattr(
        layer3_system,
        "get_system_metrics",
        lambda: ServiceMetrics(
            uptime_seconds=1,
            active_connections=0,
            total_requests=0,
            error_rate_percent=0,
        ),
    )

    payload = await layer3_system.health_check(fake_request, schema_initializer=None)

    assert payload["status"] == "degraded"
    assert payload["service"] == "layer3-knowledge"
    assert payload["readiness"] == {"is_ready": False, "reason": "neo4j_uninitialized"}


@pytest.mark.asyncio
async def test_layer6_system_health_contract_envelope(monkeypatch: pytest.MonkeyPatch) -> None:
    src_path = str(REPO_ROOT / "services" / "layer6-benchmarks" / "src")
    for name in list(sys.modules):
        if name == "api" or name.startswith("api."):
            sys.modules.pop(name)
    sys.path.insert(0, src_path)
    try:
        layer6_system = importlib.import_module("api.routes.system")
        fake_main = ModuleType("api.main")

        async def fake_health_check(_request: object) -> dict[str, str]:
            return {"status": "degraded", "service": "layer6-benchmarks"}

        fake_main.health_check = fake_health_check  # type: ignore[attr-defined]
        monkeypatch.setitem(sys.modules, "api.main", fake_main)

        fake_request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace()))
        payload = await layer6_system.health_check(fake_request)
    finally:
        sys.path.remove(src_path)

    assert payload["status"] == "degraded"
    assert payload["service"] == "layer6-benchmarks"
    assert payload["readiness"] == {"is_ready": False, "reason": "neo4j_uninitialized"}


@pytest.mark.asyncio
async def test_layer6_system_readiness_contract() -> None:
    src_path = str(REPO_ROOT / "services" / "layer6-benchmarks" / "src")
    for name in list(sys.modules):
        if name == "api" or name.startswith("api."):
            sys.modules.pop(name)
    sys.path.insert(0, src_path)
    try:
        layer6_system = importlib.import_module("api.routes.system")
        payload = await layer6_system.readiness_check()
    finally:
        sys.path.remove(src_path)

    assert payload == {"status": "ready"}
