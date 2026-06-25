from __future__ import annotations

"""Compliance route registrations."""

from fastapi import APIRouter

from . import compliance_handlers
from .schemas.compliance_schemas import ComplianceSummaryResponse

router = APIRouter()
router.add_api_route(
    "/compliance/logs", compliance_handlers.list_compliance_logs, methods=["GET"]
)
router.add_api_route(
    "/compliance/summary",
    compliance_handlers.get_compliance_summary,
    methods=["GET"],
    response_model=ComplianceSummaryResponse,
)
