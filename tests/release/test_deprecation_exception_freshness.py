"""Release Policy: Deprecation exception waivers must not be stale.

Parses the canonical deprecation register and asserts that no active exception
waiver has an expirationDate in the past.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pytest

DEPRECATIONS_JSON = Path(__file__).parent.parent.parent / "docs" / "governance" / "deprecations.json"


def _load_deprecations() -> dict[str, Any]:
    assert DEPRECATIONS_JSON.exists(), f"Canonical deprecation register not found: {DEPRECATIONS_JSON}"
    return json.loads(DEPRECATIONS_JSON.read_text(encoding="utf-8"))


def _expired_entries(entries: list[dict[str, Any]], date_field: str) -> list[dict[str, Any]]:
    today = date.today()
    expired: list[dict[str, Any]] = []
    for entry in entries:
        status = entry.get("status", "active")
        if status in {"resolved", "removed", "exception"}:
            # "exception" waivers are active until their expirationDate passes.
            if status != "exception":
                continue
        raw_date = entry.get(date_field)
        if not raw_date:
            continue
        try:
            entry_date = datetime.strptime(raw_date, "%Y-%m-%d").date()
        except ValueError:
            continue
        if entry_date < today:
            expired.append(
                {
                    "id": entry.get("id", "unknown"),
                    "date": raw_date,
                    "days_past": (today - entry_date).days,
                }
            )
    return expired


def test_no_expired_deprecation_items() -> None:
    """Canonical deprecation items must not have passed targetRemoval dates."""
    data = _load_deprecations()
    expired = _expired_entries(data.get("items", []), "targetRemoval")
    if expired:
        details = "\n".join(
            f"  - {e['id']}: target was {e['date']} ({e['days_past']} days ago)"
            for e in expired
        )
        pytest.fail(f"Found {len(expired)} expired deprecation item target(s):\n{details}")


def test_no_expired_deprecation_exceptions() -> None:
    """Canonical deprecation exception waivers must not have passed expirationDate."""
    data = _load_deprecations()
    expired = _expired_entries(data.get("exceptions", []), "expirationDate")
    if expired:
        details = "\n".join(
            f"  - {e['id']}: exception expired {e['date']} ({e['days_past']} days ago)"
            for e in expired
        )
        pytest.fail(f"Found {len(expired)} expired deprecation exception waiver(s):\n{details}")
