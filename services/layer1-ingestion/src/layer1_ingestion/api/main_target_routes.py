from __future__ import annotations

"""Scraping target route registrations."""

from fastapi import APIRouter

from . import main

router = APIRouter()
router.add_api_route(
    "/targets",
    main.list_targets,
    methods=["GET"],
    response_model=main.TargetListResponse,
)
router.add_api_route(
    "/targets",
    main.create_target,
    methods=["POST"],
    response_model=main.ScrapingTargetDetail,
    status_code=201,
)
router.add_api_route(
    "/targets/{target_id}",
    main.get_target,
    methods=["GET"],
    response_model=main.ScrapingTargetDetail,
)
router.add_api_route(
    "/targets/{target_id}",
    main.update_target,
    methods=["PUT"],
    response_model=main.ScrapingTargetDetail,
)
router.add_api_route(
    "/targets/{target_id}", main.delete_target, methods=["DELETE"], status_code=204
)
router.add_api_route(
    "/targets/{target_id}/validate",
    main.validate_target,
    methods=["POST"],
    response_model=main.ValidateTargetResponse,
)
router.add_api_route(
    "/targets/{target_id}/execute",
    main.execute_target,
    methods=["POST"],
    response_model=main.ExecuteTargetResponse,
    status_code=202,
)
router.add_api_route(
    "/targets/{target_id}/decisions",
    main.get_target_decisions,
    methods=["GET"],
    response_model=list[main.CrawlDecisionSummary],
)
