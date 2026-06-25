from __future__ import annotations

"""Scraping job route registrations."""

from fastapi import APIRouter

from . import job_handlers
from .schemas.content_schemas import DomainFallbackStatsResponse, RouterQualityReportResponse
from .schemas.job_schemas import JobListResponse, JobProgressResponse, ScrapingJobDetail

router = APIRouter()
router.add_api_route(
    "/jobs/{job_id}/router-report",
    job_handlers.get_job_router_report,
    methods=["GET"],
    response_model=RouterQualityReportResponse,
)
router.add_api_route(
    "/domains/{domain}/fallback-stats",
    job_handlers.get_domain_fallback_stats,
    methods=["GET"],
    response_model=DomainFallbackStatsResponse,
)
router.add_api_route(
    "/jobs", job_handlers.list_jobs, methods=["GET"], response_model=JobListResponse
)
router.add_api_route(
    "/jobs/{job_id}",
    job_handlers.get_job,
    methods=["GET"],
    response_model=ScrapingJobDetail,
)
router.add_api_route(
    "/jobs/{job_id}", job_handlers.cancel_job, methods=["DELETE"], status_code=202
)
router.add_api_route(
    "/jobs/{job_id}/progress",
    job_handlers.get_job_progress,
    methods=["GET"],
    response_model=JobProgressResponse,
)
router.add_api_route(
    "/jobs/{job_id}/results", job_handlers.get_job_results, methods=["GET"]
)
router.add_api_route(
    "/jobs/{job_id}/retry", job_handlers.retry_job, methods=["POST"], status_code=202
)
