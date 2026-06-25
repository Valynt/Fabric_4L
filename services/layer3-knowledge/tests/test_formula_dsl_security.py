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
    "expression,expected_error",
    [
        ("__import__('os').system('id')", "Function is not allowed"),
        ("exec('print(1)')", "Function is not allowed"),
        ("eval('1+1')", "Function is not allowed"),
        ("open('/etc/passwd').read()", "Function is not allowed"),
        ("(__import__)", "Forbidden identifier"),
        ("revenue.__class__", "Forbidden expression construct: Attribute"),
        ("globals()", "Function is not allowed"),
        ("(x for x in [1,2,3])", "Forbidden expression construct: GeneratorExp"),
        ("[x for x in [1,2,3]]", "Forbidden expression construct: ListComp"),
        ("abs(revenue) + __import__('os')", "Function is not allowed"),
    ],
)
def test_formula_dsl_rejects_injection_and_escape_attempts(expression: str, expected_error: str) -> None:
    with pytest.raises(ValueError, match=expected_error):
        evaluate_expression(expression, {"revenue": 100.0})


def test_formula_dsl_rejects_unknown_variables() -> None:
    with pytest.raises(ValueError, match="Unknown variable in formula: secret_metric"):
        evaluate_expression("revenue + secret_metric", {"revenue": 100.0})


def test_formula_dsl_rejects_division_by_zero() -> None:
    with pytest.raises(ValueError, match="INVALID_EXPRESSION_ERROR"):
        evaluate_expression("revenue / zero", {"revenue": 100.0, "zero": 0.0})


def test_formula_dsl_rejects_forbidden_identifiers() -> None:
    with pytest.raises(ValueError, match="Forbidden identifier"):
        evaluate_expression("eval + 1", {"eval": 1.0})
