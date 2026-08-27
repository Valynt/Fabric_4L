"""Frozen CARGO-EVAL-001 slug sets.

APPROVED_SLUGS is the compile-time list. load_allowlist() is the machine
document tests compare against. Do not import allowlist.json at module
import time from a packaged service path.
"""

from __future__ import annotations

import json
from pathlib import Path

APPROVED_SLUGS: tuple[str, ...] = (
    "cargo_match_business",
    "cargo_fetch_businesses",
    "cargo_enrich_firmographics",
    "cargo_enrich_technographics",
    "cargo_funding_events",
    "cargo_workforce_headcount",
    "cargo_website_changes",
    "cargo_competitive_mentions",
    "cargo_match_prospect",
)

HELD_SLUGS: tuple[str, ...] = (
    "cargo_email_waterfall",
    "cargo_phone_waterfall",
    "cargo_salesnav_lead_search",
    "cargo_linkedin_profile_enrichment",
    "cargo_workforce_narrative",
    "cargo_context_agent",
    "cargo_native_library_rag",
    "cargo_crm_writeback",
)

OUT_SLUGS: tuple[str, ...] = (
    "cargo_roi",
    "cargo_savings",
    "cargo_valuepack_recommend",
    "cargo_hypothesis_recommend",
    "cargo_strategic_insights",
    "cargo_workforce_ratings",
)


def find_allowlist_path() -> Path:
    here = Path(__file__).resolve()
    for parent in [here.parent, *here.parents]:
        candidate = parent / "docs" / "cargo" / "allowlist.json"
        if candidate.is_file():
            return candidate
    raise FileNotFoundError("docs/cargo/allowlist.json not found from slugs.py")


def load_allowlist() -> dict:
    return json.loads(find_allowlist_path().read_text(encoding="utf-8"))


def is_approved_slug(slug: str) -> bool:
    return slug in APPROVED_SLUGS
