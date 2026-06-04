from __future__ import annotations

"""Health, metrics, admin, and proxy-pool route registrations."""

from fastapi import APIRouter, Depends
from value_fabric.shared.identity.dependencies import require_authenticated

from . import main

router = APIRouter()
router.add_api_route(
    "/health",
    main.health_check,
    methods=["GET"],
    response_model=main.HealthCheckResponse,
)
router.add_api_route(
    "/metrics",
    main.metrics_endpoint,
    methods=["GET"],
    dependencies=[Depends(require_authenticated)],
)
router.add_api_route("/admin/cleanup", main.trigger_cleanup, methods=["POST"])
router.add_api_route(
    "/proxy-pools",
    main.create_proxy_pool_endpoint,
    methods=["POST"],
    response_model=main.ProxyPoolResponse,
)
