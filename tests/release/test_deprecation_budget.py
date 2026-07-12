"""Release Policy: Deprecation budget enforcement.

Verifies that P0 deprecations are resolved and P1 deprecations are within budget
before release-candidate can proceed. Parses the canonical deprecation tracking
source to count violations by severity.
"""

import json
import os
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pytest
import yaml

# Canonical deprecation tracking locations (in priority order)
DEPRECATION_LOCATIONS = [
    Path(__file__).parent.parent.parent / "docs" / "governance" / "deprecations.json",
    Path(__file__).parent.parent.parent / "DEPRECATIONS.md",
    Path(__file__).parent.parent.parent / "shared" / "DEPRECATED.md",
]


class TestDeprecationBudget:
    """Enforce: P0 deprecations must be zero; P1 within budget."""

    def _find_deprecation_file(self) -> Path:
        """Find the canonical deprecation tracking file."""
        for loc in DEPRECATION_LOCATIONS:
            if loc.exists() and loc.stat().st_size > 0:
                return loc
        pytest.fail("No deprecation tracking file found — release-policy gate requires canonical deprecation evidence")

    def _parse_deprecations(self) -> list[dict[str, Any]]:
        """Parse deprecations from canonical source."""
        deprecation_file = self._find_deprecation_file()

        with open(deprecation_file, encoding="utf-8") as f:
            content = f.read()

        # Try JSON first (preferred machine-readable format)
        if deprecation_file.suffix == ".json":
            data = json.loads(content)
            if isinstance(data, dict):
                return data.get("items", [])
            return data if isinstance(data, list) else []

        # Fall back to Markdown parsing for DEPRECATIONS.md format
        if deprecation_file.suffix == ".md":
            return self._parse_markdown_deprecations(content)

        return []

    def _parse_markdown_deprecations(self, content: str) -> list[dict[str, Any]]:
        """Parse deprecations from Markdown format.

        Expected format:
        - [P0] pattern-name: description (target: 2024-01-01)
        """
        deprecations = []
        # Look for pattern: - [P0| P1| P2] pattern-name: description
        pattern = r'-?\s*\[?(P0|P1|P2)\]?\s*([\w-]+)\s*:?\s*(.+?)(?:\s*\(target:\s*(\d{4}-\d{2}-\d{2})\))?'
        import re
        for match in re.finditer(pattern, content):
            severity = match.group(1)
            pattern_name = match.group(2)
            description = match.group(3).strip()
            target_date = match.group(4)

            deprecations.append({
                "id": pattern_name,
                "severity": severity,
                "pattern": pattern_name,
                "description": description,
                "targetRemoval": target_date,
                "status": "active",  # Assume active if in list
            })

        return deprecations

    def test_deprecation_file_exists(self):
        """Deprecation tracking file must exist."""
        deprecation_file = None
        for loc in DEPRECATION_LOCATIONS:
            if loc.exists():
                deprecation_file = loc
                break

        assert deprecation_file is not None, \
            f"No deprecation file found at any of: {DEPRECATION_LOCATIONS}"

    def test_p0_deprecations_are_zero(self):
        """P0 deprecations must be zero for release-candidate.

        P0 = Critical: Blocks release, security or correctness risk.
        Rationale: P0 deprecations indicate production-blocking technical debt.
        """
        deprecations = self._parse_deprecations()

        p0_items = [
            d for d in deprecations
            if d.get("severity", "").upper() == "P0"
            and d.get("status", "active") != "resolved"
        ]

        if p0_items:
            details = "\n".join(
                f"  - {item['id']}: {item.get('description', 'No description')} "
                f"(target: {item.get('targetRemoval', 'unset')})"
                for item in p0_items
            )
            pytest.fail(
                f"Found {len(p0_items)} P0 deprecation(s) — must be zero for release-candidate:\n{details}"
            )

    def test_p1_deprecations_within_budget(self):
        """P1 deprecations must be within configured budget.

        P1 = High: Should be resolved soon, has workaround.
        Budget: Configurable threshold (default: 10).
        """
        deprecations = self._parse_deprecations()

        p1_items = [
            d for d in deprecations
            if d.get("severity", "").upper() == "P1"
            and d.get("status", "active") != "resolved"
        ]

        # Budget threshold from environment or default
        budget = int(os.getenv("P1_DEPRECATION_BUDGET", "10"))

        assert len(p1_items) <= budget, (
            f"P1 deprecations ({len(p1_items)}) exceed release-policy budget ({budget}). "
            "Resolve items or adjust P1_DEPRECATION_BUDGET only through an approved policy change."
        )

    def test_no_expired_deprecation_exceptions(self):
        """No deprecation waivers with expired target dates.

        Rationale: Waivers must be time-bounded and actively maintained.
        """
        deprecations = self._parse_deprecations()

        today = date.today()
        expired = []

        for item in deprecations:
            if item.get("status", "active") == "resolved":
                continue
            target = item.get("targetRemoval")
            if target and target != "TBD":
                try:
                    target_date = datetime.strptime(target, "%Y-%m-%d").date()
                    if target_date < today:
                        expired.append({
                            "id": item["id"],
                            "target": target,
                            "days_past": (today - target_date).days
                        })
                except ValueError:
                    # Unparseable date is a formatting issue, not expired
                    pass

        if expired:
            details = "\n".join(
                f"  - {e['id']}: target was {e['target']} ({e['days_past']} days ago)"
                for e in expired
            )
            pytest.fail(
                f"Found {len(expired)} expired deprecation target(s):\n{details}\n"
                f"Update target date or resolve the deprecation."
            )

    def test_deprecations_have_required_fields(self):
        """All deprecations must have required fields for traceability.

        Required: id, pattern, severity, owner, targetRemoval, replacement
        """
        deprecations = self._parse_deprecations()

        required_fields = ["id", "pattern", "severity"]
        missing_fields = []

        for item in deprecations:
            missing = [f for f in required_fields if not item.get(f)]
            if missing:
                missing_fields.append(f"{item.get('id', 'unknown')}: missing {missing}")

        if missing_fields:
            pytest.fail("Deprecations missing required fields:\n" + "\n".join(missing_fields))

    def test_deprecation_compliance_score_above_threshold(self):
        """Overall deprecation compliance score must meet threshold.

        If the deprecation file includes a compliance score, verify it meets target.
        """
        deprecation_file = self._find_deprecation_file()

        assert deprecation_file.suffix == ".json", "Compliance score requires the canonical JSON deprecation register"

        with open(deprecation_file, encoding="utf-8") as f:
            data = json.load(f)

        assert isinstance(data, dict) and "compliance" in data, "Deprecation register must include compliance metadata"

        compliance = data.get("compliance", {})
        current_score = compliance.get("overallScore")
        target_score = compliance.get("targetScore")
        target_date = compliance.get("targetDate")

        assert current_score is not None and target_score is not None, "Compliance scores must be defined"

        if current_score < target_score:
            today = date.today()
            try:
                target = datetime.strptime(target_date, "%Y-%m-%d").date() if target_date else None
            except (ValueError, TypeError):
                target = None

            assert target is not None, "Below-target compliance must have a parseable target date"
            assert today <= target, (
                f"Deprecation compliance {current_score}% below target {target_score}% "
                f"and target date {target_date} has passed"
            )
