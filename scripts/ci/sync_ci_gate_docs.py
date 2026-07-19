#!/usr/bin/env python3
"""Synchronize human-readable CI workflow inventories from the JSON registry."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_DIR = ROOT / ".github" / "workflows"
REGISTRY = WORKFLOW_DIR / "workflow-registry.json"
REGISTRY_DOC = WORKFLOW_DIR / "WORKFLOW_REGISTRY.md"
README = WORKFLOW_DIR / "README.md"
CI_GATES = ROOT / "docs" / "development" / "CI_GATES.md"


def display(items: list[str]) -> str:
    return ", ".join(items) if items else "none"


def classification(entry: dict) -> str:
    if entry["blocking"]:
        return "required / blocking"
    triggers = set(entry["trigger"])
    if "pull_request" in triggers:
        return "pull request validation"
    if triggers <= {"schedule", "workflow_dispatch"} and "schedule" in triggers:
        return "scheduled assurance"
    if "workflow_call" in triggers:
        return "reusable automation"
    if triggers & {"release", "push", "workflow_run"}:
        return "delivery / continuous automation"
    return "manual automation"


def registry_inventory(entries: list[dict]) -> str:
    rows = [
        "| Workflow | Owner | Blocking | Triggers | Local validation |",
        "|---|---|---:|---|---|",
    ]
    for entry in entries:
        rows.append(
            f"| `{entry['path']}` | `{entry['owner']}` | "
            f"{'yes' if entry['blocking'] else 'no'} | "
            f"`{display(entry['trigger'])}` | `{entry['local_validation_command']}` |"
        )
    return "\n".join(rows)


def ci_gates_document(entries: list[dict]) -> str:
    rows = [
        "| Workflow | Classification | Triggers | Owner / triage | Local command | Dependencies | Artifacts | Runtime budget |",
        "|---|---|---|---|---|---|---|---:|",
    ]
    for entry in entries:
        rows.append(
            f"| `{Path(entry['path']).name}` | {classification(entry)} | "
            f"`{display(entry['trigger'])}` | `{entry['owner']}` | "
            f"`{entry['local_validation_command']}` | {display(entry['required_secrets'])} | "
            f"{display(entry['produced_artifacts'])} | {entry['runtime_budget_minutes']} min |"
        )
    return "\n".join(
        [
            "# CI Gates",
            "",
            "This is the authoritative human-readable CI classification and triage map. "
            "Its machine-readable source is `.github/workflows/workflow-registry.json`; "
            "do not edit the inventory by hand.",
            "",
            "## Classification rules",
            "",
            "- **required / blocking**: contributes to a merge, release, deployment, or promotion decision.",
            "- **pull request validation**: runs for pull requests but is not registered as blocking.",
            "- **scheduled assurance**: non-blocking scheduled operational or security evidence.",
            "- **reusable automation**: callable by another workflow.",
            "- **delivery / continuous automation**: responds to pushes, releases, or completed workflows.",
            "- **manual automation**: dispatch-only non-blocking automation.",
            "",
            "The owner is the first-response triage contact. Start with the local command, then inspect "
            "the named workflow run and its retained artifacts. Required secrets are runtime dependencies, "
            "not values that belong in logs or documentation.",
            "",
            f"## Active inventory ({len(entries)} workflows)",
            "",
            *rows,
            "",
            "## Drift check",
            "",
            "Run `make check-workflow-registry` and `make check-workflow-references`.",
            "",
        ]
    )


def synchronized_files() -> dict[Path, str]:
    entries = json.loads(REGISTRY.read_text(encoding="utf-8"))["workflows"]
    registry_doc = REGISTRY_DOC.read_text(encoding="utf-8")
    start = registry_doc.index("## Inventory")
    end = registry_doc.index("## Overlap Register", start)
    inventory = f"## Inventory\n\nThe repository currently contains **{len(entries)}** GitHub Actions workflow files.\n\n{registry_inventory(entries)}\n\n"
    registry_doc = registry_doc[:start] + inventory + registry_doc[end:]

    readme = README.read_text(encoding="utf-8")
    readme = re.sub(
        r"currently contains \*\*\d+\*\* GitHub Actions workflow files",
        f"currently contains **{len(entries)}** GitHub Actions workflow files",
        readme,
    )
    return {REGISTRY_DOC: registry_doc, README: readme, CI_GATES: ci_gates_document(entries)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    stale: list[str] = []
    for path, expected in synchronized_files().items():
        if args.check:
            if not path.exists() or path.read_text(encoding="utf-8") != expected:
                stale.append(path.relative_to(ROOT).as_posix())
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(expected, encoding="utf-8")
    if stale:
        print("CI gate documentation is stale: " + ", ".join(stale))
        return 1
    print("CI gate documentation is in sync")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
