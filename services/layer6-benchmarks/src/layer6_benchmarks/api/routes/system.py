"""System routes for Layer 6 API."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from value_fabric.shared.probes import normalize_probe_payload

router = APIRouter(tags=["system"])

@router.get("/health", response_model=None, include_in_schema=False)
async def health_check(request: Request):
    """Service-local health adapter using the shared probe contract."""
    from .. import main as handlers

    legacy_payload = dict(await handlers.health_check(request))
    status = str(legacy_payload.get("status", "unknown"))
    normalized = normalize_probe_payload(
        status=status,
        service=str(legacy_payload.get("service", "layer6-benchmarks")),
        readiness={
            "is_ready": status == "healthy",
            "reason": "dependencies_available" if status == "healthy" else "dependency_unhealthy",
        },
        dependencies=[],
    )
    normalized.update(legacy_payload)
    return normalized


@router.get("/ready", response_model=None)
async def readiness_check():
    """Dependency readiness contract for orchestration and probes."""
    from .. import main as handlers

    payload = dict(await handlers.readiness_check())
    if payload.get("status") == "ready":
        return payload
    return JSONResponse(status_code=503, content=payload)


@router.get("/readiness", response_model=None, deprecated=True, include_in_schema=True)
async def readiness_alias():
    """Temporary alias for /ready; prefer /ready (deprecated alias)."""
    return await readiness_check()
