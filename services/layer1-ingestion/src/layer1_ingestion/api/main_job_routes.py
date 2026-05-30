from __future__ import annotations

"""Scraping job route registrations."""

from fastapi import APIRouter

from . import main

router = APIRouter()
router.add_api_route(
    "/jobs/{job_id}/router-report",
    main.get_job_router_report,
    methods=["GET"],
    response_model=main.RouterQualityReportResponse,
)
router.add_api_route(
    "/domains/{domain}/fallback-stats",
    main.get_domain_fallback_stats,
    methods=["GET"],
    response_model=main.DomainFallbackStatsResponse,
)
router.add_api_route(
    "/jobs", main.list_jobs, methods=["GET"], response_model=main.JobListResponse
)
router.add_api_route(
    "/jobs/{job_id}",
    main.get_job,
    methods=["GET"],
    response_model=main.ScrapingJobDetail,
)
router.add_api_route(
    "/jobs/{job_id}", main.cancel_job, methods=["DELETE"], status_code=202
)
router.add_api_route(
    "/jobs/{job_id}/progress",
    main.get_job_progress,
    methods=["GET"],
    response_model=main.JobProgressResponse,
)
router.add_api_route("/jobs/{job_id}/results", main.get_job_results, methods=["GET"])
router.add_api_route(
    "/jobs/{job_id}/retry", main.retry_job, methods=["POST"], status_code=202
)
