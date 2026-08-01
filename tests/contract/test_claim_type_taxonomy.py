"""Contract guard: canonical claim taxonomy for the L4 -> L5 boundary.

Layer 5 owns the claim taxonomy (``layer5_ground_truth.models.truth_object.ClaimType``).
Layer 4 consumes it via ``layer4_agents.integration.claim_types`` and the
published contract ``contracts/jsonschema/claim-types.v1.json``. These tests
fail when any of the three drifts from the others.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = [pytest.mark.contract_static, pytest.mark.unit]

CONTRACT_PATH = (
    Path(__file__).resolve().parents[2] / "contracts" / "jsonschema" / "claim-types.v1.json"
)


def _contract() -> dict:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def _l5_values() -> set[str]:
    from layer5_ground_truth.models.truth_object import ClaimType

    return {member.value for member in ClaimType}


def _l4_module():
    from layer4_agents.integration import claim_types

    return claim_types


def test_contract_enum_matches_layer5_authority() -> None:
    contract_values = set(_contract()["properties"]["claim_type"]["enum"])
    assert contract_values == _l5_values(), (
        "claim-types.v1.json enum drifted from Layer 5 ClaimType"
    )


def test_layer4_canonical_set_matches_layer5_authority() -> None:
    claim_types = _l4_module()
    assert set(claim_types.CANONICAL_CLAIM_TYPES) == _l5_values(), (
        "Layer 4 CANONICAL_CLAIM_TYPES drifted from Layer 5 ClaimType"
    )


def test_layer4_mapping_values_are_canonical() -> None:
    claim_types = _l4_module()
    for legacy, canonical in claim_types.LAYER4_TO_LAYER5_CLAIM_TYPE.items():
        assert canonical in claim_types.CANONICAL_CLAIM_TYPES, (
            f"Layer 4 claim mapping {legacy!r} -> {canonical!r} is not canonical"
        )


def test_layer4_mapping_matches_published_contract() -> None:
    claim_types = _l4_module()
    contract_mapping = _contract()["properties"]["layer4_vocabulary_mapping"]["properties"]
    published = {key: value["const"] for key, value in contract_mapping.items()}
    assert published == claim_types.LAYER4_TO_LAYER5_CLAIM_TYPE, (
        "Layer 4 mapping drifted from claim-types.v1.json"
    )


def test_to_layer5_claim_type_maps_and_rejects() -> None:
    claim_types = _l4_module()
    for legacy, canonical in claim_types.LAYER4_TO_LAYER5_CLAIM_TYPE.items():
        assert claim_types.to_layer5_claim_type(legacy) == canonical
    with pytest.raises(ValueError):
        claim_types.to_layer5_claim_type("not-a-real-type")


def test_require_canonical_claim_type_accepts_authority_values() -> None:
    claim_types = _l4_module()
    for value in _l5_values():
        assert claim_types.require_canonical_claim_type(value) == value
    with pytest.raises(ValueError):
        claim_types.require_canonical_claim_type("capability")
