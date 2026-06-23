"""Architecture contract for Layer 4 canonical source-tree namespace.

Layer 4 canonical runtime code lives under ``services/layer4-agents/src/layer4_agents/``.
The ``src/`` root must contain only:

* the ``layer4_agents/`` package directory,
* standard marker files ``__init__.py`` and ``py.typed``,
* and, optionally, thin re-export shims explicitly allowlisted here.

Any other top-level directory or file is a shadow module that must be
canonicalized (moved into ``layer4_agents/``) or removed.
"""

from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
L4_SRC = REPO_ROOT / "services" / "layer4-agents" / "src"

ALLOWED_ROOT_DIRS = {"layer4_agents"}
ALLOWED_ROOT_MARKER_FILES = {"__init__.py", "py.typed"}

# Top-level directories permitted as thin backward-compatibility shim trees.
# Every .py file inside must be a valid re-export shim from layer4_agents.
# Each entry links to the removal ticket.
SHIM_DIR_ALLOWLIST: dict[str, str] = {}

# Top-level files permitted as thin backward-compatibility re-export shims.
# Each entry must contain ONLY comments, blank lines, and imports from the
# ``layer4_agents`` canonical namespace.
SHIM_FILE_ALLOWLIST: dict[str, str] = {}


def _is_valid_reexport_shim(path: Path) -> bool:
    """Return True when *path* is a thin shim importing only from layer4_agents."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

    for node in tree.body:
        # Module docstrings are allowed comments.
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
            if isinstance(node.value.value, str):
                continue
            return False

        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name != "layer4_agents" and not alias.name.startswith("layer4_agents."):
                    return False
            continue

        if isinstance(node, ast.ImportFrom):
            if node.module is None:
                return False
            if node.module != "layer4_agents" and not node.module.startswith("layer4_agents."):
                return False
            continue

        # Anything else (assignments, function calls, class definitions, etc.)
        # makes the file a substantive module, not a shim.
        return False

    return True


def _scan_shim_dir(dir_path: Path) -> list[str]:
    """Return list of non-shim .py files inside an allowlisted directory."""
    bad: list[str] = []
    for py_file in dir_path.rglob("*.py"):
        # Ignore cache artifacts if any leak in.
        if "__pycache__" in py_file.parts:
            continue
        if not _is_valid_reexport_shim(py_file):
            rel = py_file.relative_to(L4_SRC).as_posix()
            bad.append(rel)
    return bad


def test_layer4_source_tree_uses_canonical_namespace_only() -> None:
    """The Layer 4 src root must contain only layer4_agents/ and marker files."""
    dir_violations: list[str] = []
    file_violations: list[str] = []
    shim_dir_violations: list[str] = []
    shim_file_violations: list[str] = []

    for entry in L4_SRC.iterdir():
        name = entry.name

        # Ignore generated artifact directories; they are not source-tree entries.
        if name == "__pycache__":
            continue

        if entry.is_dir():
            if name in ALLOWED_ROOT_DIRS:
                continue
            if name in SHIM_DIR_ALLOWLIST:
                bad_files = _scan_shim_dir(entry)
                if bad_files:
                    shim_dir_violations.extend(
                        f"{f} (allowlisted dir {name}/, ticket {SHIM_DIR_ALLOWLIST[name]})"
                        for f in bad_files
                    )
                continue
            dir_violations.append(
                f"{name}/ is a non-canonical top-level directory under {L4_SRC.relative_to(REPO_ROOT)}"
            )
        elif entry.is_file():
            if name in ALLOWED_ROOT_MARKER_FILES:
                continue
            if name in SHIM_FILE_ALLOWLIST:
                if not _is_valid_reexport_shim(entry):
                    shim_file_violations.append(
                        f"{name} is allowlisted but is not a thin layer4_agents re-export shim "
                        f"(ticket {SHIM_FILE_ALLOWLIST[name]})"
                    )
                continue
            file_violations.append(
                f"{name} is a non-canonical top-level file under {L4_SRC.relative_to(REPO_ROOT)}"
            )

    messages: list[str] = []
    if dir_violations:
        messages.append(
            "Non-canonical top-level directories:\n"
            + "\n".join(f"  - {v}" for v in sorted(dir_violations))
        )
    if file_violations:
        messages.append(
            "Non-canonical top-level files:\n"
            + "\n".join(f"  - {v}" for v in sorted(file_violations))
        )
    if shim_dir_violations:
        messages.append(
            "Non-shim files inside allowlisted shim directories:\n"
            + "\n".join(f"  - {v}" for v in sorted(shim_dir_violations))
        )
    if shim_file_violations:
        messages.append(
            "Invalid shim allowlist entries:\n"
            + "\n".join(f"  - {v}" for v in sorted(shim_file_violations))
        )

    assert not messages, (
        "Layer 4 source tree must use canonical namespace only "
        f"({L4_SRC.relative_to(REPO_ROOT)}/layer4_agents/). Found:\n\n"
        + "\n\n".join(messages)
    )
