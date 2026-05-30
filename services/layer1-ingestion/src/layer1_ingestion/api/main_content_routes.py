from __future__ import annotations

"""Content retrieval route registrations."""

from fastapi import APIRouter

from . import main

router = APIRouter()
router.add_api_route(
    "/content/raw/{content_id}",
    main.get_raw_content,
    methods=["GET"],
    response_model=main.RawContentResponse,
)
router.add_api_route(
    "/content/extracted/{extracted_data_id}",
    main.get_extracted_data,
    methods=["GET"],
    response_model=main.ExtractedDataResponse,
)
router.add_api_route("/content", main.list_content, methods=["GET"])
