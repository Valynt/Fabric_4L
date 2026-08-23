"""PII detection and redaction service for Layer 2 extraction pipeline."""

from __future__ import annotations

import re
from typing import Literal

PiiType = Literal["email", "phone", "ssn", "credit_card", "address"]

_PII_PATTERNS: dict[PiiType, re.Pattern] = {
    "email": re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
    "phone": re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "credit_card": re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b"),
    "address": re.compile(
        r"\d+\s+\w+\s+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Court|Ct)"
    ),
}


def detect_pii(text: str) -> list[dict]:
    """Scan text for PII patterns and return matches with type and position."""
    findings: list[dict] = []
    for pii_type, pattern in _PII_PATTERNS.items():
        for match in pattern.finditer(text):
            findings.append(
                {
                    "type": pii_type,
                    "start": match.start(),
                    "end": match.end(),
                    "value": match.group(),
                }
            )
    return findings


def pii_summary(text: str) -> dict:
    """Return a summary of PII findings for ingestion job UI."""
    findings = detect_pii(text)
    counts: dict[str, int] = {}
    for f in findings:
        counts[f["type"]] = counts.get(f["type"], 0) + 1
    return {
        "has_pii": len(findings) > 0,
        "total_findings": len(findings),
        "counts": counts,
        "findings": findings,
    }
