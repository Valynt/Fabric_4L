from __future__ import annotations

"""In-memory ValuePack framework routes."""

from fastapi import APIRouter

from . import value_packs

router = APIRouter()

router.add_api_route(
    "/valuepacks",
    value_packs.list_valuepacks,
    methods=["GET"],
    response_model=value_packs.ValuePackListResponse,
)
router.add_api_route(
    "/valuepacks/{industry_id}",
    value_packs.get_valuepack,
    methods=["GET"],
    response_model=value_packs.ValuePackResponse,
)
router.add_api_route(
    "/valuepacks",
    value_packs.create_valuepack,
    methods=["POST"],
    response_model=value_packs.ValuePackResponse,
    status_code=201,
)
router.add_api_route(
    "/valuepacks/{industry_id}",
    value_packs.update_valuepack,
    methods=["PUT"],
    response_model=value_packs.ValuePackResponse,
)
router.add_api_route(
    "/valuepacks/{industry_id}",
    value_packs.delete_valuepack,
    methods=["DELETE"],
    status_code=204,
)
router.add_api_route(
    "/valuepacks/ontology-map",
    value_packs.get_ontology_map,
    methods=["GET"],
    response_model=value_packs.OntologyMapResponse,
)
router.add_api_route(
    "/valuepacks/composable-templates",
    value_packs.get_composable_templates,
    methods=["GET"],
    response_model=value_packs.ComposableTemplateLibraryResponse,
)
router.add_api_route(
    "/valuepacks/compare",
    value_packs.compare_valuepacks,
    methods=["POST"],
    response_model=value_packs.ValuePackComparisonResponse,
)
router.add_api_route(
    "/valuepacks/{industry_id}/seed",
    value_packs.seed_valuepack_data,
    methods=["POST"],
    status_code=201,
)
