#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
RUNTIME_DIRS = ("services", "packages", "value_fabric")
PUBLIC_API_PREFIX = "value_fabric.public_api"
BASELINED_SERVICE_PREFIXES = (
    "services/layer1-ingestion/",
    "services/layer2-extraction/",
    "services/layer3-knowledge/",
    "services/layer4-agents/",
    "services/layer5-ground-truth/",
    "services/layer6-benchmarks/",
)
IMPORT_RE = re.compile(r"^\s*(?:from|import)\s+(value_fabric\.[\w\.]+)")


def _is_runtime_python(rel: str) -> bool:
    if not rel.endswith(".py"):
        return False
    ignored_parts = {
        "tests",
        "test",
        "__pycache__",
        ".venv",
        "venv",
        "node_modules",
    }
    return not any(part in ignored_parts for part in rel.split("/"))


def _iter_runtime_files(repo_root: Path) -> list[Path]:
    files: list[Path] = []
    for directory in RUNTIME_DIRS:
        root = repo_root / directory
        if not root.exists():
            continue
        files.extend(
            p
            for p in root.rglob("*.py")
            if _is_runtime_python(p.relative_to(repo_root).as_posix())
        )
    return sorted(files)


def scan(repo_root: Path) -> tuple[list[str], list[str]]:
    public_imports: list[str] = []
    deep_imports: list[str] = []

    for p in _iter_runtime_files(repo_root):
        rel = p.relative_to(repo_root).as_posix()
        for lineno, line in enumerate(
            p.read_text(encoding="utf-8", errors="ignore").splitlines(),
            1,
        ):
            match = IMPORT_RE.match(line)
            if not match:
                continue
            mod = match.group(1)

            if mod == PUBLIC_API_PREFIX or mod.startswith(f"{PUBLIC_API_PREFIX}."):
                public_imports.append(f"{rel}:{lineno}:{mod}")
                continue

            if not rel.startswith(BASELINED_SERVICE_PREFIXES):
                continue
            if rel.endswith("/adapters/value_fabric_api.py"):
                continue
            if mod == "value_fabric.shared":
                continue
            if mod.startswith("value_fabric.shared."):
                deep_imports.append(f"{rel}:{lineno}:{mod}")

    return public_imports, deep_imports


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Block runtime imports of value_fabric.public_api and report "
            "remaining non-adapter value_fabric.shared deep imports."
        )
    )
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    args = parser.parse_args(argv)

    repo_root = args.repo_root.resolve()
    public_imports, deep_imports = scan(repo_root)

    if public_imports:
        print("Runtime value_fabric.public_api imports are forbidden:")
        print("\n".join(public_imports))
        return 1

    print(
        f"OK: public_api imports=0; {len(deep_imports)} non-public shared imports "
        "observed outside adapter modules"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
