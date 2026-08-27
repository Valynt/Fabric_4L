"""System routes for Layer 6 API."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from value_fabric.shared.probes import normalize_probe_response

router = APIRouter(tags=["system"])


@router.get("/health", response_model=None, include_in_schema=False)
async def health_check(request: Request):
    """Service-local health adapter using the shared probe contract."""
    from .. import main as handlers

    return normalize_probe_response(
        dict(await handlers.health_check(request)),
        default_service="layer6-benchmarks",
    )


@router.get("/ready", response_model=None)
async def readiness_check():
    """Dependency readiness contract for orchestration and probes."""
    from .. import main as handlers

    payload = normalize_probe_response(
        dict(await handlers.readiness_check()),
        default_service="layer6-benchmarks",
    )
    if payload["readiness"]["is_ready"]:
        return payload
    return JSONResponse(status_code=503, content=payload)


@router.get(
    "/readiness",
    response_model=None,
    deprecated=True,
    include_in_schema=True,
    openapi_extra={
        "x-deprecated-since": "2026-05-29",
        "x-deprecated-removal-date": "2026-09-30",
        "x-deprecation-owner": "layer6-benchmarks",
    },
)
async def readiness_alias():
    """Temporary alias for /ready; prefer /ready (deprecated alias)."""
    return await readiness_check()
