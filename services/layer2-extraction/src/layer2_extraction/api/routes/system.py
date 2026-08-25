"""System health and readiness routes for Layer 2 extraction service."""

from __future__ import annotations

from types import SimpleNamespace

from value_fabric.shared.probes import normalize_probe_response


async def _default_health_check() -> dict[str, object]:
    return {
        "status": "healthy",
        "service": "layer2-extraction",
        "readiness": {"is_ready": False, "reason": "neo4j_uninitialized"},
    }


async def health_check() -> dict[str, object]:
    """Return service health envelope.

    Delegates to ``handlers.health_check`` so contract tests can patch
    the handler without replacing the public entrypoint.
    """
    result: dict[str, object] = await handlers.health_check()
    result.setdefault(
        "readiness",
        {"is_ready": False, "reason": "neo4j_uninitialized"},
    )
    return normalize_probe_response(result, default_service="layer2-extraction")


async def readiness_check() -> dict[str, str]:
    """Return readiness status."""
    return {"status": "ready"}


# Namespace for test-level handler patching (see test_system_route_contract.py)
handlers = SimpleNamespace(health_check=_default_health_check)
