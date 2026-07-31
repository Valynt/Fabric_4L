from __future__ import annotations

import asyncio
import json

import pytest

import layer4_agents.tools.generation_tools as generation_module
from layer4_agents.models.tool_schemas import (
    AssembleDocumentInput,
    CalculateROIInput,
    CompareBenchmarksInput,
    CreateChartInput,
    EvaluateFormulaInput,
    FormatTableInput,
    GenerateSectionInput,
    SensitivityAnalysisInput,
)
from layer4_agents.services.llm_budget_guardrails import LLMBudgetExceededError
from layer4_agents.tools.calculation_tools import (
    CalculateROITool,
    CompareBenchmarksTool,
    EvaluateFormulaTool,
    SafeExpressionEvaluator,
    SensitivityAnalysisTool,
)
from layer4_agents.tools.generation_tools import (
    AssembleDocumentTool,
    CreateChartTool,
    FormatTableTool,
    GenerateSectionTool,
)


@pytest.mark.parametrize(
    ("expression", "variables", "expected"),
    [
        ("2 + 3 * 4", {}, 14),
        ("x ** 2 - -y", {"x": 3, "y": 2}, 11),
        ("7 % 4 + 7 // 4", {}, 4),
        ("8 / 2", {}, 4),
    ],
)
def test_safe_expression_evaluator_arithmetic(expression, variables, expected) -> None:
    assert SafeExpressionEvaluator(variables).evaluate(expression) == expected


@pytest.mark.parametrize(
    ("expression", "message"),
    [
        ("(", "Invalid expression syntax"),
        ("missing + 1", "Unknown variable"),
        ("'text'", "Unsupported constant type"),
        ("abs(1)", "Function calls are not allowed"),
        ("x.real", "Attribute access is not allowed"),
        ("[1]", "Unsupported AST node type"),
        ("not 1", "Unsupported unary operator"),
        ("1 << 2", "Unsupported binary operator"),
    ],
)
def test_safe_expression_evaluator_rejects_unsafe_nodes(expression, message) -> None:
    with pytest.raises(ValueError, match=message):
        SafeExpressionEvaluator({"x": 1}).evaluate(expression)


@pytest.mark.asyncio
async def test_evaluate_formula_supports_placeholders_identifiers_and_errors() -> None:
    tool = EvaluateFormulaTool()
    result = await tool.execute(
        EvaluateFormulaInput(formula="{x} + y", variables={"x": 2, "y": 3, "z": 9})
    )
    assert result.success and result.result == 5 and result.substituted_formula == "2.0 + y"
    missing = await tool.execute(EvaluateFormulaInput(formula="x + y", variables={"x": 1}))
    assert not missing.success and "y" in missing.error
    invalid = await tool.execute(EvaluateFormulaInput(formula="x / 0", variables={"x": 1}))
    assert not invalid.success and invalid.error == "FORMULA_EVALUATION_ERROR"


@pytest.mark.asyncio
async def test_evaluate_formula_propagates_cancellation(monkeypatch) -> None:
    def cancel(_self, _expression):
        raise asyncio.CancelledError

    monkeypatch.setattr(SafeExpressionEvaluator, "evaluate", cancel)
    with pytest.raises(asyncio.CancelledError):
        await EvaluateFormulaTool().execute(EvaluateFormulaInput(formula="x", variables={"x": 1}))


@pytest.mark.asyncio
async def test_roi_defaults_explicit_returns_zero_investment_and_helpers() -> None:
    tool = CalculateROITool()
    defaulted = await tool.execute(CalculateROIInput(investment=1000, returns=[], time_periods=3))
    assert defaulted.total_return == 900 and defaulted.simple_roi_percent == -10
    explicit = await tool.execute(
        CalculateROIInput(investment=1000, returns=[600, 600], time_periods=2, discount_rate=0)
    )
    assert explicit.simple_roi_percent == 20 and explicit.npv == 200
    zero = await tool.execute(CalculateROIInput(investment=0, returns=[100]))
    assert zero.simple_roi_percent == 0 and zero.irr is None
    assert tool._approximate_irr(0, [1]) is None
    assert tool._calculate_payback(100, []) is None
    assert tool._calculate_payback(100, [0, 0]) is None
    assert tool._calculate_payback(100, [1200]) == 1
    assert tool._calculate_payback(1000, [100]) > 12


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("metric", "value", "expected_phrase"),
    [
        ("roi_percent", 200, "better than"),
        ("roi_percent", 100, "worse than"),
        ("time_to_value_months", 5, "better than"),
        ("time_to_value_months", 20, "worse than"),
    ],
)
async def test_benchmark_comparison_direction(metric, value, expected_phrase) -> None:
    result = await CompareBenchmarksTool().execute(
        CompareBenchmarksInput(
            metric_name=metric, value=value, industry="technology", company_size="medium"
        )
    )
    assert expected_phrase in result.comparison_text
    assert 0 <= result.percentile <= 100 and result.industry_average is not None


@pytest.mark.asyncio
async def test_benchmark_missing_data_uses_low_confidence_fallback() -> None:
    result = await CompareBenchmarksTool().execute(
        CompareBenchmarksInput(
            metric_name="unknown", value=1, industry="unknown", company_size="giant"
        )
    )
    assert result.industry_average is None and result.percentile == 50 and result.confidence == 0.3


@pytest.mark.asyncio
async def test_sensitivity_analysis_generates_scenarios_tornado_and_optimum() -> None:
    base = {"price": 10.0, "volume": 2.0}
    result = await SensitivityAnalysisTool().execute(
        SensitivityAnalysisInput(
            base_formula="price * volume",
            base_variables=base,
            variable_ranges={"price": (5, 15, 2), "volume": (1, 3, 2)},
        )
    )
    assert len(result.scenarios) == 6 and len(result.tornado_data) == 2
    assert result.tornado_data[0]["impact"] >= result.tornado_data[1]["impact"]
    assert result.optimal_variables
    assert base == {"price": 10.0, "volume": 2.0}
    empty = await SensitivityAnalysisTool().execute(
        SensitivityAnalysisInput(base_formula="x", base_variables={"x": 1}, variable_ranges={})
    )
    assert empty.scenarios == [] and empty.optimal_variables is None


@pytest.mark.asyncio
async def test_generate_section_success_template_fallback_errors_and_cancel() -> None:
    tool = GenerateSectionTool()
    prompts = []

    async def generate(prompt, max_tokens=0):
        prompts.append((prompt, max_tokens))
        return "Point one\nPoint two\nPoint three\nPoint four"

    tool._call_llm = generate
    result = await tool.execute(
        GenerateSectionInput(
            section_type="unknown",
            context={"company": "Acme"},
            tone="injected tone",
            max_length=100,
        )
    )
    assert result.word_count == 8 and result.key_points == ["Point one", "Point two", "Point three"]
    assert "<<<USER_CONTEXT>>>" in prompts[0][0] and "Tone: professional" in prompts[0][0]
    assert prompts[0][1] == 200

    async def one_line(_prompt, max_tokens=0):
        return "A single concise point"

    tool._call_llm = one_line
    assert (
        await tool.execute(GenerateSectionInput(section_type="next_steps", max_length=100))
    ).key_points == ["A single concise point"]

    async def budget(*_args, **_kwargs):
        raise LLMBudgetExceededError("cap")

    tool._call_llm = budget
    blocked = await tool.execute(GenerateSectionInput(section_type="roi_analysis", max_length=100))
    assert blocked.word_count == 0 and "budget guardrail" in blocked.error

    async def fail(*_args, **_kwargs):
        raise RuntimeError("offline")

    tool._call_llm = fail
    failed = await tool.execute(GenerateSectionInput(section_type="current_state", max_length=100))
    assert failed.content == "" and "offline" in failed.error

    async def cancel(*_args, **_kwargs):
        raise asyncio.CancelledError

    tool._call_llm = cancel
    with pytest.raises(asyncio.CancelledError):
        await tool.execute(GenerateSectionInput(section_type="implementation", max_length=100))


@pytest.mark.asyncio
@pytest.mark.parametrize("chart_type", ["bar", "pie", "line", "table", "funnel"])
async def test_create_chart_formats_every_supported_type(chart_type) -> None:
    data = [{"label": "A", "category": "Fallback", "value": 2, "series": "S", "x": [1], "y": [2]}]
    result = await CreateChartTool().execute(
        CreateChartInput(chart_type=chart_type, data=data, title="Chart", config={"headers": ["A"]})
    )
    assert result.chart_data["type"] == chart_type and result.chart_data["data"] == data
    expected = {"bar": "x_axis", "pie": "slices", "line": "series", "table": "rows"}
    if chart_type in expected:
        assert expected[chart_type] in result.chart_data


@pytest.mark.asyncio
@pytest.mark.parametrize("fmt", ["html", "markdown", "csv"])
async def test_format_table_sorts_without_mutating_and_formats(fmt) -> None:
    rows = [["b", 2], ["a", 1]]
    result = await FormatTableTool().execute(
        FormatTableInput(headers=["Name", "Value"], rows=rows, format=fmt, sort_column=0)
    )
    assert result.row_count == 2 and rows == [["b", 2], ["a", 1]]
    assert "a" in result.formatted and "b" in result.formatted
    if fmt == "html":
        assert "<table" in result.formatted
    elif fmt == "markdown":
        assert "| --- |" in result.formatted
    else:
        assert '"Name","Value"' in result.formatted


@pytest.mark.asyncio
async def test_assemble_document_html_json_docx_and_pdf_fallback(monkeypatch) -> None:
    tool = AssembleDocumentTool()
    sections = [{"title": "Summary", "content": "Content"}, {}]
    branding = {"title": "Value Case", "company_name": "Acme", "date": "2026"}
    for output_format in ("html", "json", "docx"):
        result = await tool.execute(
            AssembleDocumentInput(sections=sections, output_format=output_format, branding=branding)
        )
        assert result.page_count == 4 and result.file_size_bytes == len(result.document_bytes)
        assert result.document_bytes
    json_result = await tool._generate_json(sections, branding)
    assert json.loads(json_result)["title"] == "Value Case"
    html = await tool._generate_html_content(sections, branding)
    assert "Prepared for Acme" in html and "<h2>Summary</h2>" in html and "<h2>Section</h2>" in html

    monkeypatch.setattr(generation_module, "WEASYPRINT_AVAILABLE", False)
    pdf = await tool.execute(
        AssembleDocumentInput(sections=sections, output_format="pdf", branding=branding)
    )
    assert pdf.document_bytes.startswith(b"<!DOCTYPE html>")

    class FakeHTML:
        def __init__(self, *, string):
            assert "Business Case" in string

        def write_pdf(self):
            return b"PDF"

    monkeypatch.setattr(generation_module, "WEASYPRINT_AVAILABLE", True)
    monkeypatch.setattr(generation_module, "HTML", FakeHTML)
    assert await tool._generate_pdf(sections, branding) == b"PDF"
