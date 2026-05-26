"""Contract tests for Layer 3 entity-resolution explanation payload."""

from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft7Validator


CONTRACT_PATH = Path("contracts/jsonschema/layer3-entity-resolution-contract.json")


def _load_contract() -> dict:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def test_entity_resolution_contract_requires_explanation_fields():
    schema = _load_contract()
    required = set(schema["required"])
    assert {
        "canonical_entity_id",
        "confidence",
        "tie_break_rule",
        "source_evidence_ids",
        "reasoning_trace_keys",
    }.issubset(required)


def test_entity_resolution_contract_accepts_explicit_explanation_payload():
    schema = _load_contract()
    payload = {
        "canonical_entity_id": "entity-123",
        "confidence": 0.94,
        "tie_break_rule": "highest_confidence",
        "source_evidence_ids": ["entity-123", "entity-999"],
        "reasoning_trace_keys": [
            "candidate_retrieval",
            "candidate_scoring",
            "deterministic_ordering",
            "tie_break_resolution",
        ],
    }
    validator = Draft7Validator(schema)
    errors = sorted(validator.iter_errors(payload), key=lambda e: e.path)
    assert errors == []
