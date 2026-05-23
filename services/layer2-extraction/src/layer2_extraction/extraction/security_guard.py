"""Security guardrails for L2 extraction LLM interactions.

This module provides:
1. Preprocessing of source content before LLM invocation.
2. Policy gate treating LLM output as untrusted data.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

CONTENT_DELIMITER_START = "<<<SOURCE_CONTENT_BEGIN>>>"
CONTENT_DELIMITER_END = "<<<SOURCE_CONTENT_END>>>"

_SUSPICIOUS_INSTRUCTION_PATTERNS = (
    re.compile(r"ignore\s+(all\s+)?previous\s+instructions", re.IGNORECASE),
    re.compile(r"system\s+prompt", re.IGNORECASE),
    re.compile(r"developer\s+message", re.IGNORECASE),
    re.compile(r"<\s*/?\s*thinking\s*>", re.IGNORECASE),
    re.compile(r"\btool\s*call\b", re.IGNORECASE),
)

_HIGH_RISK_TOKEN_PATTERNS = (
    re.compile(r"\b(rm\s+-rf|sudo|chmod\s+777|curl\s+.+\|\s*sh)\b", re.IGNORECASE),
    re.compile(r"\b(drop\s+table|truncate\s+table|alter\s+table)\b", re.IGNORECASE),
    re.compile(r"\b(exec\(|system\(|subprocess\.|os\.system)\b", re.IGNORECASE),
)


@dataclass(frozen=True)
class PreprocessedContent:
    """Structured result from content preprocessing."""

    delimited_content: str
    suspicious_instruction_hits: tuple[str, ...]
    high_risk_token_hits: tuple[str, ...]


def _find_pattern_hits(text: str, patterns: Iterable[re.Pattern[str]]) -> tuple[str, ...]:
    hits: list[str] = []
    for pattern in patterns:
        if pattern.search(text):
            hits.append(pattern.pattern)
    return tuple(hits)


def preprocess_source_content(content: str) -> PreprocessedContent:
    """Delimiter and screen source content before prompt assembly."""
    suspicious_hits = _find_pattern_hits(content, _SUSPICIOUS_INSTRUCTION_PATTERNS)
    high_risk_hits = _find_pattern_hits(content, _HIGH_RISK_TOKEN_PATTERNS)
    delimited = f"{CONTENT_DELIMITER_START}\n{content}\n{CONTENT_DELIMITER_END}"
    return PreprocessedContent(
        delimited_content=delimited,
        suspicious_instruction_hits=suspicious_hits,
        high_risk_token_hits=high_risk_hits,
    )


class UntrustedLLMOutputPolicyError(ValueError):
    """Raised when untrusted LLM output attempts privileged instructions."""


def enforce_untrusted_output_policy(items: Iterable[object]) -> None:
    """Reject LLM output containing privileged side-effect instructions.

    L2 extraction is data-only. Any instruction-like output that appears to
    request privileged operations must be blocked until deterministic,
    server-side authorization/validation logic explicitly allows it.
    """
    blocked_terms = (
        "grant_admin",
        "delete_tenant",
        "rotate_api_key",
        "run_shell",
        "execute_sql",
        "bypass_auth",
    )

    for item in items:
        content = str(getattr(item, "description", "")) + " " + str(item)
        normalized = content.lower()
        if any(term in normalized for term in blocked_terms):
            raise UntrustedLLMOutputPolicyError(
                "LLM output contained potential privileged side-effect instructions; "
                "blocked by untrusted-output policy gate."
            )
