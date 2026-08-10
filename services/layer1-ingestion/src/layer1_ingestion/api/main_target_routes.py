from __future__ import annotations

"""Scraping target route registrations."""

from fastapi import APIRouter

from . import target_handlers
from .schemas.content_schemas import CrawlDecisionSummary
from .schemas.target_schemas import (
    ExecuteTargetResponse,
    ScrapingTargetDetail,
    TargetListResponse,
    ValidateTargetResponse,
)

router = APIRouter()
router.add_api_route(
    "/targets",
    target_handlers.list_targets,
    methods=["GET"],
    response_model=TargetListResponse,
)
router.add_api_route(
    "/targets",
    target_handlers.create_target,
    methods=["POST"],
    response_model=ScrapingTargetDetail,
    status_code=201,
)
router.add_api_route(
    "/targets/{target_id}",
    target_handlers.get_target,
    methods=["GET"],
    response_model=ScrapingTargetDetail,
)
router.add_api_route(
    "/targets/{target_id}",
    target_handlers.update_target,
    methods=["PUT"],
    response_model=ScrapingTargetDetail,
)
router.add_api_route(
    "/targets/{target_id}",
    target_handlers.delete_target,
    methods=["DELETE"],
    status_code=204,
)
router.add_api_route(
    "/targets/{target_id}/validate",
    target_handlers.validate_target,
    methods=["POST"],
    response_model=ValidateTargetResponse,
)
router.add_api_route(
    "/targets/{target_id}/execute",
    target_handlers.execute_target,
    methods=["POST"],
    response_model=ExecuteTargetResponse,
    status_code=202,
)
router.add_api_route(
    "/targets/{target_id}/decisions",
    target_handlers.get_target_decisions,
    methods=["GET"],
    response_model=list[CrawlDecisionSummary],
)
