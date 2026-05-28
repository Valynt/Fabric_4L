from __future__ import annotations

"""Utility tools for validation, formatting, and common operations."""


from ..models.tool_schemas import (
    FormatCurrencyInput,
    FormatCurrencyOutput,
    ToolCategory,
    ValidateInputInput,
    ValidateInputOutput,
)
from .registry import BaseTool


class ValidateInputTool(BaseTool):
    """Validate input data against schemas."""

    name = "validate_input"
    category = ToolCategory.UTILITY
    description = "Validates input data against defined schemas"
    input_schema = ValidateInputInput
    output_schema = ValidateInputOutput
    timeout_seconds = 5

    async def execute(self, input_data: ValidateInputInput) -> ValidateInputOutput:
        """Validate input against schema."""
        data = input_data.data
        schema_name = input_data.schema_name

        errors = []
        normalized = {}

        # Mock schema validation for common types with structured error context
        if schema_name == "prospect_id":
            field_path = "prospect_id"
            if "prospect_id" not in data:
                errors.append(f"[{field_path}] Missing required field")
            elif not data["prospect_id"]:
                errors.append(f"[{field_path}] Value cannot be empty")
            elif not isinstance(data["prospect_id"], str):
                errors.append(f"[{field_path}] Expected string, got {type(data['prospect_id']).__name__}")
            else:
                normalized["prospect_id"] = data["prospect_id"].strip()

        elif schema_name == "value_drivers":
            field_path = "value_driver_ids"
            if "value_driver_ids" not in data:
                errors.append(f"[{field_path}] Missing required field")
            elif not data["value_driver_ids"]:
                errors.append(f"[{field_path}] At least one value_driver_id is required")
            elif not isinstance(data["value_driver_ids"], list):
                errors.append(f"[{field_path}] Expected list, got {type(data['value_driver_ids']).__name__}")
            else:
                normalized["value_driver_ids"] = [vid.strip() for vid in data["value_driver_ids"]]

        elif schema_name == "formula":
            if "formula" not in data or not data["formula"]:
                errors.append("Formula is required")
            else:
                formula = data["formula"]
                # Check for invalid characters with expanded operator whitelist
                # Allows: numbers, basic operators, power (^, **), modulo (%), comparison, whitespace
                allowed = set("0123456789+-*/().{}_ ^%<>!=&|")
                invalid = set(formula) - allowed
                if invalid:
                    errors.append(f"[formula] Invalid characters: {''.join(sorted(invalid))}. Allowed: 0-9, operators, parentheses, whitespace")
                else:
                    normalized["formula"] = formula

                if "variables" in data:
                    normalized["variables"] = data["variables"]

        elif schema_name == "email":
            import re

            email = data.get("email", "")
            # RFC-compliant email regex with anchors for strict validation
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not email:
                errors.append("[email] Value cannot be empty")
            elif not re.match(email_pattern, email):
                display_email = email[:50] + "..." if len(email) > 50 else email
                errors.append(f"[email] Invalid format: expected user@domain.tld, got '{display_email}'")
            else:
                normalized["email"] = email.lower().strip()

        else:
            # Generic pass-through
            normalized = data.copy()

        return ValidateInputOutput(valid=len(errors) == 0, errors=errors, normalized=normalized)


class FormatCurrencyTool(BaseTool):
    """Format numeric values as currency strings."""

    name = "format_currency"
    category = ToolCategory.UTILITY
    description = "Formats numeric values as localized currency strings"
    input_schema = FormatCurrencyInput
    output_schema = FormatCurrencyOutput
    timeout_seconds = 5

    CURRENCY_SYMBOLS = {
        "USD": "$",
        "EUR": "€",
        "GBP": "£",
        "JPY": "¥",
        "CAD": "C$",
        "AUD": "A$",
    }

    async def execute(self, input_data: FormatCurrencyInput) -> FormatCurrencyOutput:
        """Format as currency."""
        amount = input_data.amount
        currency = input_data.currency.upper()
        decimals = input_data.decimals

        symbol = self.CURRENCY_SYMBOLS.get(currency, currency)

        # Format number
        if decimals == 0:
            formatted_number = f"{int(abs(amount)):,}"
        else:
            formatted_number = f"{abs(amount):,.{decimals}f}"

        # Add symbol and sign
        if amount < 0:
            formatted = f"-{symbol}{formatted_number}"
        else:
            formatted = f"{symbol}{formatted_number}"

        return FormatCurrencyOutput(formatted=formatted, numeric=amount, currency=currency)
