from __future__ import annotations

"""Formula registry read routes."""

from fastapi import APIRouter

from . import formulas

router = APIRouter()

router.add_api_route(
    "/formulas/variables",
    formulas.get_variables_registry,
    methods=["GET"],
    response_model=formulas.VariablesRegistryResponse,
    tags=["Formulas"],
    summary="Get Variables Registry",
    description="Returns metadata for all available formula variables.",
)
router.add_api_route(
    "/formulas",
    formulas.list_formulas,
    methods=["GET"],
    response_model=formulas.FormulasRegistryResponse,
    tags=["Formulas"],
    summary="List Registered Formulas",
    description="Returns all registered formulas with their metadata.",
)
router.add_api_route(
    "/formulas/{formula_id}",
    formulas.get_formula,
    methods=["GET"],
    response_model=formulas.FormulaMetadata,
    tags=["Formulas"],
    summary="Get Formula Details",
    description="Returns details for a specific registered formula.",
)
