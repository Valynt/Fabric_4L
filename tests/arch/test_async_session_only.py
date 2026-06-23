"""Architecture gate — runtime modules must use async SQLAlchemy.

PR2 of the elevate-to-9 plan establishes ``create_postgresql_engine`` (async)
as the only sanctioned engine builder for service runtime code. Sync
``sqlalchemy.create_engine`` use is permitted in:

- ``tests/`` directories
- Alembic migration runners (``migrations/`` and ``env.py``)
- ``scripts/`` (one-shot tooling)
- the shared runtime adapter that *intentionally* supports both modes
  (``value_fabric.shared.database.runtime_adapter``)

Any new use outside the allowlist below must be reviewed.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BASELINE_FILE = REPO_ROOT / "config" / "ci" / "async_session_legacy_baseline.txt"


def _load_baseline() -> frozenset[str]:
    if not BASELINE_FILE.exists():
        return frozenset()
    paths: set[str] = set()
    for raw in BASELINE_FILE.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        paths.add(line)
    return frozenset(paths)


BASELINE = _load_baseline()

ALLOWED_PATH_FRAGMENTS = (
    "/tests/",
    "/migrations/",
    "/scripts/",
    "/alembic/",
    "packages/shared/src/value_fabric/shared/database/runtime_adapter.py",
    "packages/shared/src/value_fabric/shared/database/async_engine.py",  # uses create_async_engine; safe regex below
    "packages/shared/src/value_fabric/shared/database/postgresql.py",  # canonical async builder
)

SERVICE_ROOTS = (
    REPO_ROOT / "services",
    REPO_ROOT / "packages" / "shared" / "src",
)

EXCLUDED_DIR_NAMES = frozenset(
    {
        ".venv",
        "venv",
        "node_modules",
        "__pycache__",
        ".pytest_cache",
        ".hypothesis",
        ".uv-cache-local",
        ".tmp-local",
        ".dockerignore",
        ".mypy_cache",
        ".ruff_cache",
        "dist",
        "build",
    }
)


def _iter_python_files(root: Path):
    for path in root.iterdir():
        if path.is_dir():
            if path.name in EXCLUDED_DIR_NAMES or path.name.startswith("."):
                continue
            yield from _iter_python_files(path)
        elif path.suffix == ".py":
            yield path

# Match `create_engine(` only when not preceded by ``async_`` and not part of
# ``create_async_engine``. The negative lookbehind is required so we do not
# flag the legitimate async variant.
SYNC_CREATE_ENGINE = re.compile(r"(?<!async_)\bcreate_engine\s*\(")


def _is_allowlisted(path: Path) -> bool:
    rel = path.as_posix()
    if any(frag in rel for frag in ALLOWED_PATH_FRAGMENTS):
        return True
    try:
        rel_to_repo = path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return False
    return rel_to_repo in BASELINE


def test_no_sync_create_engine_in_service_runtime() -> None:
    offenders: list[str] = []
    for root in SERVICE_ROOTS:
        if not root.exists():
            continue
        for py in _iter_python_files(root):
            if _is_allowlisted(py):
                continue
            try:
                text = py.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            # Quick filter
            if "create_engine" not in text:
                continue
            for line_no, line in enumerate(text.splitlines(), start=1):
                if "create_async_engine" in line:
                    continue
                if SYNC_CREATE_ENGINE.search(line):
                    offenders.append(f"{py.as_posix()}:{line_no}: {line.strip()}")

    assert not offenders, (
        "Sync sqlalchemy.create_engine is forbidden in service runtime code. "
        "Use value_fabric.shared.database.create_postgresql_engine instead.\n"
        + "\n".join(offenders)
    )
