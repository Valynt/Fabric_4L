from __future__ import annotations

from types import SimpleNamespace

import pytest
from value_fabric.shared.probes import normalize_probe_payload, normalize_probe_response


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


def test_shared_probe_contract_normalizes_legacy_status_and_dependency_aliases() -> None:
    payload = normalize_probe_payload(
        status="ok",
        service="layerX",
        readiness=None,
        dependencies=[
            {
                "name": "neo4j",
                "status": "failed",
                "failure_reason": "neo4j_unreachable",
            }
        ],
    )

    assert payload["status"] == "healthy"
    assert payload["readiness"] == {"is_ready": True, "reason": "dependencies_available"}
    assert payload["dependencies"][0]["status"] == "unhealthy"
    assert payload["dependencies"][0]["reason"] == "neo4j_unreachable"
    assert payload["dependencies"][0]["error"] == "neo4j_unreachable"


def test_normalize_probe_response_preserves_extra_fields() -> None:
    payload = normalize_probe_response(
        {
            "status": "not_ready",
            "checks": {"database": {"status": "ok"}},
            "service": "layerY",
        },
        default_service="layerY",
    )

    assert payload["status"] == "not_ready"
    assert payload["readiness"] == {"is_ready": False, "reason": "dependency_unhealthy"}
    assert payload["checks"] == {"database": {"status": "ok"}}


@pytest.mark.asyncio
async def test_layer6_readiness_http_status_behavior(monkeypatch: pytest.MonkeyPatch) -> None:
    from layer6_benchmarks.api.routes import system as layer6_system

    async def ready() -> dict[str, str]:
        return {"status": "ready"}

    async def not_ready() -> dict[str, str]:
        return {"status": "not_ready"}

    monkeypatch.setattr(
        layer6_system,
        "_get_handlers",
        lambda: SimpleNamespace(readiness_check=ready),
    )
    payload = await layer6_system.readiness_check()
    assert payload["status"] == "ready"
    assert payload["readiness"]["is_ready"] is True

    monkeypatch.setattr(
        layer6_system,
        "_get_handlers",
        lambda: SimpleNamespace(readiness_check=not_ready),
    )
    response = await layer6_system.readiness_check()
    assert getattr(response, "status_code", 503) == 503


@pytest.mark.asyncio
async def test_layer6_health_adapter_backward_compatible(monkeypatch: pytest.MonkeyPatch) -> None:
    from layer6_benchmarks.api.routes import system as layer6_system

    async def health(_request: object) -> dict[str, str]:
        return {"status": "healthy", "service": "layer6-benchmarks", "version": "1.0.0"}

    monkeypatch.setattr(
        layer6_system,
        "_get_handlers",
        lambda: SimpleNamespace(health_check=health),
    )
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace()))
    payload = await layer6_system.health_check(request)

    assert payload["status"] == "healthy"
    assert payload["service"] == "layer6-benchmarks"
    assert payload["readiness"]["is_ready"] is True
    assert payload["version"] == "1.0.0"
