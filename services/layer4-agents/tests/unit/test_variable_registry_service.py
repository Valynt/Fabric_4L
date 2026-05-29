from __future__ import annotations

"""
Unit tests for Neo4jVariableRegistry helper methods.

Tests the pure-Python logic (_cast_value, _apply_rule) that requires no Neo4j
connection, and integration-level behaviour with a mocked AsyncDriver.
"""


import json
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from layer4_agents.services.variable_registry_service import Neo4jVariableRegistry
from layer4_agents.interfaces.variable_registry import (
    VariableDataType,
    VariableValidationRule,
)


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _registry() -> Neo4jVariableRegistry:
    """Return a registry with a stub Neo4j driver."""
    driver = MagicMock()
    return Neo4jVariableRegistry(driver=driver)


# ──────────────────────────────────────────────────────────────────────────────
# _cast_value
# ──────────────────────────────────────────────────────────────────────────────

class TestCastValue:
    """Tests for Neo4jVariableRegistry._cast_value."""

    @pytest.mark.unit
    def test_cast_none_returns_none(self):
        reg = _registry()
        for dtype in VariableDataType:
            assert reg._cast_value(None, dtype) is None

    @pytest.mark.unit
    def test_cast_string(self):
        reg = _registry()
        assert reg._cast_value(42, VariableDataType.STRING) == "42"
        assert reg._cast_value("hello", VariableDataType.STRING) == "hello"

    @pytest.mark.unit
    def test_cast_integer(self):
        reg = _registry()
        assert reg._cast_value("7", VariableDataType.INTEGER) == 7
        assert reg._cast_value(3.9, VariableDataType.INTEGER) == 3
        assert isinstance(reg._cast_value(5, VariableDataType.INTEGER), int)

    @pytest.mark.unit
    def test_cast_integer_invalid_raises(self):
        reg = _registry()
        with pytest.raises((ValueError, TypeError)):
            reg._cast_value("not-a-number", VariableDataType.INTEGER)

    @pytest.mark.unit
    def test_cast_decimal(self):
        reg = _registry()
        result = reg._cast_value("3.14", VariableDataType.DECIMAL)
        assert isinstance(result, Decimal)
        assert result == Decimal("3.14")

    @pytest.mark.unit
    def test_cast_boolean_truthy_strings(self):
        reg = _registry()
        for val in ("true", "1", "yes", "on"):
            assert reg._cast_value(val, VariableDataType.BOOLEAN) is True

    @pytest.mark.unit
    def test_cast_boolean_falsy_strings(self):
        reg = _registry()
        for val in ("false", "0", "no", "off", ""):
            assert reg._cast_value(val, VariableDataType.BOOLEAN) is False

    @pytest.mark.unit
    def test_cast_boolean_native_bool(self):
        reg = _registry()
        assert reg._cast_value(True, VariableDataType.BOOLEAN) is True
        assert reg._cast_value(False, VariableDataType.BOOLEAN) is False

    @pytest.mark.unit
    def test_cast_date_from_iso_string(self):
        reg = _registry()
        result = reg._cast_value("2024-03-15T00:00:00", VariableDataType.DATE)
        assert isinstance(result, datetime)
        assert result.year == 2024
        assert result.month == 3
        assert result.day == 15

    @pytest.mark.unit
    def test_cast_date_passthrough_for_non_string(self):
        reg = _registry()
        dt = datetime(2024, 1, 1, tzinfo=UTC)
        assert reg._cast_value(dt, VariableDataType.DATE) is dt

    @pytest.mark.unit
    def test_cast_enum_to_string(self):
        reg = _registry()
        assert reg._cast_value("ACTIVE", VariableDataType.ENUM) == "ACTIVE"
        assert reg._cast_value(123, VariableDataType.ENUM) == "123"

    @pytest.mark.unit
    def test_cast_json_from_string(self):
        reg = _registry()
        payload = {"key": "value", "num": 42}
        result = reg._cast_value(json.dumps(payload), VariableDataType.JSON)
        assert result == payload

    @pytest.mark.unit
    def test_cast_json_passthrough_for_dict(self):
        reg = _registry()
        payload = {"already": "parsed"}
        assert reg._cast_value(payload, VariableDataType.JSON) is payload

    @pytest.mark.unit
    def test_cast_json_invalid_string_raises(self):
        reg = _registry()
        with pytest.raises(json.JSONDecodeError):
            reg._cast_value("not-json{{{", VariableDataType.JSON)


# ──────────────────────────────────────────────────────────────────────────────
# _apply_rule
# ──────────────────────────────────────────────────────────────────────────────

class TestApplyRule:
    """Tests for Neo4jVariableRegistry._apply_rule."""

    def _range_rule(self, min_val=None, max_val=None, msg="out of range") -> VariableValidationRule:
        params = {}
        if min_val is not None:
            params["min"] = min_val
        if max_val is not None:
            params["max"] = max_val
        return VariableValidationRule(rule_type="range", parameters=params, error_message=msg)

    def _regex_rule(self, pattern: str, msg="pattern mismatch") -> VariableValidationRule:
        return VariableValidationRule(
            rule_type="regex", parameters={"pattern": pattern}, error_message=msg
        )

    def _enum_rule(self, values: list, msg="not in enum") -> VariableValidationRule:
        return VariableValidationRule(
            rule_type="enum", parameters={"values": values}, error_message=msg
        )

    @pytest.mark.unit
    def test_range_below_min_fails(self):
        reg = _registry()
        ok, err = reg._apply_rule(4, self._range_rule(min_val=5))
        assert ok is False
        assert err == "out of range"

    @pytest.mark.unit
    def test_range_above_max_fails(self):
        reg = _registry()
        ok, err = reg._apply_rule(101, self._range_rule(max_val=100))
        assert ok is False

    @pytest.mark.unit
    def test_range_at_boundary_passes(self):
        reg = _registry()
        ok, err = reg._apply_rule(5, self._range_rule(min_val=5, max_val=10))
        assert ok is True
        assert err is None

        ok, err = reg._apply_rule(10, self._range_rule(min_val=5, max_val=10))
        assert ok is True

    @pytest.mark.unit
    def test_range_within_bounds_passes(self):
        reg = _registry()
        ok, err = reg._apply_rule(7, self._range_rule(min_val=5, max_val=10))
        assert ok is True

    @pytest.mark.unit
    def test_range_no_min_no_max_passes(self):
        reg = _registry()
        ok, err = reg._apply_rule(9999, self._range_rule())
        assert ok is True

    @pytest.mark.unit
    def test_regex_matching_value_passes(self):
        reg = _registry()
        rule = self._regex_rule(r"[A-Z]{2}-\d{4}")
        ok, err = reg._apply_rule("AB-1234", rule)
        assert ok is True

    @pytest.mark.unit
    def test_regex_non_matching_value_fails(self):
        reg = _registry()
        rule = self._regex_rule(r"[A-Z]{2}-\d{4}")
        ok, err = reg._apply_rule("bad-value", rule)
        assert ok is False
        assert err == "pattern mismatch"

    @pytest.mark.unit
    def test_regex_partial_match_fails(self):
        """Regex must match the full string (anchors added automatically)."""
        reg = _registry()
        rule = self._regex_rule(r"\d+")  # digits only
        # "abc123" should fail because the rule anchors the pattern
        ok, err = reg._apply_rule("abc123", rule)
        assert ok is False

    @pytest.mark.unit
    def test_regex_default_pattern_passes_all(self):
        reg = _registry()
        rule = VariableValidationRule(
            rule_type="regex", parameters={}, error_message="fail"
        )
        ok, _ = reg._apply_rule("anything", rule)
        assert ok is True

    @pytest.mark.unit
    def test_enum_valid_value_passes(self):
        reg = _registry()
        rule = self._enum_rule(["ACTIVE", "INACTIVE", "PENDING"])
        ok, err = reg._apply_rule("ACTIVE", rule)
        assert ok is True

    @pytest.mark.unit
    def test_enum_invalid_value_fails(self):
        reg = _registry()
        rule = self._enum_rule(["ACTIVE", "INACTIVE"])
        ok, err = reg._apply_rule("DELETED", rule)
        assert ok is False
        assert err == "not in enum"

    @pytest.mark.unit
    def test_enum_empty_list_fails_any_value(self):
        reg = _registry()
        rule = self._enum_rule([])
        ok, err = reg._apply_rule("anything", rule)
        assert ok is False

    @pytest.mark.unit
    def test_unknown_rule_type_passes(self):
        """Unknown rule types are silently skipped (returns True)."""
        reg = _registry()
        rule = VariableValidationRule(
            rule_type="custom_unknown", parameters={}, error_message="unused"
        )
        ok, err = reg._apply_rule("value", rule)
        assert ok is True
        assert err is None


# ──────────────────────────────────────────────────────────────────────────────
# validate_value (integration of _cast_value + _apply_rule through mocked DB)
# ──────────────────────────────────────────────────────────────────────────────

class TestValidateValue:
    """Tests for validate_value via a mocked get_variable."""

    def _make_variable(self, data_type: VariableDataType, rules: list):
        from layer4_agents.interfaces.variable_registry import Variable

        return Variable(
            variable_id="var-001",
            name="Test Variable",
            description="For testing",
            data_type=data_type,
            validation_rules=rules,
        )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_validate_value_passes_for_valid_integer(self):
        from unittest.mock import patch

        reg = _registry()
        var = self._make_variable(
            VariableDataType.INTEGER,
            [
                VariableValidationRule(
                    rule_type="range", parameters={"min": 0, "max": 100}, error_message="OOB"
                )
            ],
        )

        with patch.object(reg, "get_variable", new=AsyncMock(return_value=var)):
            ok, error = await reg.validate_value("var-001", 50)

        assert ok is True
        assert error is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_validate_value_fails_for_range_violation(self):
        from unittest.mock import patch

        reg = _registry()
        var = self._make_variable(
            VariableDataType.INTEGER,
            [
                VariableValidationRule(
                    rule_type="range", parameters={"min": 0, "max": 100}, error_message="OOB"
                )
            ],
        )

        with patch.object(reg, "get_variable", new=AsyncMock(return_value=var)):
            ok, error = await reg.validate_value("var-001", 200)

        assert ok is False
        assert error == "OOB"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_validate_value_fails_for_missing_variable(self):
        from unittest.mock import patch

        reg = _registry()

        with patch.object(reg, "get_variable", new=AsyncMock(return_value=None)):
            ok, error = await reg.validate_value("var-missing", 42)

        assert ok is False
        assert "not found" in (error or "")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_validate_value_fails_type_cast_error(self):
        from unittest.mock import patch

        reg = _registry()
        var = self._make_variable(VariableDataType.INTEGER, [])

        with patch.object(reg, "get_variable", new=AsyncMock(return_value=var)):
            ok, error = await reg.validate_value("var-001", "not-an-int")

        assert ok is False
        assert error is not None
