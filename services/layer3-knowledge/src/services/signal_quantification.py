from __future__ import annotations

"""Signal quantification service for Layer 3.

Calculates impact values for pain signals using industry-specific
formulas and prospect data.
"""


import ast
import logging
import operator
import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from neo4j import AsyncDriver
from value_fabric.shared.models.typed_dict import TypedDictModel

from ..db.query_execution import run_validated_query


class SignalQuantificationService__select_formulaResult(TypedDictModel):
    expression: str
    id: str
    name: str
    output_unit: Any
    variables: list[Any]

class SignalQuantificationService__execute_formulaResult(TypedDictModel):
    error: str
    expression: Any | None = None
    success: bool
    value: Any | None = None

try:
    from value_fabric.shared.identity.context import require_context
except ImportError:
    require_context = None

logger = logging.getLogger(__name__)


def _get_tenant_id() -> str:
    """Safely retrieve tenant ID from request context.

    Returns "default" if context is not available (e.g., in tests or background tasks).
    """
    if not require_context:
        return "default"
    try:
        return str(require_context().tenant_id)
    except RuntimeError:
        return "default"


@dataclass
class FormulaVariable:
    """Variable definition for formula execution."""

    name: str
    display_name: str
    value: float | None = None
    data_type: str = "currency"
    default_value: float = 0.0
    valid_range: tuple[float, float] | None = None


@dataclass
class QuantificationResult:
    """Result of signal quantification."""

    success: bool
    impact_value: Decimal | None = None
    impact_unit: str | None = None
    formula_id: str | None = None
    formula_name: str | None = None
    calculation_context: dict[str, Any] | None = None
    errors: list[str] | None = None


class SignalQuantificationService:
    """Service for quantifying pain signal impact.

    Applies industry-specific formulas to calculate financial
    or operational impact of discovered signals.
    """

    # Safe operations for formula evaluation
    SAFE_OPERATORS = {
        "+": operator.add,
        "-": operator.sub,
        "*": operator.mul,
        "/": operator.truediv,
    }

    # AST operator mapping for safe evaluation (P0-2 FIX)
    SAFE_AST_OPERATORS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
        ast.Mod: operator.mod,
        ast.FloorDiv: operator.floordiv,
    }

    SAFE_UNARY_OPERATORS = {
        ast.UAdd: operator.pos,
        ast.USub: operator.neg,
    }

    # Safe functions for formula evaluation
    SAFE_FUNCTIONS = {
        "abs": abs,
        "round": round,
        "min": min,
        "max": max,
        "sum": sum,
    }

    # Default values
    DEFAULT_FORMULA_ID = "ai-f-001"
    DEFAULT_OUTPUT_UNIT = "USD/year"
    DEFAULT_FALLBACK_INDUSTRY = "manufacturing"

    # Multiplier constants for indicator parsing
    THOUSAND_MULTIPLIER = 1_000
    MILLION_MULTIPLIER = 1_000_000
    DEFAULT_FALLBACK_COST = 1_000_000

    # Industry to formula mappings for Operational signals
    OPERATIONAL_FORMULAS = {
        "manufacturing": [
            "ai-f-001",  # AI Model Operationalization ROI (adapted)
        ],
        "automotive": [
            "ai-f-001",
        ],
        "technology": [
            "ai-f-001",
            "ai-f-002",  # LLM Adoption Productivity Value
        ],
    }

    def __init__(self, driver: AsyncDriver):
        """Initialize with Neo4j driver.

        Args:
            driver: Neo4j async driver instance
        """
        self._driver = driver

    async def quantify_signal(
        self,
        tenant_id: str,
        signal_name: str,
        signal_description: str,
        impact_indicators: list[str],
        industry: str | None,
        prospect_data: dict[str, Any],
    ) -> QuantificationResult:
        """Quantify a pain signal's impact.

        Finds appropriate formula, extracts variables from prospect data,
        and calculates impact value.

        Args:
            signal_name: Signal name
            signal_description: Signal description
            impact_indicators: Clues from extraction
            industry: Industry vertical
            prospect_data: Prospect-specific data

        Returns:
            Quantification result with impact value or errors
        """
        try:
            # Step 1: Find appropriate formula
            formula = await self._select_formula(
                tenant_id,
                signal_name,
                signal_description,
                industry,
            )

            if not formula:
                return QuantificationResult(
                    success=False,
                    errors=[
                        f"No suitable formula found for '{signal_name}' "
                        f"in industry '{industry}'"
                    ],
                )

            # Step 2: Extract variables from prospect data
            variables = await self._extract_variables(
                formula,
                impact_indicators,
                prospect_data,
            )

            # Step 3: Validate and fill defaults
            validated_inputs = self._validate_and_fill_variables(variables)
            if validated_inputs.get("_errors"):
                return QuantificationResult(
                    success=False,
                    errors=validated_inputs["_errors"],
                )

            # Step 4: Execute formula
            result = await self._execute_formula(
                formula,
                validated_inputs,
            )

            if not result.get("success"):
                return QuantificationResult(
                    success=False,
                    errors=[result.get("error", "Formula execution failed")],
                )

            # Step 5: Build result
            return QuantificationResult(
                success=True,
                impact_value=Decimal(str(result["value"])),
                impact_unit=formula.get("output_unit", self.DEFAULT_OUTPUT_UNIT),
                formula_id=formula.get("id"),
                formula_name=formula.get("name"),
                calculation_context={
                    "variables_used": list(validated_inputs.keys()),
                    "industry": industry,
                    "indicators_matched": len(impact_indicators),
                },
            )

        except Exception as e:
            logger.error("Signal quantification failed", exc_info=e, extra={"signal_id": signal_id})
            return QuantificationResult(
                success=False,
                errors=["Signal quantification failed due to internal error"],
            )

    async def _select_formula(
        self,
        tenant_id: str,
        signal_name: str,
        signal_description: str,
        industry: str | None,
    ) -> dict[str, Any] | None:
        """Select the most appropriate formula for a signal.

        Args:
            signal_name: Signal name for matching
            signal_description: Signal description
            industry: Industry vertical

        Returns:
            Formula dictionary or None
        """
        # Normalize industry
        industry_key = (industry or "general").lower().strip()

        # Get candidate formulas for this industry
        candidate_ids = self.OPERATIONAL_FORMULAS.get(
            industry_key,
            self.OPERATIONAL_FORMULAS.get(
                self.DEFAULT_FALLBACK_INDUSTRY,
                [self.DEFAULT_FORMULA_ID],
            ),
        )

        # Query graph for formula details
        async with self._driver.session() as session:
            query = """
            MATCH (f:Formula)
            WHERE f.id IN $formula_ids
              AND f.tenant_id = $tenant_id
            RETURN f {
                id: f.id,
                name: f.name,
                expression: f.expression,
                output_unit: f.output_unit,
                variables: f.variables,
                industry: f.industry,
                confidence: f.confidence
            } as formula
            ORDER BY f.confidence DESC
            LIMIT 1
            """

            result = await run_validated_query(session,
                query,
                {
                    "formula_ids": candidate_ids,
                    "tenant_id": tenant_id,
                },
            )
            record = await result.single()

            if record:
                return record["formula"]

        # Fallback: Return a default formula structure if none found in graph
        return SignalQuantificationService__select_formulaResult.model_validate({
            "id": "default-operational",
            "name": "Default Operational Impact",
            "expression": "estimated_annual_cost",
            "output_unit": self.DEFAULT_OUTPUT_UNIT,
            "variables": [
                {
                    "name": "estimated_annual_cost",
                    "default_value": self.DEFAULT_FALLBACK_COST,
                    "data_type": "currency",
                }
            ],
        })


    async def _extract_variables(
        self,
        formula: dict[str, Any],
        impact_indicators: list[str],
        prospect_data: dict[str, Any],
    ) -> list[FormulaVariable]:
        """Extract formula variables from prospect data.

        Args:
            formula: Formula with variable definitions
            impact_indicators: Impact clues from signal
            prospect_data: Prospect data

        Returns:
            List of variables with extracted or default values
        """
        formula_vars = formula.get("variables", [])
        extracted_vars = []

        for var_def in formula_vars:
            var_name = var_def.get("name")
            var = FormulaVariable(
                name=var_name,
                display_name=var_def.get("display_name", var_name),
                data_type=var_def.get("data_type", "currency"),
                default_value=var_def.get("default_value", 0.0),
            )

            # Try to extract from prospect data
            if var_name in prospect_data:
                try:
                    var.value = float(prospect_data[var_name])
                except (ValueError, TypeError):
                    var.value = None

            # Try to extract from impact indicators if not found
            if var.value is None and impact_indicators:
                var.value = self._extract_from_indicators(
                    var_name,
                    impact_indicators,
                )

            extracted_vars.append(var)

        return extracted_vars

    def _extract_from_indicators(
        self,
        variable_name: str,
        impact_indicators: list[str],
    ) -> float | None:
        """Extract a variable value from impact indicators.

        Args:
            variable_name: Name of variable to find
            impact_indicators: List of impact indicator strings

        Returns:
            Extracted value or None
        """
        # Common patterns in indicators
        patterns = {
            "annual_cost": [r"\$([\d.]+)[KM]?.*annual", r"\$([\d.]+)[KM]?.*year"],
            "hourly_cost": [r"\$([\d.]+).*hour"],
            "downtime_hours": [r"(\d+).*hours?.*downtime", r"downtime.*(\d+).*hours"],
            "fte_count": [r"(\d+).*FTE", r"(\d+).*full.time"],
            "capacity_percent": [r"(\d+)%.*capacity", r"capacity.*(\d+)%"],
        }

        var_key = variable_name.lower().replace("_", "")
        regexes = patterns.get(var_key, [])

        for indicator in impact_indicators:
            indicator_lower = indicator.lower()
            for regex in regexes:
                match = re.search(regex, indicator_lower)
                if match:
                    value_str = match.group(1)
                    try:
                        value = float(value_str)
                        # Handle K/M suffixes if present in original
                        if "K" in indicator.upper():
                            value *= self.THOUSAND_MULTIPLIER
                        if "M" in indicator.upper():
                            value *= self.MILLION_MULTIPLIER
                        return value
                    except ValueError:
                        continue

        return None

    def _validate_and_fill_variables(
        self,
        variables: list[FormulaVariable],
    ) -> dict[str, Any]:
        """Validate variables and fill in defaults.

        Args:
            variables: Extracted variables

        Returns:
            Dictionary of variable names to values, with _errors key if issues
        """
        result = {}
        errors = []

        for var in variables:
            if var.value is not None:
                # Validate range if specified
                if var.valid_range:
                    min_val, max_val = var.valid_range
                    if not (min_val <= var.value <= max_val):
                        errors.append(
                            f"Variable '{var.name}' value {var.value} "
                            f"outside range [{min_val}, {max_val}]"
                        )
                        result[var.name] = var.default_value
                    else:
                        result[var.name] = var.value
                else:
                    result[var.name] = var.value
            else:
                # Use default
                result[var.name] = var.default_value

        if errors:
            result["_errors"] = errors

        return result

    async def _execute_formula(
        self,
        formula: dict[str, Any],
        inputs: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a formula safely.

        Args:
            formula: Formula definition
            inputs: Input values

        Returns:
            Execution result
        """
        expression = formula.get("expression", "")

        try:
            # Simple arithmetic expression evaluation
            # For production, use a proper formula engine
            result = self._safe_eval(expression, inputs)

            return SignalQuantificationService__execute_formulaResult.model_validate({
                "success": True,
                "value": result,
                "expression": expression,
            })


        except Exception as e:
            logger.error(f"Formula execution failed: {e}")
            return SignalQuantificationService__execute_formulaResult.model_validate({
                "success": False,
                "error": f"Formula execution failed: {e}",
            })


    def _safe_eval(self, expression: str, context: dict[str, Any]) -> float:
        """Safely evaluate a formula expression using AST parsing.

        P0-2 FIX: Replaced eval() with AST-based evaluation to prevent
        arbitrary code execution via object traversal bypasses.

        Args:
            expression: Formula expression string
            context: Variable values

        Returns:
            Calculated result

        Raises:
            ValueError: If expression contains unsafe constructs
            NameError: If expression references undefined variables
        """
        # Direct variable lookup
        if expression in context:
            return float(context[expression])

        # AST-based safe evaluation (no eval())
        allowed_names = {
            **self.SAFE_FUNCTIONS,
            **{k: v for k, v in context.items() if isinstance(v, (int, float))},
        }
        try:
            tree = ast.parse(expression, mode="eval")
            return float(self._eval_node(tree.body, allowed_names))
        except (ValueError, NameError, TypeError) as e:
            logger.error(f"Expression evaluation failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Expression parse failed: {e}")
            raise ValueError(f"Invalid formula expression: {e}") from e

    def _eval_node(self, node: ast.AST, context: dict[str, Any]) -> Any:
        """Recursively evaluate AST node safely.

        Only allows: constants, variable names, binary ops, unary ops,
        and safe function calls. Rejects attribute access, subscripts,
        imports, lambdas, and all other constructs.

        Args:
            node: AST node to evaluate
            context: Variable context

        Returns:
            Evaluated value

        Raises:
            ValueError: If node type is not allowed
            NameError: If variable not found
        """
        if isinstance(node, ast.Constant):
            if not isinstance(node.value, (int, float)):
                raise ValueError(f"Only numeric constants allowed, got {type(node.value).__name__}")
            return node.value
        elif isinstance(node, ast.Name):
            if node.id in context:
                return context[node.id]
            raise NameError(f"Variable '{node.id}' not defined")
        elif isinstance(node, ast.BinOp):
            op_type = type(node.op)
            if op_type not in self.SAFE_AST_OPERATORS:
                raise ValueError(f"Unsupported operator: {op_type.__name__}")
            left = self._eval_node(node.left, context)
            right = self._eval_node(node.right, context)
            return self.SAFE_AST_OPERATORS[op_type](left, right)
        elif isinstance(node, ast.UnaryOp):
            op_type = type(node.op)
            if op_type not in self.SAFE_UNARY_OPERATORS:
                raise ValueError(f"Unsupported unary operator: {op_type.__name__}")
            operand = self._eval_node(node.operand, context)
            return self.SAFE_UNARY_OPERATORS[op_type](operand)
        elif isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name):
                raise ValueError("Only direct function calls allowed")
            func_name = node.func.id
            if func_name not in self.SAFE_FUNCTIONS:
                raise ValueError(f"Function '{func_name}' not allowed")
            args = [self._eval_node(arg, context) for arg in node.args]
            return self.SAFE_FUNCTIONS[func_name](*args)
        else:
            raise ValueError(f"Unsupported expression type: {type(node).__name__}")

    def get_supported_units(self) -> list[str]:
        """Get list of supported impact units.

        Returns:
            List of valid unit strings
        """
        return [
            "USD/year",
            "USD/month",
            "% capacity",
            "% efficiency",
            "hours/week",
            "FTE",
        ]
