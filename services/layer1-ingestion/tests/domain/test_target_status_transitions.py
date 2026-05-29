"""Domain tests for the target status transition table.

Tests the _ALLOWED_STATUS_TRANSITIONS dict in app_monolith directly,
plus parametrized API coverage of every cell in the transition matrix.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Ensure src is importable
_src = str(Path(__file__).resolve().parents[2] / "src")
if _src not in sys.path:
    sys.path.insert(0, _src)


# ---------------------------------------------------------------------------
# Unit tests on the transition table itself (no HTTP, no DB)
# ---------------------------------------------------------------------------

class TestTransitionTableStructure:
    def test_table_is_importable(self):
        from layer1_ingestion.api.app_monolith import _ALLOWED_STATUS_TRANSITIONS
        assert isinstance(_ALLOWED_STATUS_TRANSITIONS, dict)

    def test_all_known_statuses_have_entries(self):
        from layer1_ingestion.api.app_monolith import _ALLOWED_STATUS_TRANSITIONS
        known = {"ACTIVE", "PAUSED", "ERROR", "ARCHIVED"}
        assert known == set(_ALLOWED_STATUS_TRANSITIONS.keys())

    def test_archived_has_no_outgoing_transitions(self):
        from layer1_ingestion.api.app_monolith import _ALLOWED_STATUS_TRANSITIONS
        assert _ALLOWED_STATUS_TRANSITIONS["ARCHIVED"] == set()

    def test_table_values_are_sets_of_strings(self):
        from layer1_ingestion.api.app_monolith import _ALLOWED_STATUS_TRANSITIONS
        for from_status, allowed in _ALLOWED_STATUS_TRANSITIONS.items():
            assert isinstance(allowed, set), f"{from_status} value is not a set"
            for to_status in allowed:
                assert isinstance(to_status, str), f"Transition target {to_status!r} is not a string"

    def test_table_does_not_allow_unknown_statuses(self):
        from layer1_ingestion.api.app_monolith import _ALLOWED_STATUS_TRANSITIONS
        known = {"ACTIVE", "PAUSED", "ERROR", "ARCHIVED"}
        for from_status, allowed in _ALLOWED_STATUS_TRANSITIONS.items():
            unknown = allowed - known
            assert not unknown, f"Unknown target statuses in transitions from {from_status}: {unknown}"

    def test_active_allows_paused_and_archived(self):
        from layer1_ingestion.api.app_monolith import _ALLOWED_STATUS_TRANSITIONS
        assert "PAUSED" in _ALLOWED_STATUS_TRANSITIONS["ACTIVE"]
        assert "ARCHIVED" in _ALLOWED_STATUS_TRANSITIONS["ACTIVE"]

    def test_paused_allows_active_and_archived(self):
        from layer1_ingestion.api.app_monolith import _ALLOWED_STATUS_TRANSITIONS
        assert "ACTIVE" in _ALLOWED_STATUS_TRANSITIONS["PAUSED"]
        assert "ARCHIVED" in _ALLOWED_STATUS_TRANSITIONS["PAUSED"]

    def test_error_allows_active_paused_archived(self):
        from layer1_ingestion.api.app_monolith import _ALLOWED_STATUS_TRANSITIONS
        assert "ACTIVE" in _ALLOWED_STATUS_TRANSITIONS["ERROR"]
        assert "PAUSED" in _ALLOWED_STATUS_TRANSITIONS["ERROR"]
        assert "ARCHIVED" in _ALLOWED_STATUS_TRANSITIONS["ERROR"]


# ---------------------------------------------------------------------------
# Parametrized transition matrix — API level
# Uses the conftest fixtures from tests/api/conftest.py via sys.path trick.
# ---------------------------------------------------------------------------

# Import conftest fixtures by adding the api dir to path so pytest can find them.
# (pytest collects conftest.py automatically when tests are in the same package.)

@pytest.mark.parametrize(
    ("from_status", "to_status", "expected_code"),
    [
        # Allowed
        ("ACTIVE",   "PAUSED",    200),
        ("ACTIVE",   "ARCHIVED",  200),
        ("PAUSED",   "ACTIVE",    200),
        ("PAUSED",   "ARCHIVED",  200),
        ("ERROR",    "ACTIVE",    200),
        ("ERROR",    "PAUSED",    200),
        ("ERROR",    "ARCHIVED",  200),
        # Disallowed — ARCHIVED is terminal
        ("ARCHIVED", "ACTIVE",    422),
        ("ARCHIVED", "PAUSED",    422),
        ("ARCHIVED", "ERROR",     422),
        # Disallowed — same-status self-transitions
        ("ACTIVE",   "ACTIVE",    422),
        ("PAUSED",   "PAUSED",    422),
    ],
)
def test_transition_matrix(from_status, to_status, expected_code, client, db, org_id, make_target):
    """Every cell in the transition matrix has a passing test."""
    t = make_target(org_id, status=from_status)
    resp = client.patch(
        f"/api/v1/ingestion/targets/{t.id}/status",
        json={"status": to_status},
    )
    assert resp.status_code == expected_code, (
        f"Transition {from_status} -> {to_status}: "
        f"expected {expected_code}, got {resp.status_code}. Body: {resp.text}"
    )


def test_transition_failure_message_is_safe(client, db, org_id, make_target):
    """Error message on invalid transition must not expose tenant or DB details."""
    t = make_target(org_id, status="ARCHIVED")
    resp = client.patch(
        f"/api/v1/ingestion/targets/{t.id}/status",
        json={"status": "ACTIVE"},
    )
    assert resp.status_code == 422
    detail = resp.json().get("detail", "")
    assert str(org_id) not in detail
    assert "sql" not in detail.lower()
    assert "traceback" not in detail.lower()
