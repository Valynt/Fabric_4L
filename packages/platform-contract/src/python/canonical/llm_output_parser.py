"""Canonical §2.5 boundary for parsing LLM text output into structured dicts.

All agent and extraction code that reads JSON from a raw LLM response must go
through ``parse_llm_json``.  Direct ``json.loads`` on LLM content is a
Contract §2.5 violation.

The parser applies a two-stage strategy:
1. Direct parse — works when the model returns clean JSON.
2. Bracket extraction — finds the first ``{...}`` or ``[...]`` span using a
   depth counter to locate the correct matching close bracket, then retries.
   This handles models that wrap JSON in prose or markdown fences.

Failure policy (ADR-031): the legacy default returns an empty dict on total
failure for backwards compatibility, but any call site where a schema is
required (the launch target is 100% schema-valid structured output) must use
``strict=True`` and/or ``required_keys=...`` so invalid output raises
``LLMOutputParseError`` — a typed, observable failure — instead of silently
becoming ``{}`` and flowing downstream as if it were valid empty data.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Iterable

logger = logging.getLogger(__name__)


class LLMOutputParseError(ValueError):
    """Raised when LLM output cannot be parsed or fails required-key validation.

    Carries the call site and a truncated content preview for diagnosis.
    """

    def __init__(self, message: str, *, call_site: str = "", content_preview: str = "") -> None:
        super().__init__(message)
        self.call_site = call_site
        self.content_preview = content_preview[:400]


def _find_matching_close(content: str, start: int, open_char: str, close_char: str) -> int:
    """Return the index of the close bracket that matches the open bracket at ``start``.

    Uses a depth counter so stray brackets after the JSON span do not produce
    an incorrect end position (the ``rfind`` approach fails in that case).

    Returns -1 if no matching close bracket is found.
    """
    depth = 0
    for i in range(start, len(content)):
        if content[i] == open_char:
            depth += 1
        elif content[i] == close_char:
            depth -= 1
            if depth == 0:
                return i
    return -1


def parse_llm_json(
    content: str,
    *,
    call_site: str = "",
    strict: bool = False,
    required_keys: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Parse a raw LLM response string into a dict.

    Args:
        content: Raw text from the LLM response (or function-call arguments).
        call_site: Optional label for log messages (e.g. ``"intent_classifier"``).
        strict: When True, raise ``LLMOutputParseError`` on total parse failure
            instead of returning ``{}``. Use wherever a schema is required.
        required_keys: Optional keys that must be present in the parsed dict.
            Missing keys raise ``LLMOutputParseError`` naming the absent keys —
            the lightest form of the ADR-031 required-shape contract.

    Returns:
        Parsed dict. On total failure: ``{}`` when ``strict`` is False
        (legacy behavior), otherwise ``LLMOutputParseError`` is raised.
    """
    tag = f" [{call_site}]" if call_site else ""

    def _total_failure() -> dict[str, Any]:
        if strict:
            raise LLMOutputParseError(
                f"parse_llm_json{tag}: could not extract JSON from response",
                call_site=call_site,
                content_preview=content[:200] if content else "",
            )
        logger.warning("parse_llm_json%s: could not extract JSON from response: %r", tag, content[:200])
        return {}

    def _check_required(result: dict[str, Any]) -> dict[str, Any]:
        if required_keys:
            missing = [key for key in required_keys if key not in result]
            if missing:
                raise LLMOutputParseError(
                    f"parse_llm_json{tag}: missing required keys {missing}",
                    call_site=call_site,
                    content_preview=content[:200] if content else "",
                )
        return result

    if not content or not content.strip():
        return _total_failure()

    # Stage 1: direct parse
    try:
        result = json.loads(content)
        if isinstance(result, dict):
            return _check_required(result)
        # LLM returned a JSON array or scalar — wrap so callers always get a dict
        return _check_required({"result": result})
    except json.JSONDecodeError:
        pass

    # Stage 2: bracket extraction — find first { or [ and its matching close
    for open_char, close_char in [('{', '}'), ('[', ']')]:
        start = content.find(open_char)
        if start == -1:
            continue
        end = _find_matching_close(content, start, open_char, close_char)
        if end == -1:
            continue
        try:
            result = json.loads(content[start:end + 1])
            if isinstance(result, dict):
                return _check_required(result)
            return _check_required({"result": result})
        except json.JSONDecodeError:
            continue

    return _total_failure()


def validate_llm_output_schema(parsed: dict[str, Any], schema: dict[str, Any], *, call_site: str = "") -> list[str]:
    """Validate a parsed LLM output dict against a JSON Schema.

    Returns a list of human-readable validation errors (empty when valid).
    Uses ``jsonschema`` when available; falls back to a minimal required-keys
    check so a missing optional dependency can never silently skip validation.
    """
    try:
        import jsonschema  # type: ignore

        validator = jsonschema.Draft202012Validator(schema)
        return [
            f"{list(error.absolute_path)}: {error.message}" for error in validator.iter_errors(parsed)
        ][:25]
    except ImportError:
        required = schema.get("required", []) if isinstance(schema, dict) else []
        missing = [key for key in required if key not in parsed]
        return [f"required key missing: {key}" for key in missing]
