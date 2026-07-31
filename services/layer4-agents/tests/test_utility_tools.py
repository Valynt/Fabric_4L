from __future__ import annotations

import pytest

from layer4_agents.models.tool_schemas import FormatCurrencyInput, ValidateInputInput
from layer4_agents.tools.utility_tools import FormatCurrencyTool, ValidateInputTool


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("schema", "data", "valid", "normalized", "error_fragment"),
    [
        ("prospect_id", {}, False, {}, "Missing required field"),
        ("prospect_id", {"prospect_id": ""}, False, {}, "cannot be empty"),
        ("prospect_id", {"prospect_id": 7}, False, {}, "Expected string"),
        (
            "prospect_id",
            {"prospect_id": "  prospect-1  "},
            True,
            {"prospect_id": "prospect-1"},
            None,
        ),
        ("value_drivers", {}, False, {}, "Missing required field"),
        ("value_drivers", {"value_driver_ids": []}, False, {}, "At least one"),
        ("value_drivers", {"value_driver_ids": "driver"}, False, {}, "Expected list"),
        (
            "value_drivers",
            {"value_driver_ids": [" a ", "b"]},
            True,
            {"value_driver_ids": ["a", "b"]},
            None,
        ),
        ("formula", {}, False, {}, "Formula is required"),
        (
            "formula",
            {"formula": "revenue + cost", "variables": {"revenue": 1}},
            False,
            {"variables": {"revenue": 1}},
            "Invalid characters",
        ),
        (
            "formula",
            {"formula": "{0} * 1.2", "variables": {"revenue": 1}},
            True,
            {"formula": "{0} * 1.2", "variables": {"revenue": 1}},
            None,
        ),
        ("email", {}, False, {}, "cannot be empty"),
        ("email", {"email": "not-an-email"}, False, {}, "Invalid format"),
        ("email", {"email": " Person@Example.COM "}, False, {}, "Invalid format"),
        ("email", {"email": "Person@Example.COM"}, True, {"email": "person@example.com"}, None),
        ("unknown", {"unchanged": [1, 2]}, True, {"unchanged": [1, 2]}, None),
    ],
)
async def test_validate_input_behaviors(
    schema: str,
    data: dict,
    valid: bool,
    normalized: dict,
    error_fragment: str | None,
) -> None:
    result = await ValidateInputTool().execute(ValidateInputInput(schema_name=schema, data=data))

    assert result.valid is valid
    assert result.normalized == normalized
    if error_fragment is None:
        assert result.errors == []
    else:
        assert any(error_fragment in error for error in result.errors)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("amount", "currency", "decimals", "formatted"),
    [
        (1234.4, "usd", 0, "$1,234"),
        (1234.5, "EUR", 2, "€1,234.50"),
        (-99.9, "GBP", 1, "-£99.9"),
        (1000, "JPY", 0, "¥1,000"),
        (10, "CAD", 0, "C$10"),
        (10, "AUD", 0, "A$10"),
        (10, "CHF", 0, "CHF10"),
    ],
)
async def test_format_currency_behaviors(
    amount: float, currency: str, decimals: int, formatted: str
) -> None:
    result = await FormatCurrencyTool().execute(
        FormatCurrencyInput(amount=amount, currency=currency, decimals=decimals)
    )

    assert result.formatted == formatted
    assert result.numeric == amount
    assert result.currency == currency.upper()
