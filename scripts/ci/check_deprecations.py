#!/usr/bin/env python3
"""CI gate for deprecations with passed target removal dates."""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path

REGISTER_PATH = Path(__file__).resolve().parents[2] / "docs" / "deprecation_register.json"
OVERRIDE_ENV_VAR = "DEPRECATION_ALLOW_OVERDUE"


def _load_register() -> list[dict[str, str]]:
    payload = json.loads(REGISTER_PATH.read_text(encoding="utf-8"))
    return payload.get("items", [])


def _date(value: str) -> datetime.date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def main() -> int:
    today = datetime.utcnow().date()
    override_enabled = os.getenv(OVERRIDE_ENV_VAR, "").lower() in {"1", "true", "yes"}

    overdue: list[dict[str, str]] = []
    for item in _load_register():
        removal = item.get("target_removal")
        if removal and _date(removal) < today:
            overdue.append(item)

    if not overdue:
        print(f"Deprecation check passed: no overdue items as of {today.isoformat()}.")
        return 0

    print(f"Detected {len(overdue)} overdue deprecation item(s) as of {today.isoformat()}:")
    for item in overdue:
        print(
            f" - {item.get('feature')} (owner={item.get('owner')}, "
            f"target_removal={item.get('target_removal')})"
        )

    if override_enabled:
        print(f"Override enabled via {OVERRIDE_ENV_VAR}; allowing CI to continue.")
        return 0

    print(
        f"Failing CI: at least one target_removal date has passed. "
        f"Set {OVERRIDE_ENV_VAR}=true only for explicit, temporary override."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
