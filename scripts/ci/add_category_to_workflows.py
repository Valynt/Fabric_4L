#!/usr/bin/env python3
"""Add category field to workflow frontmatter based on CATEGORY_MAP."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS_DIR = ROOT / ".devin" / "workflows"

CATEGORY_MAP: dict[str, str] = {
    "value-fabric-harness": "agent-infrastructure",
    "contract-enforcement-auditor": "quality-debt",
    "dead-code-sweeper": "quality-debt",
    "deprecation-migrator": "quality-debt",
    "dil-hook-scaffolder": "quality-debt",
    "facade-page-connector": "quality-debt",
    "tool-contract-sync": "quality-debt",
    "code-boundary-enforcement": "quality-debt",
    "autonomous-test-assurance-agent": "testing",
    "test-quality-remediation": "testing",
    "code-quality-improvement": "code-review",
    "drift-assessment": "architecture",
    "palette-ux-agent": "frontend-ux",
    "fabric-ui-drift-agent": "frontend-ux",
    "react-component-design": "frontend-ux",
    "technical-documentation": "documentation",
    "fumadocs-drift-audit": "documentation",
    "cleanup-docs": "documentation",
    "dependency-update": "infrastructure",
    "bunnyshell": "infrastructure",
    "performance-investigation": "infrastructure",
    "feature-flag-rollout": "infrastructure",
    "roadmap-management": "planning",
    "launch-readiness-assessment": "planning",
    "incident-response": "operations",
    "template-human-in-the-loop": "orchestration",
    "template-manager-worker": "orchestration",
    "template-pipeline-dag": "orchestration",
}


def add_category(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    if "category:" in text[:500]:
        return False  # Already has category

    lines = text.splitlines()
    # Find the frontmatter closing ---
    if not lines[0].strip() == "---":
        return False

    fm_end = 1
    while fm_end < len(lines) and lines[fm_end].strip() != "---":
        fm_end += 1

    if fm_end >= len(lines):
        return False

    # Extract workflow_id to look up category
    workflow_id = ""
    for line in lines[:fm_end]:
        if line.startswith("workflow_id:"):
            workflow_id = line.split(":", 1)[1].strip()
            break

    if not workflow_id:
        return False

    category = CATEGORY_MAP.get(workflow_id)
    if not category:
        print(f"WARNING: No category mapping for {workflow_id} ({path.name})")
        return False

    # Insert category before the closing ---
    new_lines = lines[:fm_end] + [f"category: {category}"] + lines[fm_end:]
    path.write_text("\n".join(new_lines) + ("\n" if text.endswith("\n") else ""), encoding="utf-8")
    print(f"Added category '{category}' to {path.name}")
    return True


def main() -> int:
    modified = 0
    for path in sorted(WORKFLOWS_DIR.iterdir()):
        if not path.suffix == ".md":
            continue
        if path.name in {"WORKFLOW.md", "INDEX.md"}:
            continue
        if add_category(path):
            modified += 1

    print(f"\nModified {modified} workflow file(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
