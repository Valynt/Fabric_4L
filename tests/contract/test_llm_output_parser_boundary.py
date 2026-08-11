"""Contract tests for the canonical §2.5 LLM output parse boundary (ADR-031).

The launch target is 100% schema-valid structured output where schemas are
required. These tests pin the failure policy: invalid output must never
silently become ``{}`` at call sites that demand a shape — it must raise a
typed, observable error (``LLMOutputParseError`` / schema validation errors).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

pytestmark = [pytest.mark.contract_static, pytest.mark.unit]

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "packages" / "platform-contract" / "src" / "python"))

from canonical.llm_output_parser import (  # noqa: E402
    LLMOutputParseError,
    parse_llm_json,
    validate_llm_output_schema,
)


class TestLegacyCompatibility:
    def test_clean_json_parses(self) -> None:
        assert parse_llm_json('{"a": 1}') == {"a": 1}

    def test_prose_wrapped_json_parses(self) -> None:
        assert parse_llm_json('Sure! Here you go: {"a": 1} — hope that helps') == {"a": 1}

    def test_array_wrapped_as_result(self) -> None:
        assert parse_llm_json('[1, 2]') == {"result": [1, 2]}

    def test_total_failure_returns_empty_dict_by_default(self) -> None:
        assert parse_llm_json("no json here") == {}
        assert parse_llm_json("") == {}


class TestStrictMode:
    def test_strict_raises_on_total_failure(self) -> None:
        with pytest.raises(LLMOutputParseError) as exc_info:
            parse_llm_json("definitely not json", strict=True, call_site="unit-test")
        assert exc_info.value.call_site == "unit-test"
        assert "definitely not json" in exc_info.value.content_preview

    def test_strict_raises_on_empty(self) -> None:
        with pytest.raises(LLMOutputParseError):
            parse_llm_json("", strict=True)

    def test_strict_still_parses_valid_output(self) -> None:
        assert parse_llm_json('{"ok": true}', strict=True) == {"ok": True}


class TestRequiredKeys:
    def test_missing_required_keys_raise_with_key_names(self) -> None:
        with pytest.raises(LLMOutputParseError) as exc_info:
            parse_llm_json('{"a": 1}', required_keys=["a", "b", "c"])
        assert "'b'" in str(exc_info.value) and "'c'" in str(exc_info.value)

    def test_required_keys_pass_when_present(self) -> None:
        assert parse_llm_json('{"a": 1, "b": 2}', required_keys=["a", "b"]) == {"a": 1, "b": 2}

    def test_required_keys_apply_to_wrapped_arrays(self) -> None:
        with pytest.raises(LLMOutputParseError):
            parse_llm_json('[1, 2]', required_keys=["missing"])


class TestSchemaValidation:
    def test_valid_output_has_no_errors(self) -> None:
        schema = {
            "type": "object",
            "required": ["intent", "confidence"],
            "properties": {"intent": {"type": "string"}, "confidence": {"type": "number"}},
        }
        assert validate_llm_output_schema({"intent": "search", "confidence": 0.9}, schema) == []

    def test_missing_required_property_reports_error(self) -> None:
        schema = {"type": "object", "required": ["intent"], "properties": {"intent": {"type": "string"}}}
        errors = validate_llm_output_schema({}, schema)
        assert errors, "schema validation must flag missing required properties"

    def test_wrong_type_reports_error(self) -> None:
        schema = {"type": "object", "properties": {"confidence": {"type": "number"}}}
        errors = validate_llm_output_schema({"confidence": "high"}, schema)
        assert errors, "schema validation must flag type violations"
