from __future__ import annotations

"""Formula mutation routes."""

from fastapi import APIRouter, status

from . import formulas

router = APIRouter()

router.add_api_route(
    "/formulas",
    formulas.create_formula,
    methods=["POST"],
    response_model=formulas.FormulaMetadata,
    status_code=status.HTTP_201_CREATED,
    tags=["Formulas"],
    summary="Create Formula",
    description="Create a new formula with variables and initial version.",
)
router.add_api_route(
    "/formulas/{formula_id}",
    formulas.update_formula,
    methods=["PATCH"],
    response_model=formulas.FormulaMetadata,
    tags=["Formulas"],
    summary="Update Formula",
    description="Update an existing formula. Creates new version if expression changes.",
)
router.add_api_route(
    "/formulas/{formula_id}",
    formulas.delete_formula,
    methods=["DELETE"],
    tags=["Formulas"],
    summary="Delete Formula",
    description="Delete a formula and all its versions. Admin only.",
)
