from __future__ import annotations

"""Graph-backed Value Pack routes."""

from fastapi import APIRouter

from . import value_packs

router = APIRouter()

router.add_api_route(
    "/packs",
    value_packs.list_packs,
    methods=["GET"],
    response_model=list[value_packs.PackSummary],
)
router.add_api_route(
    "/packs/{pack_id}",
    value_packs.get_pack,
    methods=["GET"],
    response_model=value_packs.PackDetail,
)
router.add_api_route(
    "/packs",
    value_packs.create_pack,
    methods=["POST"],
    response_model=value_packs.PackDetail,
    status_code=201,
)
router.add_api_route(
    "/packs/{pack_id}",
    value_packs.update_pack,
    methods=["PUT"],
    response_model=value_packs.PackDetail,
)
router.add_api_route(
    "/packs/{pack_id}/execute",
    value_packs.execute_pack,
    methods=["POST"],
    response_model=value_packs.PackExecuteResponse,
)
router.add_api_route(
    "/packs/{pack_id}/fork",
    value_packs.fork_pack,
    methods=["POST"],
    response_model=value_packs.PackForkResponse,
    status_code=201,
)
router.add_api_route(
    "/packs/{pack_id}/apply",
    value_packs.apply_pack,
    methods=["POST"],
    response_model=value_packs.PackExecuteResponse,
)
