from __future__ import annotations

"""Health, metrics, admin, and proxy-pool route registrations."""

from fastapi import APIRouter, Depends
from value_fabric.shared.identity.dependencies import require_authenticated

from . import admin_handlers
from .schemas.admin_schemas import HealthCheckResponse, ProxyPoolResponse

router = APIRouter()
router.add_api_route(
    "/health",
    admin_handlers.health_check,
    methods=["GET"],
    response_model=HealthCheckResponse,
)
router.add_api_route(
    "/metrics",
    admin_handlers.metrics_endpoint,
    methods=["GET"],
    dependencies=[Depends(require_authenticated)],
)
router.add_api_route(
    "/admin/cleanup", admin_handlers.trigger_cleanup, methods=["POST"]
)
router.add_api_route(
    "/proxy-pools",
    admin_handlers.create_proxy_pool_endpoint,
    methods=["POST"],
    response_model=ProxyPoolResponse,
)
