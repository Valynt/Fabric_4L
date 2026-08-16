#!/usr/bin/env python3
"""CI gate for deprecations with passed target removal dates.

Reads the register through the canonical shared loader
(``value_fabric.shared.governance.deprecation_register``) so this gate, the
Layer 1 runtime headers, and the service startup warnings all consume one
source, one path resolution, and one schema.
"""

from __future__ import annotations

import os
import sys
from datetime import UTC, datetime
from pathlib import Path

_SHARED_SRC = Path(__file__).resolve().parents[2] / "packages" / "shared" / "src"
if str(_SHARED_SRC) not in sys.path:
    sys.path.insert(0, str(_SHARED_SRC))

from value_fabric.shared.governance.deprecation_register import (  # noqa: E402
    DeprecationItem,
    DeprecationRegisterError,
    load_items,
    overdue_items,
    resolve_register_path,
)

OVERRIDE_ENV_VAR = "DEPRECATION_ALLOW_OVERDUE"


def _report(items: list[DeprecationItem], today: str) -> None:
    print(f"Detected {len(items)} overdue deprecation item(s) as of {today}:")
    for item in items:
        print(
            f" - {item.feature} (owner={item.owner}, "
            f"target_removal={item.target_removal})"
        )


def main() -> int:
    today = datetime.now(UTC).date()
    override_enabled = os.getenv(OVERRIDE_ENV_VAR, "").lower() in {"1", "true", "yes"}

    try:
        items = load_items()
    except DeprecationRegisterError as exc:
        # Fail loudly: a missing or malformed register must never be silently
        # treated as "no deprecations".
        print(f"Deprecation register error: {exc}")
        return 1

    # Every registered path must exist on disk unless the entry is explicitly
    # marked removed, so the register cannot drift away from the codebase.
    repo_root = resolve_register_path().parent.parent
    missing_paths = [
        item
        for item in items
        if item.path
        and item.status != "removed"
        and not (repo_root / item.path.split(":", 1)[0]).exists()
    ]

    overdue = overdue_items(today=today, items=items)

    if not overdue and not missing_paths:
        print(f"Deprecation check passed: no overdue items as of {today.isoformat()}.")
        print(f"Register: {resolve_register_path()} ({len(items)} item(s)).")
        return 0

    exit_code = 0

    if missing_paths:
        print(f"Detected {len(missing_paths)} register item(s) whose path no longer exists:")
        for item in missing_paths:
            print(f" - {item.feature} (path={item.path})")
        print(
            "Either restore the path, update the register entry, or set "
            'status="removed" once the surface is gone.'
        )
        exit_code = 1

    if overdue:
        _report(overdue, today.isoformat())
        if override_enabled:
            print(f"Override enabled via {OVERRIDE_ENV_VAR}; allowing CI to continue.")
        else:
            print(
                f"Failing CI: at least one target_removal date has passed. "
                f"Set {OVERRIDE_ENV_VAR}=true only for explicit, temporary override."
            )
            exit_code = 1

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
