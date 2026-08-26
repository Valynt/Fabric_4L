from pathlib import Path
import json
from typing import List

ALLOWLIST_PATH = Path("docs/cargo/allowlist.json")

def load_green_slugs() -> List[str]:
    """Machine source of truth for CARGO-EVAL-001 green list.
    Charter test asserts only these are used.
    """
    data = json.loads(ALLOWLIST_PATH.read_text())
    return data.get("green", [])

GREEN_SLUGS = load_green_slugs()

# Frozen per signed charter
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
}, "allowlist.json must match signed charter"
