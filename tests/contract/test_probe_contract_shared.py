from __future__ import annotations

from types import SimpleNamespace

import pytest

from value_fabric.shared.probes import normalize_probe_payload


def test_shared_probe_contract_shape() -> None:
    payload = normalize_probe_payload(
        status="healthy",
        service="layerX",
        readiness={"is_ready": True, "reason": "dependencies_available"},
        dependencies=[{"name": "db", "status": "healthy", "required": True}],
    )

    assert payload["status"] == "healthy"
    assert payload["service"] == "layerX"
    assert payload["liveness"] == "alive"
    assert payload["readiness"] == {"is_ready": True, "reason": "dependencies_available"}
    assert payload["dependencies"][0]["name"] == "db"
    assert payload["dependency_status"] == payload["dependencies"]


@pytest.mark.asyncio
async def test_layer6_readiness_http_status_behavior(monkeypatch: pytest.MonkeyPatch) -> None:
    from api.routes import system as layer6_system

    async def ready() -> dict[str, str]:
        return {"status": "ready"}

    async def not_ready() -> dict[str, str]:
        return {"status": "not_ready"}

    monkeypatch.setattr(layer6_system.handlers, "readiness_check", ready)
    payload = await layer6_system.readiness_check()
    assert payload["status"] == "ready"

    monkeypatch.setattr(layer6_system.handlers, "readiness_check", not_ready)
    response = await layer6_system.readiness_check()
    assert getattr(response, "status_code", 503) == 503


@pytest.mark.asyncio
async def test_layer6_health_adapter_backward_compatible(monkeypatch: pytest.MonkeyPatch) -> None:
    from api.routes import system as layer6_system

    async def health(_request: object) -> dict[str, str]:
        return {"status": "healthy", "service": "layer6-benchmarks", "version": "1.0.0"}

    monkeypatch.setattr(layer6_system.handlers, "health_check", health)
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace()))
    payload = await layer6_system.health_check(request)

    assert payload["status"] == "healthy"
    assert payload["service"] == "layer6-benchmarks"
    assert payload["readiness"]["is_ready"] is True
    assert payload["version"] == "1.0.0"
