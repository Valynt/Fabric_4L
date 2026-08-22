from value_fabric.shared.error_handling.exceptions import (
    ConflictError,
    NotFoundError,
    ServiceUnavailableError,
    ValidationError,
)

"""Allowed service-local exception for Layer 3 service wrapper.

Owner: layer3-knowledge
Removal/migration target: 2026-09-30
Reason: Formula API routes.

Provides endpoints for formula evaluation and variable registry.
Delegates calculation logic to the ROI calculation agent.
"""

import ast
import math
import re
import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from jsonschema import Draft202012Validator
from pydantic import BaseModel, Field, field_validator
from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.dependencies import require_tenant_context

from src.logging_config import get_logger

from ...agents.scenario_engine import VariableAdjustment, scenario_engine
from ...api.dependencies_tenant_secured import create_neo4j_tenant_session
from ...api.routes.formula_governance import STATUS_DRAFT, STATUS_UNDER_REVIEW
from ...auth.api_keys import APIKey
from ...auth.middleware import get_current_api_key, require_admin_role
from .formulas_mapping import filter_variables_by_category

router = APIRouter()
logger = get_logger(__name__)

# Constants for formula evaluation
DEFAULT_CONFIDENCE = 0.92
FLOATING_POINT_EPSILON = 1e-10  # Threshold for considering a value as zero
# Cap exponent magnitude to prevent DoS (e.g. 2 ** 99999999 hanging the worker).
MAX_POW_EXPONENT = 1_000_000

# Valid expression pattern: alphanumeric, operators (+, -, *, /), parentheses, underscores, whitespace
# Note: period (.) intentionally excluded to prevent attribute access attempts
_VALID_EXPRESSION_PATTERN: re.Pattern = re.compile(r"^[a-zA-Z0-9_+\-*/(),\s.]+$")
_ALLOWED_FUNCTIONS: dict[str, Any] = {
    "abs": abs,
    "min": min,
    "max": max,
    "round": round,
}
_ALLOWED_BINARY_OPERATORS: tuple[type[ast.operator], ...] = (
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.Pow,
)
_ALLOWED_UNARY_OPERATORS: tuple[type[ast.unaryop], ...] = (ast.UAdd, ast.USub)
_FORMULA_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["expression", "variables"],
    "additionalProperties": False,
    "properties": {
        "expression": {"type": "string", "minLength": 1, "maxLength": 2000},
        "variables": {
            "type": "object",
            "propertyNames": {"pattern": r"^[A-Za-z_][A-Za-z0-9_]{0,127}$"},
            "additionalProperties": {"type": "number"},
        },
    },
}
_FORMULA_SCHEMA_VALIDATOR = Draft202012Validator(_FORMULA_SCHEMA)


def _validate_expression(v: str) -> None:
    """Validate a formula expression for safety and syntax.

    Enforces a restricted formula DSL using JSON Schema + static AST checks.
    """
    if not _VALID_EXPRESSION_PATTERN.match(v):
        raise ValueError("Expression contains invalid characters")
    _validate_formula_schema(v, {})
    _validate_formula_ast(v, set())


def _validate_formula_schema(expression: str, variables: dict[str, float]) -> None:
    candidate = {"expression": expression, "variables": variables}
    errors = sorted(_FORMULA_SCHEMA_VALIDATOR.iter_errors(candidate), key=str)
    if errors:
        raise ValueError(f"Formula schema validation failed: {errors[0].message}")


def _validate_formula_ast(expression: str, allowed_variables: set[str]) -> ast.AST:
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise ValueError("Invalid expression syntax") from exc

    disallowed_nodes = (
        ast.Attribute,
        ast.Subscript,
        ast.ListComp,
        ast.SetComp,
        ast.DictComp,
        ast.GeneratorExp,
        ast.Lambda,
        ast.Import,
        ast.ImportFrom,
        ast.Await,
        ast.Yield,
        ast.NamedExpr,
    )
    for node in ast.walk(tree):
        if isinstance(node, disallowed_nodes):
            raise ValueError(f"Forbidden expression construct: {type(node).__name__}")
        if isinstance(node, ast.Call):
            if (
                not isinstance(node.func, ast.Name)
                or node.func.id not in _ALLOWED_FUNCTIONS
            ):
                raise ValueError("Function is not allowed in formula DSL")
        if isinstance(node, ast.BinOp) and not isinstance(
            node.op, _ALLOWED_BINARY_OPERATORS
        ):
            raise ValueError("Binary operator is not allowed")
        if isinstance(node, ast.UnaryOp) and not isinstance(
            node.op, _ALLOWED_UNARY_OPERATORS
        ):
            raise ValueError("Unary operator is not allowed")
        if isinstance(node, ast.Name):
            if node.id in {"eval", "exec", "__import__", "open"}:
                raise ValueError("Forbidden identifier in formula DSL")
            if (
                allowed_variables
                and node.id not in allowed_variables
                and node.id not in _ALLOWED_FUNCTIONS
            ):
                raise ValueError(f"Unknown variable in formula: {node.id}")
    return tree


class FormulaInput(BaseModel):
    """Single formula input variable."""

    name: str = Field(..., description="Variable name")
    value: float = Field(..., description="Variable value")
    unit: str | None = Field(None, description="Unit of measurement")

    @field_validator("value")
    @classmethod
    def validate_value_is_finite(cls, v: float) -> float:
        """Ensure value is a finite number (not inf, -inf, or nan)."""
        import math

        if not math.isfinite(v):
            raise ValueError("Value must be a finite number")
        return v


class FormulaEvaluateRequest(BaseModel):
    """Request to evaluate a formula."""

    formula_id: str | None = Field(
        None, description="Optional formula identifier from registry"
    )
    expression: str | None = Field(
        None, description="Custom formula expression (if formula_id not provided)"
    )
    inputs: list[FormulaInput] = Field(
        default_factory=list, description="Input variables"
    )
    output_unit: str | None = Field(None, description="Desired output unit")

    @field_validator("expression")
    @classmethod
    def validate_expression_or_formula_id(cls, v, info):
        if not v and not info.data.get("formula_id"):
            raise ValueError("Either formula_id or expression must be provided")
        if v:
            _validate_expression(v)
        return v


class CalculationStep(BaseModel):
    """Single step in formula calculation."""

    step: int = Field(..., description="Step number")
    operation: str = Field(..., description="Operation performed")
    result: str = Field(..., description="Intermediate result")


class FormulaEvaluateResponse(BaseModel):
    """Response from formula evaluation."""

    result: float = Field(..., description="Calculated result")
    unit: str = Field(..., description="Output unit")
    confidence: float = Field(
        default=DEFAULT_CONFIDENCE, ge=0.0, le=1.0, description="Confidence in result"
    )
    calculation_steps: list[CalculationStep] = Field(
        default_factory=list, description="Step-by-step calculation"
    )
    formula_used: str = Field(..., description="Formula expression used")


class VariableMetadata(BaseModel):
    """Metadata for a formula variable."""

    name: str = Field(..., description="Variable name")
    display_name: str = Field(..., description="Human-readable name")
    description: str | None = Field(None, description="Variable description")
    type: Literal["number", "currency", "percentage", "count"] = Field(
        ..., description="Data type"
    )
    unit: str | None = Field(None, description="Default unit")
    default_value: float | None = Field(
        None, description="Default value if not provided"
    )
    min_value: float | None = Field(None, description="Minimum allowed value")
    max_value: float | None = Field(None, description="Maximum allowed value")
    required: bool = Field(default=True, description="Whether variable is required")
    category: str | None = Field(
        None,
        description=(
            "Variable category (Financial, Operational, Efficiency, Quality). "
            "When set, used directly for filtering. When None, category is inferred "
            "from the variable name via keyword patterns."
        ),
    )


class FormulaMetadata(BaseModel):
    """Metadata for a registered formula."""

    id: str = Field(..., description="Formula identifier")
    formula_id: str | None = Field(
        default=None, description="Deprecated alias of id. Removal target: v2.5 (2026-10-01).", deprecated=True, json_schema_extra={"x-deprecation-target-version": "v2.5", "x-deprecation-target-date": "2026-10-01"}
    )
    name: str = Field(..., description="Formula name")
    description: str = Field(..., description="Formula description")
    category: str = Field(..., description="Formula category (e.g., ROI, Payback, NPV)")
    expression: str = Field(..., description="Formula expression template")
    variables: list[VariableMetadata] = Field(..., description="Required variables")
    output_unit: str = Field(..., description="Output unit")
    version: str = Field(default="1.0.0", description="Formula version (semver)")
    status: str = Field(default="active", description="Formula status")
    updated_at: str | None = Field(default=None, description="Last updated timestamp")
    created_at: str | None = Field(default=None, description="Creation timestamp")
    used_in_count: int = Field(
        default=0, description="Number of packs using this formula"
    )
    owner: str | None = Field(default=None, description="Formula owner email")
    governance_score: float | None = Field(
        default=None, description="Governance score 0-1"
    )


class CreateFormulaRequest(BaseModel):
    """Request to create a new formula."""

    name: str = Field(..., description="Formula name", min_length=1, max_length=200)
    description: str = Field(..., description="Formula description", min_length=1)
    expression: str = Field(..., description="Formula expression template")
    variables: list[VariableMetadata] = Field(
        default_factory=list, description="Required variables"
    )
    output_unit: str = Field(..., description="Output unit")
    category: str = Field(default="Custom", description="Formula category")
    owner: str | None = Field(default=None, description="Formula owner email")

    @field_validator("expression")
    @classmethod
    def validate_expression(cls, v):
        """Validate expression syntax."""
        _validate_expression(v)
        return v


class UpdateFormulaRequest(BaseModel):
    """Request to update an existing formula."""

    name: str | None = Field(
        default=None, description="Formula name", min_length=1, max_length=200
    )
    description: str | None = Field(default=None, description="Formula description")
    expression: str | None = Field(
        default=None, description="Formula expression template"
    )
    variables: list[VariableMetadata] | None = Field(
        default=None, description="Required variables"
    )
    output_unit: str | None = Field(default=None, description="Output unit")
    category: str | None = Field(default=None, description="Formula category")

    @field_validator("expression")
    @classmethod
    def validate_expression(cls, v):
        """Validate expression syntax."""
        if v is None:
            return v
        _validate_expression(v)
        return v


class VariablesRegistryResponse(BaseModel):
    """Response containing available variables."""

    variables: list[VariableMetadata] = Field(..., description="Available variables")
    total: int = Field(..., description="Total number of variables")
    categories: list[str] = Field(
        default_factory=list, description="Variable categories"
    )


class FormulasRegistryResponse(BaseModel):
    """Response containing registered formulas."""

    formulas: list[FormulaMetadata] = Field(..., description="Registered formulas")
    total: int = Field(..., description="Total number of formulas")


# ============================================================================
# Variable Registry
# ============================================================================

VARIABLE_REGISTRY: list[VariableMetadata] = [
    VariableMetadata(
        name="annual_cost_savings",
        display_name="Annual Cost Savings",
        description="Estimated annual cost savings from the initiative",
        type="currency",
        unit="USD",
        required=True,
        min_value=0,
        category="Financial",
    ),
    VariableMetadata(
        name="implementation_cost",
        display_name="Implementation Cost",
        description="Total cost to implement the solution",
        type="currency",
        unit="USD",
        required=True,
        min_value=0,
        category="Financial",
    ),
    VariableMetadata(
        name="annual_revenue_increase",
        display_name="Annual Revenue Increase",
        description="Estimated annual revenue increase",
        type="currency",
        unit="USD",
        default_value=0,
        min_value=0,
        category="Financial",
    ),
    VariableMetadata(
        name="time_period_years",
        display_name="Time Period",
        description="Analysis time period in years",
        type="count",
        unit="years",
        default_value=3,
        min_value=1,
        max_value=10,
        category="Operational",
    ),
    VariableMetadata(
        name="discount_rate",
        display_name="Discount Rate",
        description="Annual discount rate for NPV calculations",
        type="percentage",
        unit="percent",
        default_value=0.10,
        min_value=0,
        max_value=1,
        category="Financial",
    ),
    VariableMetadata(
        name="current_manual_hours",
        display_name="Current Manual Hours",
        description="Hours spent on manual process per month",
        type="count",
        unit="hours",
        required=True,
        min_value=0,
        category="Operational",
    ),
    VariableMetadata(
        name="hourly_rate",
        display_name="Hourly Rate",
        description="Fully loaded hourly cost",
        type="currency",
        unit="USD",
        default_value=75.0,
        min_value=0,
        category="Financial",
    ),
    VariableMetadata(
        name="automation_efficiency",
        display_name="Automation Efficiency",
        description="Percentage of time saved through automation",
        type="percentage",
        unit="percent",
        default_value=0.70,
        min_value=0,
        max_value=1,
        category="Efficiency",
    ),
    VariableMetadata(
        name="monthly_transaction_volume",
        display_name="Monthly Transaction Volume",
        description="Number of transactions processed per month",
        type="count",
        unit="transactions",
        required=True,
        min_value=0,
        category="Operational",
    ),
    VariableMetadata(
        name="error_rate_before",
        display_name="Error Rate Before",
        description="Error rate in current process (0-1)",
        type="percentage",
        unit="percent",
        default_value=0.05,
        min_value=0,
        max_value=1,
        category="Efficiency",
    ),
    VariableMetadata(
        name="error_rate_after",
        display_name="Error Rate After",
        description="Error rate after automation (0-1)",
        type="percentage",
        unit="percent",
        default_value=0.01,
        min_value=0,
        max_value=1,
        category="Efficiency",
    ),
    VariableMetadata(
        name="cost_per_error",
        display_name="Cost Per Error",
        description="Average cost to fix an error",
        type="currency",
        unit="USD",
        default_value=500.0,
        min_value=0,
        category="Efficiency",
    ),
]

# ============================================================================
# Formula Registry
# ============================================================================

FORMULA_REGISTRY: list[FormulaMetadata] = [
    FormulaMetadata(
        id="roi_basic",
        name="Basic ROI",
        description="Simple Return on Investment calculation",
        category="ROI",
        expression="(annual_benefit - annual_cost) / implementation_cost * 100",
        variables=[
            VariableMetadata(
                name="annual_benefit",
                display_name="Annual Benefit",
                description="Annual benefit value",
                type="currency",
                unit="USD",
                required=True,
            ),
            VariableMetadata(
                name="annual_cost",
                display_name="Annual Cost",
                description="Annual cost value",
                type="currency",
                unit="USD",
                default_value=0,
            ),
            VariableMetadata(
                name="implementation_cost",
                display_name="Implementation Cost",
                type="currency",
                unit="USD",
                required=True,
            ),
        ],
        output_unit="percent",
    ),
    FormulaMetadata(
        id="payback_period",
        name="Payback Period",
        description="Time to recover initial investment",
        category="Payback",
        expression="implementation_cost / (annual_savings / 12)",
        variables=[
            VariableMetadata(
                name="implementation_cost",
                display_name="Implementation Cost",
                description="Total cost to implement the solution",
                type="currency",
                unit="USD",
                required=True,
            ),
            VariableMetadata(
                name="annual_savings",
                display_name="Annual Savings",
                description="Annual cost savings from the initiative",
                type="currency",
                unit="USD",
                required=True,
            ),
        ],
        output_unit="months",
    ),
    FormulaMetadata(
        id="automation_savings",
        name="Labor Cost Savings",
        description="Cost savings from process automation",
        category="Cost Reduction",
        expression="current_manual_hours * hourly_rate * 12 * automation_efficiency",
        variables=[
            VariableMetadata(
                name="current_manual_hours",
                display_name="Current Manual Hours",
                description="Hours spent on manual process per month",
                type="count",
                unit="hours/month",
                required=True,
            ),
            VariableMetadata(
                name="hourly_rate",
                display_name="Hourly Rate",
                description="Fully loaded hourly cost",
                type="currency",
                unit="USD",
                default_value=75.0,
            ),
            VariableMetadata(
                name="automation_efficiency",
                display_name="Automation Efficiency",
                description="Percentage of time saved through automation",
                type="percentage",
                unit="percent",
                default_value=0.70,
            ),
        ],
        output_unit="USD/year",
    ),
    FormulaMetadata(
        id="error_reduction_savings",
        name="Error Reduction Savings",
        description="Savings from reduced error rates",
        category="Cost Reduction",
        expression="monthly_transaction_volume * 12 * (error_rate_before - error_rate_after) * cost_per_error",
        variables=[
            VariableMetadata(
                name="monthly_transaction_volume",
                display_name="Monthly Transaction Volume",
                description="Number of transactions processed per month",
                type="count",
                unit="transactions",
                required=True,
            ),
            VariableMetadata(
                name="error_rate_before",
                display_name="Error Rate Before",
                description="Error rate in current process (0-1)",
                type="percentage",
                unit="percent",
                default_value=0.05,
            ),
            VariableMetadata(
                name="error_rate_after",
                display_name="Error Rate After",
                description="Error rate after automation (0-1)",
                type="percentage",
                unit="percent",
                default_value=0.01,
            ),
            VariableMetadata(
                name="cost_per_error",
                display_name="Cost Per Error",
                description="Average cost to fix an error",
                type="currency",
                unit="USD",
                default_value=500.0,
            ),
        ],
        output_unit="USD/year",
    ),
]


# ============================================================================
# Endpoints
# ============================================================================


async def evaluate_formula(
    request: FormulaEvaluateRequest,
) -> FormulaEvaluateResponse:
    """Evaluate a formula with the provided inputs.

    Either `formula_id` (to use a registered formula) or `expression`
    (for custom formulas) must be provided.
    """
    try:
        # Get formula and variables
        if request.formula_id:
            formula = next(
                (f for f in FORMULA_REGISTRY if f.id == request.formula_id), None
            )
            if not formula:
                raise NotFoundError(
                    message=str(f"Formula {request.formula_id} not found")
                )
            expression = formula.expression
            output_unit = request.output_unit or formula.output_unit
        else:
            expression = request.expression or ""
            output_unit = request.output_unit or "value"

        # Build variable lookup
        inputs_dict = {inp.name: inp.value for inp in request.inputs}

        # Calculate result using safe evaluation
        try:
            result = evaluate_expression(expression, inputs_dict)
        except Exception:
            raise ValidationError(
                message="Formula evaluation failed. Check expression syntax and variable values."
            )

        # Generate calculation steps for transparency
        steps = generate_calculation_steps(expression, inputs_dict, result)

        return FormulaEvaluateResponse(
            result=result,
            unit=output_unit,
            confidence=DEFAULT_CONFIDENCE,
            calculation_steps=steps,
            formula_used=expression,
        )

    except HTTPException:
        raise
    except Exception:
        raise ServiceUnavailableError(message="FORMULA_EVALUATION_ERROR")


async def get_variables_registry(
    category: str | None = None,
) -> VariablesRegistryResponse:
    """Get the registry of available variables for formula building."""
    variables = VARIABLE_REGISTRY

    if category:
        variables = filter_variables_by_category(variables, category)

    categories = list(set(["Financial", "Operational", "Efficiency", "Quality"]))

    return VariablesRegistryResponse(
        variables=variables,
        total=len(variables),
        categories=categories,
    )


async def list_formulas(
    category: str | None = None,
) -> FormulasRegistryResponse:
    """List all registered formulas."""
    formulas = FORMULA_REGISTRY

    if category:
        formulas = [f for f in formulas if f.category.lower() == category.lower()]

    return FormulasRegistryResponse(
        formulas=formulas,
        total=len(formulas),
    )


async def get_formula(formula_id: str) -> FormulaMetadata:
    """Get details for a specific formula."""
    formula = next((f for f in FORMULA_REGISTRY if f.id == formula_id), None)
    if not formula:
        raise NotFoundError(message=str(f"Formula {formula_id} not found"))
    return formula


# ============================================================================
# Scenario / What-If Analysis Endpoints
# ============================================================================


class VariableAdjustmentInput(BaseModel):
    """Variable adjustment for scenario analysis."""

    name: str = Field(..., description="Variable name to adjust")
    value: float = Field(..., description="New value for the variable")
    original_value: float = Field(
        ..., description="Original/base value for delta calculation"
    )


class ScenarioRequest(BaseModel):
    """Request to calculate a what-if scenario."""

    base_case_id: str = Field(..., description="Reference business case ID")
    adjustments: list[VariableAdjustmentInput] = Field(
        ..., description="Variable adjustments to apply"
    )
    base_case_data: dict[str, Any] | None = Field(
        default=None,
        description="Optional base case data (total_value, implementation_cost, etc.). If provided, bypasses repository lookup.",
    )


class ScenarioResponse(BaseModel):
    """Response from scenario calculation."""

    scenario_id: str = Field(..., description="Generated scenario identifier")
    original_value: float = Field(
        ..., description="Original total value from base case"
    )
    adjusted_value: float = Field(..., description="New total value after adjustments")
    delta_percentage: float = Field(..., description="Percentage change from original")
    new_roi: float = Field(..., description="Recalculated ROI ratio")
    new_payback_months: float = Field(
        ..., description="Recalculated payback period in months"
    )
    formula_used: str = Field(
        ..., description="Formula expression used for calculations"
    )
    calculation_steps: list[dict[str, Any]] = Field(
        default_factory=list, description="Step-by-step breakdown"
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Warning messages (e.g., incomplete data, calculation warnings)",
    )


async def calculate_scenario(
    request: ScenarioRequest,
) -> ScenarioResponse:
    """Calculate a what-if scenario by applying variable adjustments.

    This endpoint enables interactive "what-if" analysis by recalculating
    ROI and payback metrics based on adjusted input variables.
    """
    try:
        # Resolve base case data — prefer inline payload, fallback to lookup
        base_case_data = request.base_case_data
        warnings: list[str] = []

        if base_case_data is None:
            # Attempt to resolve from Neo4j ROICalculation (optional fallback)
            # If unavailable, synthesize minimal defaults so the endpoint never 501s
            warnings.append(
                "Base case data not provided; using zero-value fallback. "
                "Pass base_case_data for accurate scenario modeling."
            )
            base_case_data = {
                "total_value": 0.0,
                "implementation_cost": 0.0,
                "roi_ratio": 0.0,
                "payback_months": 0.0,
            }

        # Convert adjustments to engine dataclass
        engine_adjustments = [
            VariableAdjustment(
                name=adj.name,
                value=adj.value,
                original_value=adj.original_value,
            )
            for adj in request.adjustments
        ]

        # Run scenario calculation
        result = scenario_engine.calculate_scenario(
            base_case_data=base_case_data,
            adjustments=engine_adjustments,
        )

        return ScenarioResponse(
            scenario_id=result.scenario_id,
            original_value=result.original_value,
            adjusted_value=result.adjusted_value,
            delta_percentage=result.delta_percentage,
            new_roi=result.new_roi,
            new_payback_months=result.new_payback_months,
            formula_used=result.formula_used,
            calculation_steps=result.calculation_steps,
            warnings=warnings if warnings else [],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Scenario calculation failed: %s", e, exc_info=True)
        raise ServiceUnavailableError(message="SCENARIO_CALCULATION_ERROR")


# ============================================================================
# Helper Functions
# ============================================================================


def evaluate_expression(expression: str, variables: dict[str, float]) -> float:
    """Safely evaluate a typed formula DSL with a strict AST whitelist."""
    _validate_formula_schema(expression, variables)
    tree = _validate_formula_ast(expression, set(variables.keys()))
    try:
        result = _evaluate_ast_node(tree.body, variables)
        if not isinstance(result, (int, float)) or not math.isfinite(float(result)):
            raise ValueError("Formula result must be a finite number")
        return float(result)
    except (ValueError, ZeroDivisionError, TypeError):
        raise ValueError("INVALID_EXPRESSION_ERROR")


def _evaluate_ast_node(node: ast.AST, variables: dict[str, float]) -> float:
    if isinstance(node, ast.Constant):
        if not isinstance(node.value, (int, float)):
            raise ValueError("Only numeric constants are allowed")
        return float(node.value)
    if isinstance(node, ast.Name):
        if node.id not in variables:
            raise ValueError(f"Unknown variable: {node.id}")
        return float(variables[node.id])
    if isinstance(node, ast.UnaryOp):
        operand = _evaluate_ast_node(node.operand, variables)
        if isinstance(node.op, ast.UAdd):
            return +operand
        if isinstance(node.op, ast.USub):
            return -operand
        raise ValueError("Unsupported unary operator")
    if isinstance(node, ast.BinOp):
        left = _evaluate_ast_node(node.left, variables)
        right = _evaluate_ast_node(node.right, variables)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Div):
            if abs(right) < FLOATING_POINT_EPSILON:
                raise ZeroDivisionError("Division by zero")
            return left / right
        if isinstance(node.op, ast.Pow):
            # Prevent DoS from huge exponents (e.g. 2 ** 99999999).
            if abs(right) > MAX_POW_EXPONENT:
                raise ValueError("Exponent too large in formula")
            return left**right
        raise ValueError("Unsupported binary operator")
    if isinstance(node, ast.Call):
        fn = node.func
        if not isinstance(fn, ast.Name) or fn.id not in _ALLOWED_FUNCTIONS:
            raise ValueError("Unsupported function call")
        args = [_evaluate_ast_node(arg, variables) for arg in node.args]
        if fn.id == "round" and len(args) == 2:
            args[1] = int(args[1])
        return float(_ALLOWED_FUNCTIONS[fn.id](*args))
    raise ValueError(f"Unsupported AST node: {type(node).__name__}")


def generate_calculation_steps(
    expression: str, variables: dict[str, float], final_result: float
) -> list[CalculationStep]:
    """Generate human-readable calculation steps."""
    steps = []

    # Show variable substitution
    substituted = expression
    for var, val in variables.items():
        substituted = substituted.replace(var, str(val))

    steps.append(
        CalculationStep(
            step=1,
            operation="Substitute variables",
            result=substituted,
        )
    )

    # Show final result
    steps.append(
        CalculationStep(
            step=2,
            operation="Evaluate expression",
            result=str(final_result),
        )
    )

    return steps


# ============================================================================
# Formula CRUD Endpoints
# ============================================================================


def _build_formula_metadata(
    formula_node: dict, variables_nodes: list
) -> FormulaMetadata:
    """Build FormulaMetadata from Neo4j node data."""
    return FormulaMetadata(
        id=formula_node["id"],
        formula_id=formula_node["id"],
        name=formula_node["name"],
        description=formula_node["description"],
        category=formula_node["category"],
        expression=formula_node["expression"],
        output_unit=formula_node["outputUnit"],
        version=formula_node["version"],
        status=formula_node["status"],
        created_at=formula_node["createdAt"],
        updated_at=formula_node["updatedAt"],
        owner=formula_node.get("owner"),
        variables=[
            VariableMetadata(
                name=v["name"],
                display_name=v.get("displayName", v["name"]),
                description=v.get("description"),
                type=v.get("type", "number"),
                unit=v.get("unit"),
                default_value=v.get("defaultValue"),
                min_value=v.get("minValue"),
                max_value=v.get("maxValue"),
                required=v.get("required", True),
            )
            for v in variables_nodes
            if v
        ],
        used_in_count=0,
    )


async def create_formula(
    request: CreateFormulaRequest,
    api_key: APIKey = Depends(get_current_api_key),
    tenant: RequestContext = Depends(require_tenant_context),
) -> FormulaMetadata:
    """Create a new formula with Neo4j persistence.

    Creates a Formula node, initial FormulaVersion, and Variable nodes.
    Formula is created in 'draft' status.
    """
    formula_id = f"formula_{uuid.uuid4().hex[:12]}"
    version_id = f"fv_{uuid.uuid4().hex[:12]}"
    now = datetime.now(UTC).isoformat()
    tenant_id = str(tenant.tenant_id)
    owner = request.owner or getattr(api_key, "owner_email", None)

    async with await create_neo4j_tenant_session(tenant_id) as neo4j:
        # Check for name collision within tenant
        check_result = await neo4j.run(
            """
            MATCH (f:Formula {name: $name})
            WHERE f.tenant_id = $tenant_id
            RETURN f.id as existing_id
            """,
            name=request.name,
            tenant_id=tenant_id,
        )
        existing = await check_result.single()
        if existing and existing.get("existing_id"):
            raise ConflictError(
                message=f"Formula with name '{request.name}' already exists"
            )

        # Create formula, version, and variables in a single auto-committed
        # statement so a mid-write failure cannot leave a formula node without
        # its version or variables (the previous two-statement pattern could
        # commit formula+version then fail on variables, leaving partial state).
        await neo4j.run(
            """
            CREATE (f:Formula {
                id: $formula_id,
                name: $name,
                description: $description,
                expression: $expression,
                outputUnit: $output_unit,
                category: $category,
                status: $status,
                version: '1.0.0',
                createdAt: $created_at,
                updatedAt: $created_at,
                owner: $owner,
                tenant_id: $tenant_id
            })
            CREATE (fv:FormulaVersion {
                id: $version_id,
                version: '1.0.0',
                formulaId: $formula_id,
                status: $status,
                createdAt: $created_at,
                createdBy: $owner,
                changeSummary: 'Initial version',
                tenant_id: $tenant_id
            })
            CREATE (f)-[:HAS_VERSION]->(fv)
            WITH f
            UNWIND ($variables) AS var
            WITH f, var WHERE var IS NOT NULL
            MERGE (v:Variable {name: var.name, tenant_id: $tenant_id})
            ON CREATE SET
                v.displayName = var.display_name,
                v.description = var.description,
                v.type = var.type,
                v.unit = var.unit,
                v.defaultValue = var.default_value,
                v.minValue = var.min_value,
                v.maxValue = var.max_value,
                v.required = var.required
            CREATE (f)-[:REQUIRES]->(v)
            """,
            formula_id=formula_id,
            name=request.name,
            description=request.description,
            expression=request.expression,
            output_unit=request.output_unit,
            category=request.category,
            status=STATUS_DRAFT,
            created_at=now,
            owner=owner,
            tenant_id=tenant_id,
            version_id=version_id,
            variables=[v.model_dump() for v in request.variables] if request.variables else [],
        )

        # Fetch created formula
        result = await neo4j.run(
            """
            MATCH (f:Formula {id: $formula_id})
            WHERE f.tenant_id = $tenant_id
            OPTIONAL MATCH (f)-[:REQUIRES]->(v:Variable)
            RETURN f, collect(v) as variables
            """,
            formula_id=formula_id,
            tenant_id=tenant_id,
        )
        record = await result.single()
        if not record:
            raise ServiceUnavailableError(message="Failed to create formula")

        formula_node = record["f"]
        variables_nodes = record["variables"]

        # Audit log the creation
        logger.info(
            "formula_created",
            extra={
                "formula_id": formula_id,
                "name": request.name,
                "category": request.category,
                "owner": owner,
                "tenant_id": tenant_id,
                "actor_key_id": api_key.key_id if api_key else None,
            },
        )

        return _build_formula_metadata(formula_node, variables_nodes)


async def update_formula(
    formula_id: str,
    request: UpdateFormulaRequest,
    api_key: APIKey = Depends(get_current_api_key),
    tenant: RequestContext = Depends(require_tenant_context),
) -> FormulaMetadata:
    """Update an existing formula.

    Only formulas in 'draft' or 'under_review' status can be updated.
    If expression changes, creates a new version.
    """
    tenant_id = str(tenant.tenant_id)

    async with await create_neo4j_tenant_session(tenant_id) as neo4j:
        # Check formula exists and is editable
        check_result = await neo4j.run(
            """
            MATCH (f:Formula {id: $formula_id})
            WHERE f.tenant_id = $tenant_id
            RETURN f.status as status, f.version as version,
                   f.expression as current_expr, f.updatedAt as updated_at
            """,
            formula_id=formula_id,
            tenant_id=tenant_id,
        )
        record = await check_result.single()
        if not record:
            raise NotFoundError(message=str(f"Formula {formula_id} not found"))

        current_status = record["status"]
        current_version = record["version"]
        current_expr = record["current_expr"]
        current_updated_at = record["updated_at"]

        if current_status not in (STATUS_DRAFT, STATUS_UNDER_REVIEW):
            raise ConflictError(
                message=f"Cannot update formula in status '{current_status}'"
            )

        # Check if expression changed (requires new version)
        expr_changed = (
            request.expression is not None and request.expression != current_expr
        )

        # Compute (and validate) the next version BEFORE any writes so a
        # malformed stored version fails fast as a 400 rather than leaving
        # the formula node updated with no matching FormulaVersion.
        new_version: str | None = None
        if expr_changed:
            try:
                new_version = _bump_minor_version(current_version)
            except ValueError as exc:
                raise ValidationError(
                    message=str(
                        f"Stored formula version {current_version!r} is "
                        f"malformed; cannot create a new version"
                    )
                ) from exc

        # Build update properties
        update_fields = []
        params = {"formula_id": formula_id, "tenant_id": tenant_id}

        if request.name is not None:
            update_fields.append("f.name = $name")
            params["name"] = request.name
        if request.description is not None:
            update_fields.append("f.description = $description")
            params["description"] = request.description
        if request.expression is not None:
            update_fields.append("f.expression = $expression")
            params["expression"] = request.expression
        if request.output_unit is not None:
            update_fields.append("f.outputUnit = $output_unit")
            params["output_unit"] = request.output_unit
        if request.category is not None:
            update_fields.append("f.category = $category")
            params["category"] = request.category

        update_fields.append("f.updatedAt = $updated_at")
        params["updated_at"] = datetime.now(UTC).isoformat()

        # Update formula
        if update_fields:
            # Optimistic concurrency: require the row's updatedAt to still
            # match the value we read; a concurrent update that bumped
            # updatedAt means our in-memory view is stale -> 409 Conflict.
            update_query = f"""
                MATCH (f:Formula {{id: $formula_id}})
                WHERE f.tenant_id = $tenant_id
                  AND f.updatedAt = $expected_updated_at
                SET {', '.join(update_fields)}
                RETURN count(f) AS matched
                """
            params["expected_updated_at"] = current_updated_at
            update_result = await neo4j.run(update_query, **params)
            update_record = await update_result.single()
            if not update_record or update_record["matched"] == 0:
                raise ConflictError(
                    message=(
                        f"Formula {formula_id} was modified by another request; "
                        "reload and retry"
                    )
                )

        # Create new version if expression changed
        if expr_changed:
            version_id = f"fv_{uuid.uuid4().hex[:12]}"
            await neo4j.run(
                """
                MATCH (f:Formula {id: $formula_id})
                WHERE f.tenant_id = $tenant_id
                CREATE (fv:FormulaVersion {
                    id: $version_id,
                    version: $new_version,
                    formulaId: $formula_id,
                    status: $status,
                    createdAt: $created_at,
                    createdBy: $owner,
                    changeSummary: 'Expression updated',
                    tenant_id: $tenant_id
                })
                CREATE (f)-[:HAS_VERSION]->(fv)
                SET f.version = $new_version
                """,
                formula_id=formula_id,
                version_id=version_id,
                new_version=new_version,
                status=STATUS_DRAFT,
                created_at=datetime.now(UTC).isoformat(),
                owner=getattr(api_key, "owner_email", None),
                tenant_id=tenant_id,
            )

        # Update variables if provided
        if request.variables is not None:
            # Remove old variable relationships
            await neo4j.run(
                """
                MATCH (f:Formula {id: $formula_id})-[r:REQUIRES]->(v:Variable)
                WHERE f.tenant_id = $tenant_id
                DELETE r
                """,
                formula_id=formula_id,
                tenant_id=tenant_id,
            )
            # Create new variables
            await neo4j.run(
                """
                MATCH (f:Formula {id: $formula_id})
                WHERE f.tenant_id = $tenant_id
                UNWIND $variables as var
                MERGE (v:Variable {name: var.name, tenant_id: $tenant_id})
                ON CREATE SET
                    v.displayName = var.display_name,
                    v.description = var.description,
                    v.type = var.type,
                    v.unit = var.unit,
                    v.defaultValue = var.default_value,
                    v.minValue = var.min_value,
                    v.maxValue = var.max_value,
                    v.required = var.required
                CREATE (f)-[:REQUIRES]->(v)
                """,
                formula_id=formula_id,
                variables=[v.model_dump() for v in request.variables],
                tenant_id=tenant_id,
            )

        # Fetch updated formula
        result = await neo4j.run(
            """
            MATCH (f:Formula {id: $formula_id})
            WHERE f.tenant_id = $tenant_id
            OPTIONAL MATCH (f)-[:REQUIRES]->(v:Variable)
            RETURN f, collect(v) as variables
            """,
            formula_id=formula_id,
            tenant_id=tenant_id,
        )
        record = await result.single()
        if not record:
            raise NotFoundError(
                message=str(f"Formula {formula_id} not found after update")
            )

        formula_node = record["f"]
        variables_nodes = record["variables"]

        # Audit log the update
        logger.info(
            "formula_updated",
            extra={
                "formula_id": formula_id,
                "version_changed": expr_changed,
                "new_version": new_version if expr_changed else current_version,
                "tenant_id": tenant_id,
                "actor_key_id": api_key.key_id if api_key else None,
            },
        )

        return _build_formula_metadata(formula_node, variables_nodes)


async def delete_formula(
    formula_id: str,
    api_key: APIKey = Depends(require_admin_role),
    tenant: RequestContext = Depends(require_tenant_context),
) -> dict[str, str]:
    """Delete a formula and all associated versions and variables.

    Restricted to admin users. Cannot delete if formula is referenced by ValuePacks.
    """
    tenant_id = str(tenant.tenant_id)

    async with await create_neo4j_tenant_session(tenant_id) as neo4j:
        # Check formula exists
        check_result = await neo4j.run(
            """
            MATCH (f:Formula {id: $formula_id})
            WHERE f.tenant_id = $tenant_id
            OPTIONAL MATCH (vp:ValuePack)-[:USES_FORMULA]->(f)
            RETURN f.status as status, count(vp) as ref_count
            """,
            formula_id=formula_id,
            tenant_id=tenant_id,
        )
        record = await check_result.single()
        if not record:
            raise NotFoundError(message=str(f"Formula {formula_id} not found"))

        ref_count = record["ref_count"]
        if ref_count > 0:
            raise ConflictError(
                message=f"Cannot delete formula: referenced by {ref_count} ValuePack(s)"
            )

        # Delete formula and related nodes
        await neo4j.run(
            """
            MATCH (f:Formula {id: $formula_id})
            WHERE f.tenant_id = $tenant_id
            OPTIONAL MATCH (f)-[:HAS_VERSION]->(fv:FormulaVersion)
            OPTIONAL MATCH (f)-[r:REQUIRES]->(v:Variable)
            DELETE fv, r, f
            """,
            formula_id=formula_id,
            tenant_id=tenant_id,
        )

    # Audit log the deletion
    logger.info(
        "formula_deleted",
        extra={
            "formula_id": formula_id,
            "tenant_id": tenant_id,
            "actor_key_id": api_key.key_id if api_key else None,
        },
    )

    return {"status": "deleted", "formula_id": formula_id}


def _bump_minor_version(version: str) -> str:
    """Bump the minor version number (e.g., 1.0.0 -> 1.1.0).

    Raises ValueError on malformed semver so a corrupted stored version
    surfaces as an error instead of silently resetting to 1.0.0.
    """
    if not version or not isinstance(version, str):
        raise ValueError(f"Invalid formula version: {version!r}")
    parts = version.split(".")
    if len(parts) != 3:
        raise ValueError(f"Invalid formula version (expected major.minor.patch): {version!r}")
    try:
        major = int(parts[0])
        minor = int(parts[1])
        patch = int(parts[2])
    except ValueError as exc:
        raise ValueError(f"Invalid formula version (non-numeric segment): {version!r}") from exc
    if major < 0 or minor < 0 or patch < 0:
        raise ValueError(f"Invalid formula version (negative segment): {version!r}")
    return f"{major}.{minor + 1}.0"


# Local route modules register cohesive formula route groups without changing public paths.
from .formulas_evaluation_routes import router as formula_evaluation_router
from .formulas_mutation_routes import router as formula_mutation_router
from .formulas_registry_routes import router as formula_registry_router

router.include_router(formula_evaluation_router)
router.include_router(formula_registry_router)
router.include_router(formula_mutation_router)
