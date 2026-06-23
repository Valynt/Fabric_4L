#!/usr/bin/env python3
"""Validate the production-readiness scorecard documentation."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
READINESS_DIR = ROOT / "production-readiness"

REQUIRED_FILES = (
    "README.md",
    "scorecard.md",
    "launch_checklist.md",
    "ownership_matrix.md",
    "risk_register.md",
)

REQUIRED_AREAS = {
    "security",
    "reliability",
    "observability",
    "dr",
    "release safety",
    "billing",
    "tenancy",
    "data lifecycle",
    "compliance evidence",
}

REQUIRED_SCORECARD_COLUMNS = {
    "area",
    "owner",
    "status",
    "risk",
    "validation command",
    "launch blocker",
    "ci artifact",
}

ALLOWED_STATUSES = {"PASS", "CONDITIONAL", "BLOCKED", "NOT_STARTED"}


def _read(relative: str) -> str:
    return (READINESS_DIR / relative).read_text(encoding="utf-8")


def _table_rows(markdown: str) -> list[list[str]]:
    rows: list[list[str]] = []
    for line in markdown.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or not stripped.endswith("|"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if cells and all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells):
            continue
        rows.append(cells)
    return rows


def _scorecard_records(markdown: str) -> tuple[list[str], list[dict[str, str]]]:
    rows = _table_rows(markdown)
    if not rows:
        return [], []
    header = [cell.lower() for cell in rows[0]]
    records = [dict(zip(header, row, strict=False)) for row in rows[1:]]
    return header, records


def validate_files() -> list[str]:
    errors: list[str] = []
    for file_name in REQUIRED_FILES:
        path = READINESS_DIR / file_name
        if not path.exists():
            errors.append(f"missing required file: production-readiness/{file_name}")
        elif not path.read_text(encoding="utf-8").strip():
            errors.append(f"required file is empty: production-readiness/{file_name}")
    return errors


def validate_scorecard() -> list[str]:
    errors: list[str] = []
    scorecard = _read("scorecard.md")
    header, records = _scorecard_records(scorecard)
    missing_columns = REQUIRED_SCORECARD_COLUMNS - set(header)
    if missing_columns:
        errors.append(f"scorecard table missing columns: {sorted(missing_columns)}")
        return errors

    rows_by_area = {record.get("area", "").strip().lower(): record for record in records}
    missing_areas = REQUIRED_AREAS - set(rows_by_area)
    if missing_areas:
        errors.append(f"scorecard missing required areas: {sorted(missing_areas)}")

    for area in sorted(REQUIRED_AREAS & set(rows_by_area)):
        row = rows_by_area[area]
        for column in ("owner", "status", "risk", "validation command"):
            value = row.get(column, "").strip()
            if not value or value == "-":
                errors.append(f"{area}: missing {column}")
        status = row.get("status", "").strip()
        if status not in ALLOWED_STATUSES:
            errors.append(f"{area}: invalid status {status!r}")
        ci_artifact = row.get("ci artifact", "")
        if ".github/workflows/" not in ci_artifact or "artifact" not in ci_artifact.lower():
            errors.append(f"{area}: CI artifact must link to a workflow artifact")

    for marker in ("[BLOCKER:P0]", "[BLOCKER:P1]"):
        if marker not in scorecard:
            errors.append(f"scorecard must clearly mark {marker} launch blockers")

    return errors


def validate_launch_gate() -> list[str]:
    errors: list[str] = []
    checklist = _read("launch_checklist.md").lower()
    if "production launch requires scorecard review" not in checklist:
        errors.append("launch checklist must state that production launch requires scorecard review")
    if "ticket comments" not in checklist or "isolated ci logs" not in checklist:
        errors.append("launch checklist must reject informal launch approval sources")
    return errors


def validate_risk_register() -> list[str]:
    errors: list[str] = []
    risk_register = _read("risk_register.md")
    for marker in ("[BLOCKER:P0]", "[BLOCKER:P1]"):
        if marker not in risk_register:
            errors.append(f"risk register must include {marker} entries")
    for area in REQUIRED_AREAS:
        if area not in risk_register.lower():
            errors.append(f"risk register missing area: {area}")
    return errors


def validate_ownership_matrix() -> list[str]:
    errors: list[str] = []
    matrix = _read("ownership_matrix.md").lower()
    for area in REQUIRED_AREAS:
        if area not in matrix:
            errors.append(f"ownership matrix missing area: {area}")
    if "validation command" not in matrix:
        errors.append("ownership matrix must include validation commands")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--scorecard-only",
        action="store_true",
        help="Validate only the production-readiness markdown scorecard set.",
    )
    parser.parse_args(argv)

    errors = []
    errors.extend(validate_files())
    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1

    errors.extend(validate_scorecard())
    errors.extend(validate_launch_gate())
    errors.extend(validate_risk_register())
    errors.extend(validate_ownership_matrix())

    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1

    print("PASS: production-readiness scorecard documentation is complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
