"""Release gate for DEPRECATION_MAP overdue item resolution."""

from __future__ import annotations

from datetime import date
from pathlib import Path

DEPRECATION_MAP = Path("docs/platform-contract/DEPRECATION_MAP.md")
ALLOWED_STATUSES = {"complete", "waived-with-exception"}


def _parse_primary_table_rows(content: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    capture = False
    for line in content.splitlines():
        if line.startswith("| Deprecated Pattern |"):
            capture = True
            continue
        if capture and line.startswith("## "):
            break
        if not capture or not line.startswith("|") or line.startswith("|---"):
            continue

        parts = [cell.strip() for cell in line.strip("|").split("|")]
        if len(parts) < 6:
            continue
        rows.append(
            {
                "pattern": parts[0],
                "deadline": parts[2],
                "status": parts[4].lower(),
                "validation": parts[5],
            }
        )
    return rows


def test_overdue_deprecation_map_entries_are_resolved_or_waived() -> None:
    assert DEPRECATION_MAP.exists(), f"Missing {DEPRECATION_MAP}"
    rows = _parse_primary_table_rows(DEPRECATION_MAP.read_text(encoding="utf-8"))
    assert rows, "Could not parse deprecation rows from DEPRECATION_MAP.md"

    today = date.today()
    violations: list[str] = []
    for row in rows:
        deadline = row["deadline"]
        if deadline == "TBD":
            continue
        due = date.fromisoformat(deadline)
        if due <= today and row["status"] not in ALLOWED_STATUSES:
            violations.append(
                f"{row['pattern']} deadline={deadline} status={row['status']} validation={row['validation']}"
            )

    assert not violations, "Overdue deprecation entries unresolved:\n" + "\n".join(violations)
