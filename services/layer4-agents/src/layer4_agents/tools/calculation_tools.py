from __future__ import annotations

"""Calculation tools for formulas, ROI, benchmarks, and sensitivity analysis."""


import ast
import operator
import re

import numpy as np

from ..models.tool_schemas import (
    CalculateROIInput,
    CalculateROIOutput,
    CompareBenchmarksInput,
    CompareBenchmarksOutput,
    EvaluateFormulaInput,
    EvaluateFormulaOutput,
    SensitivityAnalysisInput,
    SensitivityAnalysisOutput,
    ToolCategory,
)
from .registry import BaseTool


class SafeExpressionEvaluator:
    """Safe mathematical expression evaluator using AST.

    Only allows basic arithmetic operations - no function calls,
    attribute access, or other potentially dangerous operations.
    """

    # Allowed operators
    OPERATORS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
        ast.Mod: operator.mod,
        ast.FloorDiv: operator.floordiv,
    }

    def __init__(self, variables: dict[str, float]):
        """Initialize with variable values."""
        self.variables = variables

    def evaluate(self, expression: str) -> float:
        """Safely evaluate a mathematical expression.

        Args:
            expression: Mathematical expression string

        Returns:
            Calculated value

        Raises:
            ValueError: If expression is invalid or unsafe
        """
        try:
            tree = ast.parse(expression, mode="eval")
        except SyntaxError as e:
            raise ValueError(f"Invalid expression syntax: {e}")

        return self._eval_node(tree.body)

    def _eval_node(self, node: ast.AST) -> float:
        """Recursively evaluate AST nodes."""
        if isinstance(node, ast.Num):  # Python 3.7 compatibility
            return float(node.n)
        elif isinstance(node, ast.Constant):  # Python 3.8+
            if isinstance(node.value, (int, float)):
                return float(node.value)
            raise ValueError(f"Unsupported constant type: {type(node.value)}")

        elif isinstance(node, ast.Name):
            if node.id in self.variables:
                return float(self.variables[node.id])
            raise ValueError(f"Unknown variable: {node.id}")

        elif isinstance(node, ast.BinOp):
            op_type = type(node.op)
            if op_type not in self.OPERATORS:
                raise ValueError(f"Unsupported binary operator: {op_type.__name__}")

            left = self._eval_node(node.left)
            right = self._eval_node(node.right)
            return self.OPERATORS[op_type](left, right)

        elif isinstance(node, ast.UnaryOp):
            op_type = type(node.op)
            if op_type not in self.OPERATORS:
                raise ValueError(f"Unsupported unary operator: {op_type.__name__}")

            operand = self._eval_node(node.operand)
            return self.OPERATORS[op_type](operand)

        elif isinstance(node, ast.Call):
            raise ValueError("Function calls are not allowed in formulas")

        elif isinstance(node, ast.Attribute):
            raise ValueError("Attribute access is not allowed in formulas")

        else:
            raise ValueError(f"Unsupported AST node type: {type(node).__name__}")


class EvaluateFormulaTool(BaseTool):
    """Evaluate mathematical formulas with variable substitution."""

    name = "evaluate_formula"
    category = ToolCategory.CALCULATION
    description = "Safely evaluates mathematical formulas with variable substitution"
    input_schema = EvaluateFormulaInput
    output_schema = EvaluateFormulaOutput
    timeout_seconds = 10

    # Pattern to find {variable} placeholders
    VARIABLE_PATTERN = re.compile(r"\{([^}]+)\}")
    IDENTIFIER_PATTERN = re.compile(r"\b[a-zA-Z_][a-zA-Z0-9_]*\b")

    async def execute(self, input_data: EvaluateFormulaInput) -> EvaluateFormulaOutput:
        """Execute formula evaluation."""
        try:
            # Extract and substitute variables
            formula = input_data.formula
            variables = input_data.variables

            # Find variables from both {placeholder} format and canonical identifier format (x + y)
            placeholder_names = {name.strip() for name in self.VARIABLE_PATTERN.findall(formula)}
            identifier_names = set(self.IDENTIFIER_PATTERN.findall(formula))
            referenced_vars = placeholder_names | identifier_names

            eval_vars = {name: value for name, value in variables.items() if name in referenced_vars}
            missing = sorted(name for name in referenced_vars if name not in variables)

            if missing:
                return EvaluateFormulaOutput(
                    result=None,
                    substituted_formula=formula,
                    success=False,
                    error=f"Missing variables: {missing}",
                )

            # Substitute values into formula
            substituted = formula
            for var_name, value in eval_vars.items():
                substituted = substituted.replace(f"{{{var_name}}}", str(value))

            # Also substitute numeric variables for evaluation
            eval_formula = formula
            for var_name, value in eval_vars.items():
                eval_formula = eval_formula.replace(f"{{{var_name}}}", str(value))

            # Evaluate the expression
            evaluator = SafeExpressionEvaluator(eval_vars)
            result = evaluator.evaluate(eval_formula)

            return EvaluateFormulaOutput(
                result=result,
                substituted_formula=substituted,
                success=True,
                error=None if not missing else f"Missing variables: {missing}",
            )

        except Exception:
            return EvaluateFormulaOutput(
                result=None, substituted_formula=input_data.formula, success=False, error="FORMULA_EVALUATION_ERROR"
            )


class CalculateROITool(BaseTool):
    """Calculate ROI metrics from investment and returns data."""

    name = "calculate_roi"
    category = ToolCategory.CALCULATION
    description = "Calculates ROI, NPV, IRR, and payback period"
    input_schema = CalculateROIInput
    output_schema = CalculateROIOutput
    timeout_seconds = 15

    async def execute(self, input_data: CalculateROIInput) -> CalculateROIOutput:
        """Calculate ROI metrics."""
        investment = input_data.investment
        returns = input_data.returns
        time_periods = input_data.time_periods
        discount_rate = input_data.discount_rate

        if not returns:
            # Generate equal returns across time periods
            annual_return = investment * 0.3  # Assume 30% annual return as default
            returns = [annual_return] * time_periods

        # Simple ROI
        total_return = sum(returns)
        simple_roi = ((total_return - investment) / investment * 100) if investment > 0 else 0

        # NPV calculation
        npv = -investment
        for t, ret in enumerate(returns, start=1):
            npv += ret / ((1 + discount_rate) ** t)

        # IRR approximation (Newton-Raphson would be better but this is simpler)
        irr = self._approximate_irr(investment, returns)

        # Payback period
        payback = self._calculate_payback(investment, returns)

        return CalculateROIOutput(
            simple_roi_percent=round(simple_roi, 2),
            npv=round(npv, 2),
            irr=round(irr, 4) if irr else None,
            payback_period_months=round(payback, 1) if payback else None,
            total_return=round(total_return, 2),
        )

    def _approximate_irr(self, investment: float, returns: list[float]) -> float | None:
        """Approximate IRR using iterative approach."""
        if investment <= 0:
            return None

        # Try rates from -50% to 100%
        rates = np.linspace(-0.5, 1.0, 150)
        best_rate = None
        best_npv_diff = float("inf")

        for rate in rates:
            npv = -investment
            for t, ret in enumerate(returns, start=1):
                npv += ret / ((1 + rate) ** t)

            if abs(npv) < best_npv_diff:
                best_npv_diff = abs(npv)
                best_rate = rate

        return best_rate if best_rate and best_rate > 0 else None

    def _calculate_payback(self, investment: float, returns: list[float]) -> float | None:
        """Calculate payback period in months."""
        cumulative = 0
        for month, ret in enumerate(returns, start=1):
            cumulative += ret / 12  # Assume returns are annual, convert to monthly
            if cumulative >= investment:
                return month

        # Extrapolate if not paid back within returns period
        if returns:
            annual_return = sum(returns) / len(returns)
            if annual_return > 0:
                remaining = investment - cumulative
                months_needed = remaining / (annual_return / 12)
                return len(returns) * 12 + months_needed

        return None


class CompareBenchmarksTool(BaseTool):
    """Compare metrics against industry benchmarks."""

    name = "compare_benchmarks"
    category = ToolCategory.CALCULATION
    description = "Compares metrics against industry benchmarks"
    input_schema = CompareBenchmarksInput
    output_schema = CompareBenchmarksOutput
    timeout_seconds = 10

    # Simulated benchmark database (in production, this would query a real DB)
    BENCHMARKS = {
        "roi_percent": {
            "technology": {"small": 150, "medium": 180, "large": 220},
            "manufacturing": {"small": 120, "medium": 140, "large": 170},
            "financial_services": {"small": 130, "medium": 160, "large": 200},
        },
        "cost_reduction": {
            "technology": {"small": 15, "medium": 20, "large": 25},
            "manufacturing": {"small": 12, "medium": 18, "large": 22},
            "financial_services": {"small": 10, "medium": 15, "large": 20},
        },
        "time_to_value_months": {
            "technology": {"small": 6, "medium": 9, "large": 12},
            "manufacturing": {"small": 8, "medium": 12, "large": 18},
            "financial_services": {"small": 9, "medium": 14, "large": 20},
        },
    }

    async def execute(self, input_data: CompareBenchmarksInput) -> CompareBenchmarksOutput:
        """Compare against benchmarks."""
        metric = input_data.metric_name
        value = input_data.value
        industry = (input_data.industry or "technology").lower()
        company_size = (input_data.company_size or "medium").lower()

        # Get benchmark data
        benchmarks = self.BENCHMARKS.get(metric, {})
        industry_data = benchmarks.get(industry, {})
        benchmark_avg = industry_data.get(company_size)

        if benchmark_avg is None:
            return CompareBenchmarksOutput(
                percentile=50.0,
                industry_average=None,
                comparison_text=f"No benchmark data available for {metric} in {industry}",
                confidence=0.3,
            )

        # Calculate percentile (simplified)
        # Assume normal distribution around benchmark
        if metric in ["time_to_value_months"]:
            # Lower is better
            percentile = max(0, min(100, 100 - (value / benchmark_avg * 50)))
            comparison = "better than" if value < benchmark_avg else "worse than"
        else:
            # Higher is better
            percentile = max(0, min(100, (value / benchmark_avg * 50)))
            comparison = "better than" if value > benchmark_avg else "worse than"

        text = f"Your {metric} of {value} is {comparison} the {industry} {company_size} company average of {benchmark_avg}"

        return CompareBenchmarksOutput(
            percentile=round(percentile, 1),
            industry_average=benchmark_avg,
            comparison_text=text,
            confidence=0.75,
        )


class SensitivityAnalysisTool(BaseTool):
    """Perform sensitivity analysis on formulas."""

    name = "sensitivity_analysis"
    category = ToolCategory.CALCULATION
    description = "Performs sensitivity analysis on formulas by varying inputs"
    input_schema = SensitivityAnalysisInput
    output_schema = SensitivityAnalysisOutput
    timeout_seconds = 30

    async def execute(self, input_data: SensitivityAnalysisInput) -> SensitivityAnalysisOutput:
        """Execute sensitivity analysis."""
        formula = input_data.base_formula
        base_vars = input_data.base_variables.copy()
        ranges = input_data.variable_ranges

        scenarios = []
        tornado_data = []

        # Calculate base case
        base_tool = EvaluateFormulaTool()
        base_input = EvaluateFormulaInput(formula=formula, variables=base_vars)
        base_result = await base_tool.execute(base_input)
        base_value = base_result.result or 0

        # Generate scenarios
        for var_name, (min_val, max_val, steps) in ranges.items():
            var_scenarios = []
            step_size = (max_val - min_val) / steps

            for i in range(steps + 1):
                val = min_val + (step_size * i)
                test_vars = base_vars.copy()
                test_vars[var_name] = val

                test_input = EvaluateFormulaInput(formula=formula, variables=test_vars)
                test_result = await base_tool.execute(test_input)

                if test_result.success and test_result.result is not None:
                    var_scenarios.append(
                        {
                            "variable": var_name,
                            "value": val,
                            "result": test_result.result,
                            "change_from_base": test_result.result - base_value,
                        }
                    )

            scenarios.extend(var_scenarios)

            # Calculate tornado impact for this variable
            if var_scenarios:
                min_result = min(s["result"] for s in var_scenarios)
                max_result = max(s["result"] for s in var_scenarios)
                impact = max_result - min_result

                tornado_data.append(
                    {
                        "variable": var_name,
                        "impact": impact,
                        "min_result": min_result,
                        "max_result": max_result,
                    }
                )

        # Sort tornado data by impact
        tornado_data.sort(key=lambda x: x["impact"], reverse=True)

        # Find optimal values (simplified - just max result)
        optimal = {}
        if scenarios:
            best_scenario = max(scenarios, key=lambda x: x["result"])
            optimal = {best_scenario["variable"]: best_scenario["value"]}

        return SensitivityAnalysisOutput(
            scenarios=scenarios,
            tornado_data=tornado_data,
            optimal_variables=optimal if optimal else None,
        )
