from __future__ import annotations

"""Compliance route registrations."""

from fastapi import APIRouter

from . import main

router = APIRouter()
router.add_api_route("/compliance/logs", main.list_compliance_logs, methods=["GET"])
router.add_api_route(
    "/compliance/summary",
    main.get_compliance_summary,
    methods=["GET"],
    response_model=main.ComplianceSummaryResponse,
)
