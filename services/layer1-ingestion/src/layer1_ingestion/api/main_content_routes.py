from __future__ import annotations

"""Content retrieval route registrations."""

from fastapi import APIRouter

from . import content_handlers
from .schemas.content_schemas import ExtractedDataResponse, RawContentResponse

router = APIRouter()
router.add_api_route(
    "/content/raw/{content_id}",
    content_handlers.get_raw_content,
    methods=["GET"],
    response_model=RawContentResponse,
    operation_id="get_raw_content",
    summary="Retrieve raw content by ID",
    tags=["Content"],
)
router.add_api_route(
    "/content/extracted/{extracted_data_id}",
    content_handlers.get_extracted_data,
    methods=["GET"],
    response_model=ExtractedDataResponse,
    operation_id="get_extracted_data",
    summary="Retrieve extracted data by ID",
    tags=["Content"],
)
router.add_api_route(
    "/content",
    content_handlers.list_content,
    methods=["GET"],
    operation_id="list_content",
    summary="List raw content with filtering",
    tags=["Content"],
)
