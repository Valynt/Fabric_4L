from __future__ import annotations

import json
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
COMMANDS_DOC = REPO_ROOT / "docs" / "development" / "COMMANDS.md"
BUILD_SYSTEM_DOC = REPO_ROOT / "docs" / "development" / "BUILD_SYSTEM.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _root_scripts() -> set[str]:
    package_json = json.loads((REPO_ROOT / "package.json").read_text(encoding="utf-8"))
    return set(package_json["scripts"])


def _public_make_targets() -> set[str]:
    source = _read(REPO_ROOT / "Makefile")
    pattern = re.compile(r"^([A-Za-z0-9_.-]+):.*##", re.MULTILINE)
    return set(pattern.findall(source))


def test_every_root_package_script_is_documented() -> None:
    commands = _read(COMMANDS_DOC)

    missing = sorted(script for script in _root_scripts() if f"`{script}`" not in commands)

    assert not missing, f"Root package scripts missing from COMMANDS.md: {missing}"


def test_every_public_makefile_target_is_documented() -> None:
    commands = _read(COMMANDS_DOC)

    missing = sorted(target for target in _public_make_targets() if f"`{target}`" not in commands)

    assert not missing, f"Public Makefile targets missing from COMMANDS.md: {missing}"


def test_command_docs_define_canonical_hierarchy_and_ci_mapping() -> None:
    commands = _read(COMMANDS_DOC)
    build_system = _read(BUILD_SYSTEM_DOC)
    combined = f"{commands}\n{build_system}"

    required_phrases = [
        "The Makefile is the de facto build system",
        "Use `make` for repo-wide build, test, migration, contract, release, and readiness workflows",
        "Use `pnpm` for JavaScript and TypeScript package management",
        "Use direct Python CI runners only when debugging or reproducing a CI job",
        "Public Makefile targets are targets with `##` help text",
        "CI To Local Mapping",
    ]

    missing = [phrase for phrase in required_phrases if phrase not in combined]

    assert not missing, f"Required command hierarchy text missing: {missing}"


def test_root_docs_link_to_command_map() -> None:
    required_links = [
        "docs/development/BUILD_SYSTEM.md",
        "docs/development/COMMANDS.md",
    ]

    for relative_path in ("README.md", "CONTRIBUTING.md", "AGENTS.md"):
        source = _read(REPO_ROOT / relative_path)
        missing = [link for link in required_links if link not in source]
        assert not missing, f"{relative_path} is missing command-map links: {missing}"
