"""CARGO-EVAL-001 charter freeze.

Static contract: charter and allowlist.json agree, only green slugs are
approved, L1 does not emit Observations, Context Agent is out, and the
charter is not treated as signed until humans sign it.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

pytestmark = [pytest.mark.contract_static, pytest.mark.unit]

REPO_ROOT = Path(__file__).resolve().parents[2]
CHARTER_PATH = REPO_ROOT / "docs" / "cargo" / "eval-charter-001.md"
ALLOWLIST_PATH = REPO_ROOT / "docs" / "cargo" / "allowlist.json"
PORT_PATH = (
    REPO_ROOT
    / "services"
    / "layer1-ingestion"
    / "src"
    / "layer1_ingestion"
    / "providers"
    / "account_intelligence"
    / "port.py"
)
MODELS_PATH = PORT_PATH.with_name("models.py")

APPROVED = [
    "cargo_match_business",
    "cargo_fetch_businesses",
    "cargo_enrich_firmographics",
    "cargo_enrich_technographics",
    "cargo_funding_events",
    "cargo_workforce_headcount",
    "cargo_website_changes",
    "cargo_competitive_mentions",
    "cargo_match_prospect",
]

HELD = [
    "cargo_email_waterfall",
    "cargo_phone_waterfall",
    "cargo_salesnav_lead_search",
    "cargo_linkedin_profile_enrichment",
    "cargo_workforce_narrative",
    "cargo_context_agent",
    "cargo_native_library_rag",
    "cargo_crm_writeback",
]

OUT = [
    "cargo_roi",
    "cargo_savings",
    "cargo_valuepack_recommend",
    "cargo_hypothesis_recommend",
    "cargo_strategic_insights",
    "cargo_workforce_ratings",
]


def _allowlist() -> dict:
    assert ALLOWLIST_PATH.is_file(), f"missing allowlist: {ALLOWLIST_PATH}"
    return json.loads(ALLOWLIST_PATH.read_text(encoding="utf-8"))


def _charter() -> str:
    assert CHARTER_PATH.is_file(), f"missing charter: {CHARTER_PATH}"
    return CHARTER_PATH.read_text(encoding="utf-8")


def test_allowlist_matches_frozen_green_list() -> None:
    data = _allowlist()
    assert data["approved_slugs"] == APPROVED
    assert data["held_slugs"] == HELD
    assert data["out_slugs"] == OUT
    assert data["l1_emits"] == "RawSnapshot"
    assert data["l2_emits"] == "Observation"
    assert data["value_driver_tags_on_ingest"] == []
    assert data["context_agent_permitted"] is False
    assert data["status"] == "draft_pending_signatures"


def test_allowlist_sets_have_no_overlap() -> None:
    data = _allowlist()
    approved = set(data["approved_slugs"])
    held = set(data["held_slugs"])
    out = set(data["out_slugs"])
    assert approved.isdisjoint(held)
    assert approved.isdisjoint(out)
    assert held.isdisjoint(out)


def test_charter_references_every_approved_slug() -> None:
    text = _charter()
    missing = [slug for slug in APPROVED if slug not in text]
    assert missing == [], f"charter missing approved slugs: {missing}"


def test_charter_does_not_approve_held_or_out_slugs() -> None:
    text = _charter()
    section = text.split("## 3. Approved slugs (green)", 1)[1].split("## 4. Held", 1)[0]
    leaked = [slug for slug in HELD + OUT if slug in section]
    assert leaked == [], f"held/out slugs listed as approved: {leaked}"


def test_charter_has_at_least_twelve_named_paired_tasks() -> None:
    text = _charter()
    task_ids = re.findall(r"\| T(\d{2}) \|", text)
    assert len(task_ids) >= 12, f"found {len(task_ids)} paired tasks, need >= 12"


def test_charter_is_not_claimed_signed() -> None:
    text = _charter()
    assert "pending Product, Platform, and Security signatures" in text
    assert "Not in force" in text
    assert "Charter signed." not in text


def test_l1_does_not_emit_observation() -> None:
    text = _charter()
    assert "RawSnapshot" in text
    assert "L1 must not emit `Observation`" in text
    port = PORT_PATH.read_text(encoding="utf-8")
    models = MODELS_PATH.read_text(encoding="utf-8")
    assert "class Observation" not in port
    assert "class Observation" not in models
    assert "EnrichedAccountContext" not in models
    assert "CargoMcpRequest" not in models
    assert "valueDriverTags" not in models
    assert "raw_payload_ref" in models


def test_value_driver_tags_empty_on_ingest() -> None:
    assert _allowlist()["value_driver_tags_on_ingest"] == []


def test_context_agent_excluded() -> None:
    text = _charter().lower()
    assert "context agent" in text
    assert "excluded" in text
    assert _allowlist()["context_agent_permitted"] is False


def test_strategic_insights_not_in_approved_slugs() -> None:
    data = _allowlist()
    assert "cargo_strategic_insights" not in data["approved_slugs"]
    assert "cargo_strategic_insights" in data["out_slugs"]
