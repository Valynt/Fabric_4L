import json
from pathlib import Path

ALLOWLIST_PATH = Path(__file__).parent.parent.parent.parent.parent.parent / "docs" / "cargo" / "allowlist.json"

def load_green_slugs() -> list[str]:
    """Machine source of truth for CARGO-EVAL-001 green list.
    Charter test asserts only these are used.
    """
    data = json.loads(ALLOWLIST_PATH.read_text())
    # Support both legacy "green" and new charter schema
    return data.get("approved_slugs") or data.get("green", [])

GREEN_SLUGS = load_green_slugs()

# Frozen per signed charter (CARGO-EVAL-001)
assert set(GREEN_SLUGS) == {
    "cargo_match_business",
    "cargo_fetch_businesses",
    "cargo_enrich_firmographics",
    "cargo_enrich_technographics",
    "cargo_funding_events",
    "cargo_workforce_headcount",
    "cargo_website_changes",
    "cargo_competitive_mentions",
    "cargo_match_prospect",
}, "allowlist.json must match signed charter (eval-charter-001.md)"
