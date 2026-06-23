"""Architecture contract for Layer 4 canonical source-tree namespace.

Layer 4 canonical runtime code lives under ``services/layer4-agents/src/layer4_agents/``.
The ``src/`` root should contain only:

* the ``layer4_agents/`` package directory,
* standard marker files ``__init__.py`` and ``py.typed``,
* and a small, tracked set of backward-compatibility shims.

This test uses a baseline ratchet: existing non-canonical entries are listed in
``config/ci/layer4_source_tree_baseline.json``. Net-new non-canonical entries
fail the test. Existing entries must be removed or converted to shims over time.
"""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
L4_SRC = REPO_ROOT / "services" / "layer4-agents" / "src"
BASELINE_PATH = REPO_ROOT / "config" / "ci" / "layer4_source_tree_baseline.json"

ALLOWED_ROOT_DIRS = {"layer4_agents"}
ALLOWED_ROOT_MARKER_FILES = {"__init__.py", "py.typed"}


def _load_baseline() -> set[str]:
    """Load the set of grandfathered non-canonical source-tree entries."""
    if not BASELINE_PATH.exists():
        return set()
    data = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    return set(data if isinstance(data, list) else data.get("entries", []))


def test_layer4_source_tree_uses_canonical_namespace_only() -> None:
    """The L4 src root must not gain new non-canonical top-level entries."""
    baseline = _load_baseline()
    violations: list[str] = []

    for entry in L4_SRC.iterdir():
        name = entry.name

        # Ignore generated artifact directories.
        if name == "__pycache__":
            continue

        rel = entry.relative_to(L4_SRC).as_posix()
        if rel in baseline:
            continue

        if entry.is_dir():
            if name not in ALLOWED_ROOT_DIRS:
                violations.append(
                    f"{rel}/ is a non-canonical top-level directory"
                )
        elif entry.is_file():
            if name not in ALLOWED_ROOT_MARKER_FILES:
                violations.append(
                    f"{rel} is a non-canonical top-level file"
                )

    assert not violations, (
        "Layer 4 source tree must use canonical namespace only "
        f"({L4_SRC.relative_to(REPO_ROOT)}/layer4_agents/). "
        "Net-new non-canonical entries found:\n\n"
        + "\n".join(f"  - {v}" for v in sorted(violations))
        + "\n\nIf these are pre-existing entries, add them to "
        f"{BASELINE_PATH.relative_to(REPO_ROOT)}. "
        "If they are new, move them into src/layer4_agents/."
    )
