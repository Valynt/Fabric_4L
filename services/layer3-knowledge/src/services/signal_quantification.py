from __future__ import annotations

"""Signal quantification service for Layer 3.

Calculates impact values for pain signals using industry-specific
formulas and prospect data.
"""


import ast
import logging
import math
import operator
import re
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from neo4j import AsyncDriver
from value_fabric.shared.models.typed_dict import TypedDictModel

from ..db.query_execution import run_validated_query

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Formula evaluation safety limits.
#
# These bounds guard user- or configuration-supplied formulas before any
# numeric work happens. The values are intentionally conservative: formulas
# come from untrusted sources and must fail closed rather than consume
# unbounded CPU, blow the stack, or overflow into non-finite numbers.
# ---------------------------------------------------------------------------
MAX_EXPRESSION_LENGTH = 2000  # Maximum characters in a formula expression
MAX_AST_NODES = 100          # Maximum number of AST nodes in a formula
MAX_AST_DEPTH = 20           # Maximum nesting depth of a formula
MAX_POW_EXPONENT = 100       # Maximum absolute integer exponent for `**`
MAX_POW_BASE = 10_000        # Maximum absolute base for `**`

# Stable, user-safe error codes returned through execute_formula. These are
# deliberately terse and do not contain raw parser or arithmetic text; detailed
# diagnostics are emitted only to structured server logs.
ERROR_CODE_TOO_LONG = "FORMULA_TOO_LONG"
ERROR_CODE_TOO_COMPLEX = "FORMULA_TOO_COMPLEX"
ERROR_CODE_TOO_DEEP = "FORMULA_TOO_DEEP"
ERROR_CODE_POW_LIMIT = "FORMULA_POW_LIMIT"
ERROR_CODE_NON_FINITE = "FORMULA_NON_FINITE"
ERROR_CODE_INVALID_EXPRESSION = "FORMULA_INVALID_EXPRESSION"
ERROR_CODE_GENERIC = "FORMULA_EVALUATION_FAILED"

ERROR_MESSAGE_TOO_LONG = "Formula expression exceeds the maximum allowed length."
ERROR_MESSAGE_TOO_COMPLEX = "Formula expression contains too many components."
ERROR_MESSAGE_TOO_DEEP = "Formula expression is nested too deeply."
ERROR_MESSAGE_POW_LIMIT = "Formula exponentiation uses values outside the allowed range."
ERROR_MESSAGE_NON_FINITE = "Formula produced or used a non-finite numeric value."
ERROR_MESSAGE_INVALID_EXPRESSION = "Formula expression is invalid or uses unsupported constructs."
ERROR_MESSAGE_GENERIC = "Formula evaluation failed."


class FormulaEvalError(ValueError):
    """Raised when a formula expression is rejected by safety checks.

    Carries a stable, user-safe ``code`` so callers can program against the
    failure without depending on raw parser or arithmetic exception text. The
    ``message`` is safe to surface to end users; detailed ``detail`` must only
    be emitted to structured server logs, never returned through the public
    formula API.
    """

    def __init__(self, code: str, message: str, *, detail: str = "") -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.detail = detail


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
    error_code: str | None = None



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

    # Formula security limits (module-level constants, aliased for concise use)
    MAX_EXPRESSION_LENGTH = MAX_EXPRESSION_LENGTH
    MAX_AST_NODES = MAX_AST_NODES
    MAX_AST_DEPTH = MAX_AST_DEPTH
    MAX_POW_EXPONENT = MAX_POW_EXPONENT
    MAX_POW_BASE = MAX_POW_BASE

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
            logger.error("Signal quantification failed", exc_info=e, extra={"signal_name": signal_name})
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

            result = await run_validated_query(
                session,
                query,
                {
                    "formula_ids": candidate_ids,
                    "tenant_id": tenant_id,
                },
                tenant_id=tenant_id,
                require_explicit_tenant_id=True,
                query_name="signal_quantification.select_formula",
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

        var_key = variable_name.lower()
        regexes = patterns.get(var_key, [])

        for indicator in impact_indicators:
            for regex in regexes:
                match = re.search(regex, indicator, re.IGNORECASE)
                if match:
                    value_str = match.group(1)
                    try:
                        value = float(value_str)
                        # Check if K/M appears immediately after the number in the original indicator
                        # Find the position where the number ends in the indicator string
                        num_end_pos = match.end(1)
                        if num_end_pos < len(indicator) and indicator[num_end_pos].upper() in ["K", "M"]:
                            suffix = indicator[num_end_pos].upper()
                            if suffix == "K":
                                value *= self.THOUSAND_MULTIPLIER
                            elif suffix == "M":
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
                "error": "",
                "error_code": "",
            })

        except FormulaEvalError as e:
            # Safety-limit rejections carry a stable, user-safe code/message.
            # Raw diagnostics stay in the structured server log only.
            logger.error(
                "Formula evaluation rejected",
                extra={
                    "error_code": e.code,
                    "expression": expression,
                    "detail": e.detail,
                },
            )
            return SignalQuantificationService__execute_formulaResult.model_validate({
                "success": False,
                "expression": expression,
                "error": e.message,
                "error_code": e.code,
            })
        except Exception as e:
            # Never propagate raw parser/arithmetic exception text to callers.
            logger.error(
                "Formula execution failed",
                extra={
                    "error_code": ERROR_CODE_GENERIC,
                    "expression": expression,
                },
                exc_info=e,
            )
            return SignalQuantificationService__execute_formulaResult.model_validate({
                "success": False,
                "expression": expression,
                "error": ERROR_MESSAGE_GENERIC,
                "error_code": ERROR_CODE_GENERIC,
            })


    def _safe_eval(self, expression: str, context: dict[str, Any]) -> float:
        """Safely evaluate a formula expression using AST parsing.

        P0-2 FIX: Replaced eval() with AST-based evaluation to prevent
        arbitrary code execution via object traversal bypasses.

        Hardening limits applied before any numeric work:
          * Expressions longer than ``MAX_EXPRESSION_LENGTH`` are rejected.
          * AST trees exceeding ``MAX_AST_NODES`` or ``MAX_AST_DEPTH`` are
            rejected before evaluation.
          * Exponentiation is bounded to ``MAX_POW_BASE`` ** ``MAX_POW_EXPONENT``.
          * Non-finite inputs and results are rejected with ``math.isfinite``.

        Args:
            expression: Formula expression string
            context: Variable values

        Returns:
            Calculated result

        Raises:
            FormulaEvalError: If expression violates a safety limit or is
                otherwise invalid. Subclass of ``ValueError`` carrying a stable
                ``code``.
            NameError: If expression references undefined variables
        """
        if len(expression) > self.MAX_EXPRESSION_LENGTH:
            raise FormulaEvalError(
                ERROR_CODE_TOO_LONG,
                ERROR_MESSAGE_TOO_LONG,
                detail=(
                    f"length={len(expression)} max={self.MAX_EXPRESSION_LENGTH}"
                ),
            )

        # Direct variable lookup (single, short identifier only)
        if expression in context:
            return self._require_finite(
                context[expression],
                detail=f"variable '{expression}' is not a finite number",
            )

        # AST-based safe evaluation (no eval())
        allowed_names = {
            **self.SAFE_FUNCTIONS,
            **{k: v for k, v in context.items() if isinstance(v, (int, float))},
        }
        try:
            tree = ast.parse(expression, mode="eval")
        except Exception as e:
            logger.error(
                "Formula parse failed",
                extra={"expression": expression, "detail": repr(e)},
            )
            raise FormulaEvalError(
                ERROR_CODE_INVALID_EXPRESSION,
                ERROR_MESSAGE_INVALID_EXPRESSION,
                detail=f"parse error: {e}",
            ) from e

        # Structural safety checks BEFORE evaluation.
        self._validate_tree_limits(tree)

        try:
            raw = self._eval_node(tree.body, allowed_names)
        except FormulaEvalError:
            raise
        except (NameError, TypeError):
            # Undefined variables and type errors are expected user-facing
            # signals. Raw text is never returned through execute_formula.
            logger.error(
                "Expression evaluation rejected",
                extra={"expression": expression},
                exc_info=True,
            )
            raise
        except Exception as e:
            if isinstance(e, OverflowError):
                # Overflow from finite inputs yields a non-finite result.
                logger.error(
                    "Formula evaluation overflow",
                    extra={"expression": expression, "detail": repr(e)},
                )
                raise FormulaEvalError(
                    ERROR_CODE_NON_FINITE,
                    ERROR_MESSAGE_NON_FINITE,
                    detail=f"numeric overflow: {e}",
                ) from e
            logger.error(
                "Expression evaluation failed",
                extra={"expression": expression, "detail": repr(e)},
            )
            raise FormulaEvalError(
                ERROR_CODE_INVALID_EXPRESSION,
                ERROR_MESSAGE_INVALID_EXPRESSION,
                detail=f"evaluation error: {e}",
            ) from e

        return self._require_finite(
            raw,
            detail="formula result is not a finite number",
        )

    def _require_finite(self, value: Any, *, detail: str = "") -> float:
        """Coerce ``value`` to ``float`` and reject non-finite numbers.

        Args:
            value: Value to validate
            detail: Diagnostic detail for the structured log

        Returns:
            Finite float

        Raises:
            FormulaEvalError: If the value is not a finite number
        """
        try:
            fvalue = float(value)
        except (TypeError, ValueError) as e:
            raise FormulaEvalError(
                ERROR_CODE_NON_FINITE,
                ERROR_MESSAGE_NON_FINITE,
                detail=f"{detail} (not numeric: {e!r})",
            ) from e
        if not math.isfinite(fvalue):
            raise FormulaEvalError(
                ERROR_CODE_NON_FINITE,
                ERROR_MESSAGE_NON_FINITE,
                detail=detail or f"value {fvalue!r} is not finite",
            )
        return fvalue

    def _validate_tree_limits(self, tree: ast.AST) -> None:
        """Walk the AST iteratively enforcing node-count and depth limits.

        Uses an explicit stack (not recursion) so deeply nested hostile input
        cannot trigger Python's recursion limit during validation.

        Args:
            tree: Parsed AST to validate

        Raises:
            FormulaEvalError: If the tree exceeds node-count or depth limits
        """
        stack = [(tree, 1)]
        node_count = 0
        while stack:
            node, depth = stack.pop()
            node_count += 1
            if node_count > self.MAX_AST_NODES:
                raise FormulaEvalError(
                    ERROR_CODE_TOO_COMPLEX,
                    ERROR_MESSAGE_TOO_COMPLEX,
                    detail=(
                        f"node_count={node_count} max={self.MAX_AST_NODES}"
                    ),
                )
            if depth > self.MAX_AST_DEPTH:
                raise FormulaEvalError(
                    ERROR_CODE_TOO_DEEP,
                    ERROR_MESSAGE_TOO_DEEP,
                    detail=f"depth={depth} max={self.MAX_AST_DEPTH}",
                )
            for child in ast.iter_child_nodes(node):
                stack.append((child, depth + 1))

    def _eval_pow(self, node: ast.AST, context: Mapping[str, object]) -> float:
        """Evaluate ``base ** exponent`` under explicit power safety bounds.

        Requirement: bounded exponent magnitude and bounded base must be
        satisfied before the operator is invoked, so hostile formulas cannot
        drive exponentiation to overflow or burn CPU. Fractional exponents
        are supported (e.g. ``4 ** 0.5``); a negative base raised to a
        fractional exponent yields a non-finite (complex) result, which is
        rejected by the finite-result check.

        Args:
            node: The Pow binary operator node
            context: Variable context (already finite-checked at this point)

        Returns:
            Finite result

        Raises:
            FormulaEvalError: If exponent/base are out of bounds or non-finite
        """
        base = self._require_finite(
            self._eval_node(node.left, context),
            detail="exponentiation base is not a finite number",
        )
        exponent = self._require_finite(
            self._eval_node(node.right, context),
            detail="exponentiation exponent is not a finite number",
        )

        if abs(exponent) > self.MAX_POW_EXPONENT:
            raise FormulaEvalError(
                ERROR_CODE_POW_LIMIT,
                ERROR_MESSAGE_POW_LIMIT,
                detail=(
                    f"exponent {exponent!r} exceeds max {self.MAX_POW_EXPONENT}"
                ),
            )
        if abs(base) > self.MAX_POW_BASE:
            raise FormulaEvalError(
                ERROR_CODE_POW_LIMIT,
                ERROR_MESSAGE_POW_LIMIT,
                detail=f"base {base!r} exceeds max {self.MAX_POW_BASE}",
            )

        result = base ** exponent
        return self._require_finite(
            result,
            detail="exponentiation result is not a finite number",
        )

    def _eval_node(self, node: ast.AST, context: Mapping[str, object]) -> float:
        """Recursively evaluate AST node safely.

        Only allows: constants, variable names, binary ops, unary ops,
        and safe function calls. Rejects attribute access, subscripts,
        imports, lambdas, and all other constructs. Every produced value is
        finite-checked to keep the evaluation closed under non-finite numbers.

        Args:
            node: AST node to evaluate
            context: Variable context

        Returns:
            Finite numeric result

        Raises:
            FormulaEvalError: If node type is not allowed or a safety limit is hit
            NameError: If variable not found
        """
        if isinstance(node, ast.Constant):
            if not isinstance(node.value, (int, float)):
                raise FormulaEvalError(
                    ERROR_CODE_INVALID_EXPRESSION,
                    ERROR_MESSAGE_INVALID_EXPRESSION,
                    detail=(
                        "only numeric constants allowed, "
                        f"got {type(node.value).__name__}"
                    ),
                )
            return self._require_finite(
                node.value,
                detail="constant is not a finite number",
            )
        elif isinstance(node, ast.Name):
            if node.id in context:
                return self._require_finite(
                    context[node.id],
                    detail=f"variable '{node.id}' is not a finite number",
                )
            raise NameError(f"Variable '{node.id}' not defined")
        elif isinstance(node, ast.BinOp):
            if isinstance(node.op, ast.Pow):
                return self._eval_pow(node, context)
            op_type = type(node.op)
            if op_type not in self.SAFE_AST_OPERATORS:
                raise FormulaEvalError(
                    ERROR_CODE_INVALID_EXPRESSION,
                    ERROR_MESSAGE_INVALID_EXPRESSION,
                    detail=f"Unsupported operator: {op_type.__name__}",
                )
            left = self._eval_node(node.left, context)
            right = self._eval_node(node.right, context)
            result = self.SAFE_AST_OPERATORS[op_type](left, right)
            return self._require_finite(
                result,
                detail=(
                    f"operator {op_type.__name__} produced a "
                    "non-finite result"
                ),
            )
        elif isinstance(node, ast.UnaryOp):
            op_type = type(node.op)
            if op_type not in self.SAFE_UNARY_OPERATORS:
                raise FormulaEvalError(
                    ERROR_CODE_INVALID_EXPRESSION,
                    ERROR_MESSAGE_INVALID_EXPRESSION,
                    detail=f"Unsupported unary operator: {op_type.__name__}",
                )
            operand = self._eval_node(node.operand, context)
            result = self.SAFE_UNARY_OPERATORS[op_type](operand)
            return self._require_finite(
                result,
                detail=(
                    f"unary operator {op_type.__name__} produced a "
                    "non-finite result"
                ),
            )
        elif isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name):
                raise FormulaEvalError(
                    ERROR_CODE_INVALID_EXPRESSION,
                    ERROR_MESSAGE_INVALID_EXPRESSION,
                    detail="Only direct function calls allowed",
                )
            func_name = node.func.id
            if func_name not in self.SAFE_FUNCTIONS:
                raise FormulaEvalError(
                    ERROR_CODE_INVALID_EXPRESSION,
                    ERROR_MESSAGE_INVALID_EXPRESSION,
                    detail=f"Function '{func_name}' not allowed",
                )
            values = [self._eval_node(arg, context) for arg in node.args]
            result = self.SAFE_FUNCTIONS[func_name](*values)
            return self._require_finite(
                result,
                detail=(
                    f"function '{func_name}' produced a non-finite result"
                ),
            )
        else:
            raise FormulaEvalError(
                ERROR_CODE_INVALID_EXPRESSION,
                ERROR_MESSAGE_INVALID_EXPRESSION,
                detail=f"Unsupported expression type: {type(node).__name__}",
            )

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
