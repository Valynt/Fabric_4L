"""Allowed service-local exception for Layer 3 service wrapper.

Owner: layer3-knowledge
Removal/migration target: 2026-09-30
Reason: ROI Calculation Agent.

Implements formula execution, metric substitution, and sensitivity analysis.
"""

import ast
import logging
import operator
import time
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from neo4j import AsyncDriver
from value_fabric.shared.identity.isolation import ScopedQuery, TenantScopedCypher
from value_fabric.shared.models.typed_dict import TypedDictModel

from .base import AgentResult, BaseAgent
from ..db.query_execution import run_validated_query


class ROICalculationAgent__run_sensitivity_analysisResult(TypedDictModel):
    base_inputs: Any | None = None
    error: str
    formula_id: Any | None = None
    most_sensitive_variable: Any | None = None
    variable_analysis: Any | None = None

class ROICalculationAgent__retrieve_formulasResult(TypedDictModel):
    error: str
    formulas: list[Any]
    formulas_found: Any | None = None
    use_case_id: Any | None = None

class ROICalculationAgent__calculate_sensitivityResult(TypedDictModel):
    elasticity_metrics: Any
    variables_analyzed: list[Any]

class ROICalculationAgent__execute_formulaResult(TypedDictModel):
    error: str
    formula: Any
    validation_errors: Any | None = None

logger = logging.getLogger(__name__)


@dataclass
class FormulaNode:
    """Formula stored in graph."""

    formula_id: str
    name: str
    description: str
    formula_expression: str
    variables: list[dict[str, Any]]
    constants: dict[str, float]
    output_metric: str
    applicable_personas: list[str]
    applicable_use_cases: list[str]
    assumptions: list[str]
    validation_rules: list[str]


@dataclass
class ROIResult:
    """Result of ROI calculation."""

    calculation_id: str
    formula_id: str
    inputs: dict[str, Any]
    outputs: dict[str, Any]
    intermediate_values: dict[str, float]
    execution_trace: list[dict[str, Any]]
    confidence_score: float
    sensitivity_analysis: dict[str, Any] | None
    calculation_timestamp: str


class ROICalculationAgent(BaseAgent):
    """Agent for ROI calculation and formula execution.

    Capabilities:
    - formula_execution: Execute stored formulas safely
    - metric_substitution: Substitute actual values for metrics
    - sensitivity_analysis: Analyze variable sensitivity
    - scenario_modeling: Model different scenarios

    Execution engine: deterministic with formula validation
    """

    # Safe operations for formula evaluation
    SAFE_OPERATORS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
    }

    SAFE_FUNCTIONS = {
        "abs": abs,
        "round": round,
        "min": min,
        "max": max,
        "sum": sum,
        "pow": pow,
        "Decimal": Decimal,
    }

    def __init__(self, driver: AsyncDriver | None = None):
        """Initialize ROI calculation agent.

        Args:
            driver: Neo4j async driver for graph operations
        """
        super().__init__("ROICalculationAgent")
        self._driver = driver

    @staticmethod
    def _query_tuple(scoped_query: ScopedQuery) -> tuple[str, dict[str, Any]]:
        """Expose strict scoped-query execution metadata while preserving session.run compatibility."""
        return scoped_query.as_tuple()

    def _require_tenant_id(self, tenant_id: str | None) -> str:
        """Require tenant identifier for all public ROI operations."""
        if tenant_id and str(tenant_id).strip():
            return str(tenant_id)
        raise ValueError("tenant_id is required for tenant-scoped ROI calculations")

    def _builder(self, tenant_id: str | None) -> TenantScopedCypher:
        return TenantScopedCypher(self._require_tenant_id(tenant_id))

    async def execute(self, context: dict[str, Any]) -> AgentResult:
        """Execute ROI calculation.

        Args:
            context: Must contain:
                - operation: 'calculate', 'sensitivity_analysis', 'formula_retrieval'
                - formula_id: ID of formula to execute (for calculate)
                - inputs: Dict of variable values (for calculate)
                - use_case_id: ID to retrieve formulas (for formula_retrieval)

        Returns:
            AgentResult with calculation results
        """
        start_time = time.time()

        try:
            operation = context.get("operation", "calculate")

            if operation == "calculate":
                result = await self._execute_formula(
                    context.get("formula_id"),
                    context.get("inputs", {}),
                    context.get("run_sensitivity", False),
                    context.get("tenant_id"),
                )
            elif operation == "sensitivity_analysis":
                result = await self._run_sensitivity_analysis(
                    context.get("formula_id"),
                    context.get("inputs", {}),
                    context.get("variable_ranges", {}),
                    context.get("tenant_id"),
                )
            elif operation == "formula_retrieval":
                result = await self._retrieve_formulas(
                    context.get("use_case_id"),
                    context.get("tenant_id"),
                )
            else:
                return self._create_result(
                    status="failed",
                    output={},
                    execution_time_ms=int((time.time() - start_time) * 1000),
                    errors=[f"Unknown operation: {operation}"],
                )

            return self._create_result(
                status="success",
                output=result,
                execution_time_ms=int((time.time() - start_time) * 1000),
            )

        except Exception as e:
            logger.error(f"ROI calculation failed: {e}")
            return self._create_result(
                status="failed",
                output={},
                execution_time_ms=int((time.time() - start_time) * 1000),
                errors=[str(e)],
            )

    async def _execute_formula(
        self,
        formula_id: str,
        inputs: dict[str, Any],
        run_sensitivity: bool = False,
        tenant_id: str | None = None,
    ) -> dict[str, Any]:
        """Execute a formula with given inputs.

        Args:
            formula_id: ID of formula to execute
            inputs: Variable values
            run_sensitivity: Whether to run sensitivity analysis
            tenant_id: Tenant ID for data isolation

        Returns:
            Dict with calculation results
        """
        resolved_tenant_id = self._require_tenant_id(tenant_id)
        if not self._driver:
            return ROICalculationAgent__execute_formulaResult.model_validate({"error": "No database driver"})

        # Retrieve formula from graph
        formula = await self._get_formula(formula_id, resolved_tenant_id)
        if not formula:
            return ROICalculationAgent__execute_formulaResult.model_validate({"error": f"Formula {formula_id} not found"})

        # Validate inputs
        validation_errors = self._validate_inputs(formula, inputs)
        if validation_errors:
            return ROICalculationAgent__execute_formulaResult.model_validate({
                "error": "Input validation failed",
                "validation_errors": validation_errors,
            })


        # Prepare execution context
        execution_context = {
            **formula.constants,
            **inputs,
        }

        # Execute formula safely
        try:
            result = self._safe_eval(formula.formula_expression, execution_context)
        except Exception as e:
            return ROICalculationAgent__execute_formulaResult.model_validate({
                "error": f"Formula execution failed: {e}",
                "formula": formula.formula_expression,
            })


        # Build execution trace
        trace = self._build_execution_trace(formula, inputs, execution_context)

        # Run sensitivity analysis if requested
        sensitivity = None
        if run_sensitivity:
            sensitivity = await self._calculate_sensitivity(
                formula, inputs, execution_context
            )

        roi_result = {
            "calculation_id": f"calc-{formula_id}-{int(time.time())}",
            "formula_id": formula_id,
            "formula_name": formula.name,
            "inputs": inputs,
            "outputs": {
                formula.output_metric: result,
                "raw_value": float(result) if isinstance(result, Decimal) else result,
            },
            "intermediate_values": execution_context,
            "execution_trace": trace,
            "confidence_score": 0.95,  # High confidence for deterministic calc
            "sensitivity_analysis": sensitivity,
            "calculation_timestamp": datetime.utcnow().isoformat(),
            "assumptions": formula.assumptions,
        }

        return roi_result

    async def _run_sensitivity_analysis(
        self,
        formula_id: str,
        base_inputs: dict[str, Any],
        variable_ranges: dict[str, list[Any]],
        tenant_id: str | None = None,
    ) -> dict[str, Any]:
        """Run sensitivity analysis on formula variables.

        Args:
            formula_id: ID of formula
            base_inputs: Base input values
            variable_ranges: Ranges for each variable to test
            tenant_id: Tenant ID for data isolation

        Returns:
            Dict with sensitivity analysis results
        """
        resolved_tenant_id = self._require_tenant_id(tenant_id)
        if not self._driver:
            return ROICalculationAgent__run_sensitivity_analysisResult.model_validate({"error": "No database driver"})

        formula = await self._get_formula(formula_id, resolved_tenant_id)
        if not formula:
            return ROICalculationAgent__run_sensitivity_analysisResult.model_validate({"error": f"Formula {formula_id} not found"})

        results = {}

        for variable, values in variable_ranges.items():
            variable_results = []

            for value in values:
                test_inputs = {**base_inputs, variable: value}

                try:
                    execution_context = {**formula.constants, **test_inputs}
                    result = self._safe_eval(
                        formula.formula_expression, execution_context
                    )
                    variable_results.append(
                        {
                            "variable_value": value,
                            "result": float(result)
                            if isinstance(result, Decimal)
                            else result,
                        }
                    )
                except Exception as e:
                    logger.warning(
                        f"Sensitivity test failed for {variable}={value}: {e}"
                    )

            # Calculate sensitivity metrics
            if variable_results:
                results_values = [r["result"] for r in variable_results]
                results[variable] = {
                    "range_tested": (min(values), max(values)),
                    "result_range": (min(results_values), max(results_values)),
                    "sensitivity_ratio": (
                        (max(results_values) - min(results_values))
                        / (max(values) - min(values))
                        if len(values) > 1 and max(values) != min(values)
                        else 0
                    ),
                    "test_points": variable_results,
                }

        return ROICalculationAgent__run_sensitivity_analysisResult.model_validate({
            "formula_id": formula_id,
            "base_inputs": base_inputs,
            "variable_analysis": results,
            "most_sensitive_variable": max(
                results.items(),
                key=lambda x: x[1].get("sensitivity_ratio", 0),
            )[0]
            if results
            else None,
        })


    async def _retrieve_formulas(self, use_case_id: str, tenant_id: str | None = None) -> dict[str, Any]:
        """Retrieve formulas applicable to a use case.

        Retrieves formulas linked to the use case within tenant scope.

        Args:
            use_case_id: Use case ID
            tenant_id: Tenant ID for data isolation

        Returns:
            Dict with formulas
        """
        resolved_tenant_id = self._require_tenant_id(tenant_id)
        if not self._driver:
            return ROICalculationAgent__retrieve_formulasResult.model_validate({"formulas": [], "error": "No database driver"})

        builder = self._builder(resolved_tenant_id)
        query = builder.custom_tenant_query(
            """
            // strict-scoped-query-execution
            // strict-scoped-query-execution
            MATCH (uc:UseCase {id: $use_case_id, tenant_id: $_tenant_id})-[:delivers]->(vd:ValueDriver {tenant_id: $_tenant_id})
            // strict-scoped-query-execution
            OPTIONAL MATCH (vd)-[:measuredBy|calculatedBy]->(f:Formula {tenant_id: $_tenant_id})
            RETURN f.id as formula_id, f.name as name, f.description as description,
                   f.formula_expression as expression, f.variables as variables,
                   f.constants as constants, f.output_metric as output_metric,
                   f.assumptions as assumptions
            """,
            params={"use_case_id": use_case_id},
            operation="roi_calculation.retrieve_formulas",
            labels=("UseCase", "ValueDriver", "Formula"),
        )

        formulas = []

        async with self._driver.session() as session:
            result = await run_validated_query(session, *self._query_tuple(query))
            async for record in result:
                if record["formula_id"]:
                    formulas.append(
                        {
                            "formula_id": record["formula_id"],
                            "name": record["name"],
                            "description": record["description"],
                            "expression": record["expression"],
                            "variables": record["variables"],
                            "constants": record["constants"],
                            "output_metric": record["output_metric"],
                            "assumptions": record["assumptions"],
                        }
                    )

        return ROICalculationAgent__retrieve_formulasResult.model_validate({
            "use_case_id": use_case_id,
            "formulas_found": len(formulas),
            "formulas": formulas,
        })


    async def _get_formula(self, formula_id: str, tenant_id: str | None = None) -> FormulaNode | None:
        """Retrieve formula from graph by ID.

        Args:
            formula_id: Formula ID
            tenant_id: Tenant ID for data isolation

        Returns:
            FormulaNode if found, None otherwise
        """
        resolved_tenant_id = self._require_tenant_id(tenant_id)
        if not self._driver:
            return None

        builder = self._builder(resolved_tenant_id)
        query = builder.custom_tenant_query(
            """
            // strict-scoped-query-execution
            MATCH (f:Formula {id: $formula_id, tenant_id: $_tenant_id})
            RETURN f.id as id, f.name as name, f.description as description,
                   f.formula_expression as expression, f.variables as variables,
                   f.constants as constants, f.output_metric as output_metric,
                   f.applicable_personas as personas, f.applicable_use_cases as use_cases,
                   f.assumptions as assumptions, f.validation_rules as validation_rules
            """,
            params={"formula_id": formula_id},
            operation="roi_calculation.get_formula",
            labels=("Formula",),
        )

        async with self._driver.session() as session:
            result = await run_validated_query(session, *self._query_tuple(query))
            record = await result.single()

            if record:
                return FormulaNode(
                    formula_id=record["id"],
                    name=record["name"],
                    description=record["description"],
                    formula_expression=record["expression"],
                    variables=record["variables"] or [],
                    constants=record["constants"] or {},
                    output_metric=record["output_metric"],
                    applicable_personas=record["personas"] or [],
                    applicable_use_cases=record["use_cases"] or [],
                    assumptions=record["assumptions"] or [],
                    validation_rules=record["validation_rules"] or [],
                )

            return None

    def _validate_inputs(
        self, formula: FormulaNode, inputs: dict[str, Any]
    ) -> list[str]:
        """Validate inputs against formula requirements.

        Args:
            formula: Formula definition
            inputs: Input values

        Returns:
            List of validation error messages
        """
        errors = []

        required_vars = {
            v["name"] for v in formula.variables if v.get("required", True)
        }
        provided_vars = set(inputs.keys())

        missing = required_vars - provided_vars
        if missing:
            errors.append(f"Missing required variables: {missing}")

        # Validate types
        for var in formula.variables:
            var_name = var["name"]
            if var_name in inputs:
                expected_type = var.get("type", "number")
                value = inputs[var_name]

                if expected_type == "number":
                    try:
                        float(value)
                    except (ValueError, TypeError):
                        errors.append(f"Variable {var_name} must be numeric")
                elif expected_type == "integer":
                    try:
                        int(value)
                    except (ValueError, TypeError):
                        errors.append(f"Variable {var_name} must be an integer")

        return errors

    def _safe_eval(self, expression: str, context: dict[str, Any]) -> Any:
        """Safely evaluate a mathematical expression.

        Uses AST parsing to only allow safe operations.

        Args:
            expression: Formula expression string
            context: Variable values

        Returns:
            Calculated result
        """
        tree = ast.parse(expression, mode="eval")

        return self._eval_node(tree.body, context)

    def _eval_node(self, node: ast.AST, context: dict[str, Any]) -> Any:
        """Recursively evaluate AST node.

        Args:
            node: AST node
            context: Variable context

        Returns:
            Evaluated value
        """
        if isinstance(node, ast.Num):  # Python 3.7
            return node.n
        elif isinstance(node, ast.Constant):  # Python 3.8+
            return node.value
        elif isinstance(node, ast.Name):
            if node.id in context:
                return context[node.id]
            elif node.id in self.SAFE_FUNCTIONS:
                return self.SAFE_FUNCTIONS[node.id]
            else:
                raise NameError(f"Variable '{node.id}' not defined")
        elif isinstance(node, ast.BinOp):
            left = self._eval_node(node.left, context)
            right = self._eval_node(node.right, context)
            op_type = type(node.op)

            if op_type in self.SAFE_OPERATORS:
                return self.SAFE_OPERATORS[op_type](left, right)
            else:
                raise ValueError(f"Unsupported binary operator: {op_type}")
        elif isinstance(node, ast.UnaryOp):
            operand = self._eval_node(node.operand, context)
            op_type = type(node.op)

            if op_type in self.SAFE_OPERATORS:
                return self.SAFE_OPERATORS[op_type](operand)
            else:
                raise ValueError(f"Unsupported unary operator: {op_type}")
        elif isinstance(node, ast.Call):
            func = self._eval_node(node.func, context)
            args = [self._eval_node(arg, context) for arg in node.args]

            if func in self.SAFE_FUNCTIONS.values():
                return func(*args)
            else:
                raise ValueError("Unsupported function call")
        else:
            raise ValueError(f"Unsupported expression type: {type(node)}")

    def _build_execution_trace(
        self,
        formula: FormulaNode,
        inputs: dict[str, Any],
        context: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Build execution trace for provenance.

        Args:
            formula: Executed formula
            inputs: Input values
            context: Full execution context

        Returns:
            List of execution steps
        """
        trace = [
            {
                "step": 1,
                "operation": "input_validation",
                "inputs": inputs,
            },
            {
                "step": 2,
                "operation": "constant_substitution",
                "constants_used": formula.constants,
            },
            {
                "step": 3,
                "operation": "formula_execution",
                "expression": formula.formula_expression,
                "full_context": context,
            },
        ]

        return trace

    async def _calculate_sensitivity(
        self,
        formula: FormulaNode,
        base_inputs: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Calculate sensitivity for each variable.

        Args:
            formula: Formula definition
            base_inputs: Base input values
            context: Execution context

        Returns:
            Dict with sensitivity metrics
        """
        sensitivities = {}

        for var in formula.variables:
            var_name = var["name"]
            if var_name not in base_inputs:
                continue

            base_value = float(base_inputs[var_name])

            # Test +/- 10% variation
            test_values = [
                base_value * 0.9,
                base_value * 1.0,
                base_value * 1.1,
            ]

            results = []
            for test_val in test_values:
                test_context = {**context, var_name: test_val}
                try:
                    result = self._safe_eval(formula.formula_expression, test_context)
                    results.append(
                        float(result) if isinstance(result, Decimal) else result
                    )
                except Exception:
                    results.append(None)

            if all(r is not None for r in results):
                delta_input = test_values[2] - test_values[0]
                delta_output = results[2] - results[0]

                sensitivities[var_name] = {
                    "elasticity": (delta_output / results[1])
                    / (delta_input / base_value)
                    if results[1] and base_value
                    else 0,
                    "absolute_sensitivity": delta_output / delta_input
                    if delta_input
                    else 0,
                }

        return ROICalculationAgent__calculate_sensitivityResult.model_validate({
            "variables_analyzed": list(sensitivities.keys()),
            "elasticity_metrics": sensitivities,
        })

