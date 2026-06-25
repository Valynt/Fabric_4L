from __future__ import annotations

"""
Tests for Neo4jVariableRegistry pure helper methods.

Covers (no Neo4j required):
- _cast_value: STRING, INTEGER, DECIMAL, BOOLEAN, DATE, ENUM, JSON, None, unknown type
- _apply_rule: range, regex, enum, unknown rule type
"""


from datetime import datetime
from decimal import Decimal

import pytest

from layer4_agents.interfaces.variable_registry import (
    VariableDataType,
    VariableValidationRule,
)
from layer4_agents.services.variable_registry_service import Neo4jVariableRegistry

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def registry() -> Neo4jVariableRegistry:
    """Return registry with a dummy driver (driver not called in unit tests)."""
    return Neo4jVariableRegistry(driver=None)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# _cast_value
# ---------------------------------------------------------------------------

class TestCastValue:
    """Tests for _cast_value type coercions."""

    def test_cast_none_returns_none(self, registry):
        assert registry._cast_value(None, VariableDataType.STRING) is None

    def test_cast_to_string(self, registry):
        assert registry._cast_value(42, VariableDataType.STRING) == "42"

    def test_cast_to_integer(self, registry):
        assert registry._cast_value("7", VariableDataType.INTEGER) == 7

    def test_cast_to_integer_invalid_raises(self, registry):
        with pytest.raises((ValueError, TypeError)):
            registry._cast_value("not-a-number", VariableDataType.INTEGER)

    def test_cast_to_decimal(self, registry):
        result = registry._cast_value("3.14", VariableDataType.DECIMAL)
        assert result == Decimal("3.14")

    def test_cast_boolean_true_string(self, registry):
        for truthy in ("true", "1", "yes", "on"):
            assert registry._cast_value(truthy, VariableDataType.BOOLEAN) is True

    def test_cast_boolean_false_string(self, registry):
        assert registry._cast_value("false", VariableDataType.BOOLEAN) is False

    def test_cast_boolean_from_bool(self, registry):
        assert registry._cast_value(True, VariableDataType.BOOLEAN) is True
        assert registry._cast_value(False, VariableDataType.BOOLEAN) is False

    def test_cast_date_from_iso_string(self, registry):
        iso_str = "2024-01-15T10:00:00"
        result = registry._cast_value(iso_str, VariableDataType.DATE)
        assert isinstance(result, datetime)
        assert result.day == 15

    def test_cast_date_passthrough_non_string(self, registry):
        """Non-string date values are returned as-is."""
        dt = datetime(2024, 6, 1)
        assert registry._cast_value(dt, VariableDataType.DATE) == dt

    def test_cast_enum_returns_string(self, registry):
        assert registry._cast_value("LOW", VariableDataType.ENUM) == "LOW"

    def test_cast_json_from_string(self, registry):
        payload = '{"key": "value"}'
        result = registry._cast_value(payload, VariableDataType.JSON)
        assert result == {"key": "value"}

    def test_cast_json_passthrough_dict(self, registry):
        data = {"already": "parsed"}
        assert registry._cast_value(data, VariableDataType.JSON) == data

    def test_cast_unknown_type_passthrough(self, registry):
        """Unknown data types return the original value unchanged."""
        sentinel = object()
        # Use an unexpected enum value by patching temporarily
        # We model this by passing a non-enum directly to _cast_value via a fake type
        # that won't match any branch — the function should return value unchanged.
        class FakeType:
            pass

        result = registry._cast_value(sentinel, FakeType())  # type: ignore[arg-type]
        assert result is sentinel


# ---------------------------------------------------------------------------
# _apply_rule
# ---------------------------------------------------------------------------

class TestApplyRule:
    """Tests for _apply_rule validation rule evaluation."""

    def _rule(self, rule_type: str, params: dict, error_msg: str = "Validation error") -> VariableValidationRule:
        return VariableValidationRule(rule_type=rule_type, parameters=params, error_message=error_msg)

    # --- range ---

    def test_range_within_bounds_passes(self, registry):
        rule = self._rule("range", {"min": 1, "max": 100})
        ok, msg = registry._apply_rule(50, rule)
        assert ok is True
        assert msg is None

    def test_range_at_min_passes(self, registry):
        rule = self._rule("range", {"min": 5, "max": 10})
        ok, _ = registry._apply_rule(5, rule)
        assert ok is True

    def test_range_below_min_fails(self, registry):
        rule = self._rule("range", {"min": 10, "max": 100}, "Too small")
        ok, msg = registry._apply_rule(5, rule)
        assert ok is False
        assert msg == "Too small"

    def test_range_above_max_fails(self, registry):
        rule = self._rule("range", {"min": 0, "max": 10}, "Too large")
        ok, msg = registry._apply_rule(999, rule)
        assert ok is False
        assert msg == "Too large"

    def test_range_only_min_no_max(self, registry):
        rule = self._rule("range", {"min": 1})
        ok, _ = registry._apply_rule(100, rule)
        assert ok is True

    def test_range_only_max_no_min(self, registry):
        rule = self._rule("range", {"max": 50})
        ok, _ = registry._apply_rule(10, rule)
        assert ok is True

    # --- regex ---

    def test_regex_match_passes(self, registry):
        rule = self._rule("regex", {"pattern": r"\d{3}-\d{4}"})
        ok, _ = registry._apply_rule("123-4567", rule)
        assert ok is True

    def test_regex_no_match_fails(self, registry):
        rule = self._rule("regex", {"pattern": r"\d+"}, "Must be digits")
        ok, msg = registry._apply_rule("abc", rule)
        assert ok is False
        assert msg == "Must be digits"

    def test_regex_default_pattern_accepts_anything(self, registry):
        """Missing pattern defaults to '.*', which accepts any string."""
        rule = self._rule("regex", {})
        ok, _ = registry._apply_rule("anything", rule)
        assert ok is True

    def test_regex_anchored_pattern_rejects_partial(self, registry):
        """Pattern is anchored so partial matches are rejected."""
        rule = self._rule("regex", {"pattern": r"\d+"})
        # "12abc" won't fully match ^\d+$
        ok, _ = registry._apply_rule("12abc", rule)
        assert ok is False

    # --- enum ---

    def test_enum_allowed_value_passes(self, registry):
        rule = self._rule("enum", {"values": ["low", "medium", "high"]})
        ok, _ = registry._apply_rule("medium", rule)
        assert ok is True

    def test_enum_disallowed_value_fails(self, registry):
        rule = self._rule("enum", {"values": ["low", "medium", "high"]}, "Invalid choice")
        ok, msg = registry._apply_rule("extreme", rule)
        assert ok is False
        assert msg == "Invalid choice"

    def test_enum_empty_values_fails_any(self, registry):
        """Empty allowed list causes any value to fail."""
        rule = self._rule("enum", {"values": []})
        ok, _ = registry._apply_rule("anything", rule)
        assert ok is False

    # --- unknown rule type ---

    def test_unknown_rule_type_passes(self, registry):
        """An unrecognised rule_type defaults to passing (no-op)."""
        rule = self._rule("nonexistent_rule", {})
        ok, msg = registry._apply_rule("value", rule)
        assert ok is True
        assert msg is None
