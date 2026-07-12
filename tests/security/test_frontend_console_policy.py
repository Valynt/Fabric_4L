"""Production frontend source must not contain direct console calls."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
WEB_SRC = REPO_ROOT / "apps" / "web" / "src"
CONSOLE_CALL_RE = re.compile(r"\bconsole\.(?:log|warn|error|info|debug)\b")
PRODUCTION_EXTENSIONS = {".ts", ".tsx"}


def _production_source_files() -> list[Path]:
    files: list[Path] = []
    for path in WEB_SRC.rglob("*"):
        if path.suffix not in PRODUCTION_EXTENSIONS:
            continue
        if path.name.endswith((".test.ts", ".test.tsx", ".spec.ts", ".spec.tsx")):
            continue
        files.append(path)
    return files


@pytest.mark.security
def test_frontend_production_source_has_no_direct_console_calls() -> None:
    offenders: list[str] = []
    for path in _production_source_files():
        source = path.read_text(encoding="utf-8")
        for index, line in enumerate(source.splitlines(), start=1):
            if CONSOLE_CALL_RE.search(line):
                offenders.append(f"{path.relative_to(REPO_ROOT)}:{index}")

    assert offenders == []
