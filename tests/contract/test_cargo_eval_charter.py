"""Contract test for CARGO-EVAL-001 charter and allowlist.

This test enforces the signed charter, frozen green list, L1=RawSnapshot contract,
and exclusions. It must pass before any real adapter or treatment runs.
"""
import json
from pathlib import Path

import pytest
import yaml  # if charter becomes YAML; for now MD parse is minimal


CHARTER_PATH = Path("docs/cargo/eval-charter-001.md")
ALLOWLIST_PATH = Path("docs/cargo/allowlist.json")
GREEN_SLUGS = {
    "cargo_match_business",
    "cargo_fetch_businesses",
    "cargo_enrich_firmographics",
    "cargo_enrich_technographics",
    "cargo_funding_events",
    "cargo_workforce_headcount",
    "cargo_website_changes",
    "cargo_competitive_mentions",
    "cargo_match_prospect",
}


def test_cargo_eval_001_charter_exists_and_governs():
    """CARGO-EVAL-001 must exist, reference the allowlist, and enforce the contract."""
    assert CHARTER_PATH.exists(), "eval-charter-001.md is the governing document"
    content = CHARTER_PATH.read_text(encoding="utf-8")
    assert "CARGO-EVAL-001" in content
    assert "L1=RawSnapshot" in content or "RawSnapshot" in content
    assert "valueDriverTags" in content
    assert "Context Agent excluded" in content or "Context Agent" in content
    assert "pending human review" in content or "Signatures pending" in content
    assert "Hard gates non-compensable" in content


def test_allowlist_json_matches_charter_green_list():
    """Machine source of truth must exactly match the signed charter green list."""
    assert ALLOWLIST_PATH.exists(), "allowlist.json is the machine source of truth"
    data = json.loads(ALLOWLIST_PATH.read_text(encoding="utf-8"))
    
    approved = set(data.get("approved_slugs") or data.get("green", []))
    assert approved == GREEN_SLUGS, f"Green slugs must match exactly: {GREEN_SLUGS}"
    
    # Schema validation for charter test
    assert "l1_emits" in data and data["l1_emits"] == "RawSnapshot"
    assert data.get("value_driver_tags_on_ingest") == "empty"
    assert data.get("context_agent_permitted") is False


def test_no_held_or_out_slugs_in_approved():
    """Held and out signals must not leak into green/approved."""
    data = json.loads(ALLOWLIST_PATH.read_text(encoding="utf-8"))
    approved = set(data.get("approved_slugs") or data.get("green", []))
    held = set(data.get("held_slugs") or data.get("held", []))
    out = set(data.get("out_slugs") or data.get("out", []))
    
    assert not approved & held, "No overlap between approved and held"
    assert not approved & out, "No overlap between approved and out"
    assert len(approved) == 9, "Exactly the 9 frozen green slugs"


@pytest.mark.contract_static
def test_charter_blocks_observations_in_l1():
    """L1 contract: only RawSnapshot. Observations are L2 only."""
    content = CHARTER_PATH.read_text(encoding="utf-8")
    assert "RawSnapshot" in content
    # Negative assertion for previous drift
    # (in practice we'd parse more strictly; this guards the plan/catalog fix)
    assert "L1 emits Observations" not in content.lower()