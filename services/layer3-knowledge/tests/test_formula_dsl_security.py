from __future__ import annotations

import pytest

from src.api.routes.formulas import evaluate_expression


def test_formula_dsl_allows_whitelisted_arithmetic_and_functions() -> None:
    result = evaluate_expression(
        "round(max((revenue - cost) / users, 0), 2)",
        {"revenue": 1000.0, "cost": 250.0, "users": 8.0},
    )
    assert result == 93.75


@pytest.mark.parametrize(
    "expression",
    [
        "__import__('os').system('id')",
        "exec('print(1)')",
        "eval('1+1')",
        "open('/etc/passwd').read()",
        "(__import__)",
        "revenue.__class__",
        "globals()",
        "(x for x in [1,2,3])",
        "[x for x in [1,2,3]]",
    ],
)
def test_formula_dsl_rejects_injection_and_escape_attempts(expression: str) -> None:
    with pytest.raises(ValueError, match="INVALID_EXPRESSION_ERROR|invalid|Forbidden|Unknown|Function"):
        evaluate_expression(expression, {"revenue": 100.0})


def test_formula_dsl_rejects_unknown_variables() -> None:
    with pytest.raises(ValueError, match="INVALID_EXPRESSION_ERROR"):
        evaluate_expression("revenue + secret_metric", {"revenue": 100.0})
