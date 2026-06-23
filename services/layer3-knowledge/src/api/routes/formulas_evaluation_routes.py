from __future__ import annotations

"""Formula evaluation and scenario routes."""

from fastapi import APIRouter

from . import formulas

router = APIRouter()

router.add_api_route(
    "/formulas/evaluate",
    formulas.evaluate_formula,
    methods=["POST"],
    response_model=formulas.FormulaEvaluateResponse,
    tags=["Formulas"],
    summary="Evaluate Formula",
    description="Execute a formula with typed inputs and return the result.",
    responses={
        400: {"description": "Invalid inputs or formula"},
        422: {"description": "Validation error"},
    },
)
router.add_api_route(
    "/formulas/scenario",
    formulas.calculate_scenario,
    methods=["POST"],
    response_model=formulas.ScenarioResponse,
    tags=["Formulas"],
    summary="Calculate What-If Scenario",
    description="Calculate new business case metrics based on variable adjustments.",
    responses={400: {"description": "Invalid adjustments or missing base case data"}},
)
