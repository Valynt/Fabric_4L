from __future__ import annotations

"""Security regressions for the ROI formula evaluator.

The evaluator intentionally supports a small arithmetic expression language. These
checks document the expected fail-closed behavior for common Python escape hatches
so future refactors do not accidentally expand formula execution into code
execution.
"""


import pytest

from value_fabric.layer3.agents.roi_calculation import ROICalculationAgent


@pytest.fixture
def agent() -> ROICalculationAgent:
    return ROICalculationAgent(driver=None)


def test_safe_eval_allows_arithmetic_and_approved_functions(agent: ROICalculationAgent) -> None:
    result = agent._safe_eval("round(max(revenue - cost, 0) / cost, 2)", {"revenue": 125, "cost": 100})

    assert result == 0.25


@pytest.mark.parametrize(
    "expression",
    [
        "__import__('os').system('id')",
        "open('/etc/passwd').read()",
        "(1).__class__",
        "lambda x: x",
        "[x for x in range(3)]",
        "globals()",
    ],
)
def test_safe_eval_rejects_code_execution_escape_hatches(agent: ROICalculationAgent, expression: str) -> None:
    with pytest.raises((NameError, ValueError)):
        agent._safe_eval(expression, {"revenue": 125, "cost": 100})


def test_safe_eval_rejects_unknown_variables(agent: ROICalculationAgent) -> None:
    with pytest.raises(NameError):
        agent._safe_eval("revenue + unapproved_metric", {"revenue": 125})
