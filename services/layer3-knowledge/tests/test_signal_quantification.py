"""Unit tests for signal quantification service.

Tests cover safe formula evaluation, variable extraction, and formula selection fallback.
"""

from __future__ import annotations

import pytest

from src.services.signal_quantification import (
    FormulaEvalError,
    FormulaVariable,
    SignalQuantificationService,
)


class FakeAsyncResult:
    def __init__(self, record):
        self._record = record

    async def single(self):
        return self._record


class FakeSession:
    pass


class FakeDriver:
    def __init__(self, record=None):
        self._record = record

    def session(self):
        return FakeSessionContext(self._record)


class FakeSessionContext:
    def __init__(self, record):
        self._record = record

    async def __aenter__(self):
        return FakeSession()

    async def __aexit__(self, exc_type, exc, tb):
        return False


class TestSafeEval:
    """Test safe formula evaluation with AST parsing."""

    def test_safe_eval_simple_math(self):
        service = SignalQuantificationService(driver=FakeDriver())
        result = service._safe_eval("a * b + c", {"a": 2, "b": 3, "c": 4})
        assert result == 10.0

    def test_safe_eval_direct_variable_lookup(self):
        service = SignalQuantificationService(driver=FakeDriver())
        result = service._safe_eval("cost", {"cost": 123.0})
        assert result == 123.0

    def test_safe_eval_function_call(self):
        service = SignalQuantificationService(driver=FakeDriver())
        result = service._safe_eval("abs(-5)", {})
        assert result == 5.0

    def test_safe_eval_rejects_unsafe_call(self):
        service = SignalQuantificationService(driver=FakeDriver())
        with pytest.raises(FormulaEvalError) as exc_info:
            service._safe_eval("__import__('os').system('x')", {})
        assert exc_info.value.code == "FORMULA_INVALID_EXPRESSION"
        # Raw parser/exception text must not be surfaced to callers.
        assert "__import__" not in exc_info.value.message

    def test_safe_eval_missing_variable_raises(self):
        service = SignalQuantificationService(driver=FakeDriver())
        with pytest.raises(NameError):
            service._safe_eval("a + missing", {"a": 1})


class TestSafeEvalHardening:
    """Hostile-input regression tests for formula evaluation safety bounds."""

    async def _execute(self, expression, context=None):
        service = SignalQuantificationService(driver=FakeDriver())
        return await service._execute_formula(
            {"expression": expression}, context or {}
        )

    @pytest.mark.asyncio
    async def test_oversized_expression_rejected(self):
        # Many operands -> expression string far exceeds MAX_EXPRESSION_LENGTH
        long_expr = " + ".join(["1"] * 300)
        assert len(long_expr) > 500
        result = await self._execute(long_expr, {})
        assert not result["success"]
        assert result["error_code"] == "FORMULA_TOO_LONG"
        # Message is a stable, safe constant, not raw text.
        assert result["error"] == "Formula expression exceeds the maximum allowed length."

    @pytest.mark.asyncio
    async def test_huge_exponent_rejected(self):
        # 2 ** 100000 -> exponent far exceeds MAX_POW_EXPONENT
        result = await self._execute("a ** 100000", {"a": 2})
        assert not result["success"]
        assert result["error_code"] == "FORMULA_POW_LIMIT"
        assert result["error"] == "Formula exponentiation uses values outside the allowed range."

    @pytest.mark.asyncio
    async def test_overflowing_power_rejected(self):
        # 10000 ** 100 would overflow to inf even though each side is bounded;
        # the result must be rejected as non-finite.
        result = await self._execute("a ** b", {"a": 10000, "b": 100})
        assert not result["success"]
        assert result["error_code"] == "FORMULA_NON_FINITE"

    @pytest.mark.asyncio
    async def test_deeply_nested_expression_rejected(self):
        # Parentheses create NO AST nodes in Python, so use nested unary
        # minus operators to build genuine AST depth exceeding MAX_AST_DEPTH.
        # 40 nested negations -> 41 AST nodes, depth 41 > MAX_AST_DEPTH.
        deep = "".join(["- " for _ in range(40)]) + "1"
        result = await self._execute(deep, {})
        assert not result["success"]
        assert result["error_code"] == "FORMULA_TOO_DEEP"
        assert result["error"] == "Formula expression is nested too deeply."

    @pytest.mark.asyncio
    async def test_many_nodes_expression_rejected(self):
        # A single shallow `min` call with ~110 args yields >MAX_AST_NODES
        # (1 Call + 110 constants) while staying under the character limit
        # and safely within the depth limit, exercising the node-count bound.
        expr = "min(" + ",".join(str(i) for i in range(1, 110)) + ")"
        assert len(expr) <= 500
        result = await self._execute(expr, {})
        assert not result["success"]
        assert result["error_code"] == "FORMULA_TOO_COMPLEX"

    @pytest.mark.asyncio
    async def test_non_finite_constant_rejected(self):
        # 1e400 parses to an infinite float constant.
        result = await self._execute("1e400", {})
        assert not result["success"]
        assert result["error_code"] == "FORMULA_NON_FINITE"

    @pytest.mark.asyncio
    async def test_non_finite_input_variable_rejected(self):
        # Variable bound to inf must be rejected as a non-finite input.
        result = await self._execute("a + 1", {"a": float("inf")})
        assert not result["success"]
        assert result["error_code"] == "FORMULA_NON_FINITE"

    @pytest.mark.asyncio
    async def test_non_finite_negative_inf_rejected(self):
        result = await self._execute("a * 2", {"a": float("-inf")})
        assert not result["success"]
        assert result["error_code"] == "FORMULA_NON_FINITE"

    @pytest.mark.asyncio
    async def test_nan_rejected(self):
        result = await self._execute("a", {"a": float("nan")})
        assert not result["success"]
        assert result["error_code"] == "FORMULA_NON_FINITE"

    @pytest.mark.asyncio
    async def test_division_by_zero_does_not_leak(self):
        # Arithmetic failure must NOT surface raw exception text to the caller.
        result = await self._execute("1 / 0", {})
        assert not result["success"]
        assert result["error_code"] == "FORMULA_INVALID_EXPRESSION"
        assert "ZeroDivisionError" not in result["error"]
        assert result["error"] == "Formula expression is invalid or uses unsupported constructs."

    @pytest.mark.asyncio
    async def test_non_finite_does_not_leak_raw_text(self):
        result = await self._execute("1e400", {})
        assert not result["success"]
        assert "inf" not in result["error"].lower()
        assert result["error"] == "Formula produced or used a non-finite numeric value."

    @pytest.mark.asyncio
    async def test_ordinary_arithmetic_allowed(self):
        result = await self._execute("a * b + c", {"a": 2, "b": 3, "c": 4})
        assert result["success"]
        assert result["value"] == 10.0
        assert result["error_code"] == ""

    @pytest.mark.asyncio
    async def test_bounded_power_allowed(self):
        result = await self._execute("a ** b", {"a": 10, "b": 3})
        assert result["success"]
        assert result["value"] == 1000.0

    @pytest.mark.asyncio
    async def test_unsafe_call_entrypoint_rejected(self):
        result = await self._execute("__import__('os').system('x')", {})
        assert not result["success"]
        assert result["error_code"] == "FORMULA_INVALID_EXPRESSION"


class TestExtractFromIndicators:
    """Test extraction of numeric values from indicator text."""

    def test_extract_from_indicators_dollars_millions(self):
        service = SignalQuantificationService(driver=FakeDriver())
        # K/M suffix must be immediately after the number
        result = service._extract_from_indicators("annual_cost", ["$1.5M annual"])
        assert result == 1_500_000.0

    def test_extract_from_indicators_dollars_thousands(self):
        service = SignalQuantificationService(driver=FakeDriver())
        result = service._extract_from_indicators("annual_cost", ["$500K year"])
        assert result == 500_000.0

    def test_extract_from_indicators_no_suffix_no_multiplier(self):
        service = SignalQuantificationService(driver=FakeDriver())
        # Without K/M suffix, should not multiply
        result = service._extract_from_indicators("annual_cost", ["$1.5 annual"])
        assert result == 1.5

    def test_extract_from_indicators_m_in_word_does_not_multiply(self):
        service = SignalQuantificationService(driver=FakeDriver())
        # "m" in "annual" should NOT trigger million multiplier
        result = service._extract_from_indicators("annual_cost", ["$1.5 annual"])
        assert result == 1.5, "Should not multiply by 1M just because 'm' appears in 'annual'"

    def test_extract_from_indicators_no_match_returns_none(self):
        service = SignalQuantificationService(driver=FakeDriver())
        result = service._extract_from_indicators("annual_cost", ["no numbers here"])
        assert result is None


class TestValidateAndFillVariables:
    """Test variable validation and default value application."""

    def test_validate_and_fill_variables_applies_defaults(self):
        service = SignalQuantificationService(driver=FakeDriver())
        var = FormulaVariable(
            name="x",
            display_name="X",
            value=None,
            default_value=50.0,
        )
        result = service._validate_and_fill_variables([var])
        assert result["x"] == 50.0
        assert "_errors" not in result

    def test_validate_and_fill_variables_enforces_range(self):
        service = SignalQuantificationService(driver=FakeDriver())
        var = FormulaVariable(
            name="x",
            display_name="X",
            value=150.0,
            default_value=50.0,
            valid_range=(0.0, 100.0),
        )
        result = service._validate_and_fill_variables([var])
        assert result["x"] == 50.0  # Falls back to default
        assert "_errors" in result


class TestSelectFormula:
    """Test formula selection with fallback."""

    @pytest.mark.asyncio
    async def test_select_formula_fallback_when_no_graph_record(self, monkeypatch):
        service = SignalQuantificationService(driver=FakeDriver())

        async def fake_run_query(session, query, parameters, **kwargs):
            return FakeAsyncResult(None)

        monkeypatch.setattr(
            "src.services.signal_quantification.run_validated_query", fake_run_query
        )

        result = await service._select_formula(
            tenant_id="tenant-1",
            signal_name="Manual invoice processing",
            signal_description="desc",
            industry="manufacturing",
        )
        assert result["id"] == "default-operational"
        assert result["expression"] == "estimated_annual_cost"

    @pytest.mark.asyncio
    async def test_select_formula_returns_graph_record(self, monkeypatch):
        service = SignalQuantificationService(driver=FakeDriver())
        formula_record = {
            "formula": {
                "id": "ai-f-001",
                "name": "AI ROI",
                "expression": "a * b",
                "output_unit": "USD/year",
                "variables": [],
            }
        }

        async def fake_run_query(session, query, parameters, **kwargs):
            return FakeAsyncResult(formula_record)

        monkeypatch.setattr(
            "src.services.signal_quantification.run_validated_query", fake_run_query
        )

        result = await service._select_formula(
            tenant_id="tenant-1",
            signal_name="Signal",
            signal_description="desc",
            industry="manufacturing",
        )
        assert result["id"] == "ai-f-001"


class TestQuantifySignal:
    """Test the main quantify_signal method."""

    @pytest.mark.asyncio
    async def test_quantify_signal_success_with_fallback(self, monkeypatch):
        service = SignalQuantificationService(driver=FakeDriver())

        async def fake_run_query(session, query, parameters, **kwargs):
            return FakeAsyncResult(None)  # Force fallback

        monkeypatch.setattr(
            "src.services.signal_quantification.run_validated_query", fake_run_query
        )

        result = await service.quantify_signal(
            tenant_id="tenant-1",
            signal_name="Manual invoice processing",
            signal_description="desc",
            impact_indicators=[],
            industry="manufacturing",
            prospect_data={"estimated_annual_cost": 1_200_000.0},
        )
        assert result.success
        assert result.formula_id == "default-operational"
        assert result.impact_value == 1_200_000.0

    @pytest.mark.asyncio
    async def test_quantify_signal_no_formula(self, monkeypatch):
        service = SignalQuantificationService(driver=FakeDriver())

        async def fake_select(*args, **kwargs):
            return None

        monkeypatch.setattr(service, "_select_formula", fake_select)

        result = await service.quantify_signal(
            tenant_id="tenant-1",
            signal_name="Signal",
            signal_description="desc",
            impact_indicators=[],
            industry="manufacturing",
            prospect_data={},
        )
        assert not result.success
        assert len(result.errors) > 0
        assert "formula" in result.errors[0].lower()

    @pytest.mark.asyncio
    async def test_quantify_signal_validation_error(self, monkeypatch):
        service = SignalQuantificationService(driver=FakeDriver())

        async def fake_select(*args, **kwargs):
            return {
                "id": "test-formula",
                "name": "Test",
                "expression": "x",
                "output_unit": "USD/year",
                "variables": [],
            }

        monkeypatch.setattr(service, "_select_formula", fake_select)
        monkeypatch.setattr(
            service, "_validate_and_fill_variables", lambda vars: {"_errors": ["bad"]}
        )

        result = await service.quantify_signal(
            tenant_id="tenant-1",
            signal_name="Signal",
            signal_description="desc",
            impact_indicators=[],
            industry="manufacturing",
            prospect_data={},
        )
        assert not result.success
        assert len(result.errors) > 0
