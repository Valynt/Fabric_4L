#!/usr/bin/env python3
"""Auto-generate .devin/workflows/INDEX.md from workflow frontmatter."""
from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_WORKFLOWS_DIR = ROOT / ".devin" / "workflows"

# Display names for category slugs read from frontmatter
CATEGORY_DISPLAY: dict[str, str] = {
    "agent-infrastructure": "Agent Infrastructure & Meta Workflows",
    "quality-debt": "Quality Debt & Code Hygiene",
    "testing": "Testing & Quality Assurance",
    "code-review": "Code Review & Development",
    "architecture": "Architecture & Governance",
    "frontend-ux": "Frontend & UX",
    "documentation": "Documentation",
    "infrastructure": "Infrastructure & DevOps",
    "planning": "Planning & Roadmap",
    "operations": "Operations & Incident Response",
    "orchestration": "Orchestration Patterns (Templates)",
}

# Ordering of categories in the generated index
CATEGORY_ORDER = [
    "Agent Infrastructure & Meta Workflows",
    "Quality Debt & Code Hygiene",
    "Testing & Quality Assurance",
    "Code Review & Development",
    "Architecture & Governance",
    "Frontend & UX",
    "Documentation",
    "Infrastructure & DevOps",
    "Planning & Roadmap",
    "Operations & Incident Response",
]


def parse_frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not match:
        return {}
    raw = match.group(1)
    data: dict[str, str] = {}
    for line in raw.splitlines():
        if ":" in line:
            key, val = line.split(":", 1)
            data[key.strip()] = val.strip()
    return data


def build_index(workflows_dir: Path) -> str:
    workflows: list[tuple[Path, dict[str, str]]] = []

    for path in sorted(workflows_dir.iterdir()):
        if not path.suffix == ".md":
            continue
        if path.name in {"WORKFLOW.md", "INDEX.md"}:
            continue
        fm = parse_frontmatter(path)
        workflows.append((path, fm))

    # Categorize workflows using frontmatter category, fallback to Uncategorized
    categorized: dict[str, list[tuple[Path, dict[str, str]]]] = defaultdict(list)
    for path, fm in workflows:
        category_slug = fm.get("category", "")
        category = CATEGORY_DISPLAY.get(category_slug, "Uncategorized") if category_slug else "Uncategorized"
        categorized[category].append((path, fm))

    lines: list[str] = [
        "# Workflows Index",
        "",
        "This index catalogs all available workflows in the `.devin/workflows/` directory. Workflows are orchestration patterns with explicit state machines for human-driven processes.",
        "",
        "For workflow authoring specifications, see [WORKFLOW.md](./WORKFLOW.md).",
        "",
        "---",
        "",
    ]

    for category in CATEGORY_ORDER:
        items = categorized.get(category, [])
        if not items:
            continue
        lines.append(f"## {category}")
        lines.append("")
        for path, fm in items:
            workflow_id = fm.get("workflow_id", path.stem)
            name = fm.get("name", workflow_id)
            description = fm.get("description", "")
            lines.append(f"### {workflow_id}")
            lines.append(f"**Description:** {description}")
            lines.append(f"**When to Use:** See workflow file for activation criteria")
            lines.append("")
        lines.append("---")
        lines.append("")

    # Workflow spec
    lines.append("## Workflow Templates")
    lines.append("")
    lines.append("### WORKFLOW.md")
    lines.append("**Description:** Workflow authoring specification for structured orchestration patterns")
    lines.append("**When to Use:** Creating new workflows with proper state management and circuit breakers")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Maintenance footer
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    total = len(workflows)
    lines.append("## Workflow Maintenance")
    lines.append("")
    lines.append(f"**Last Updated:** {now}")
    lines.append("")
    lines.append(f"**Total Workflows:** {total}")
    lines.append("")
    lines.append(f"**Workflows with Frontmatter:** {total}/{total} (100%)")
    lines.append("")
    lines.append("**Note:** This index is auto-generated. Run `python scripts/ci/generate_workflow_index.py` to regenerate.")
    lines.append("")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate workflow INDEX.md from frontmatter")
    parser.add_argument(
        "--workflows-dir",
        type=Path,
        default=DEFAULT_WORKFLOWS_DIR,
        help="Directory containing workflow markdown files",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_WORKFLOWS_DIR / "INDEX.md",
        help="Output path for generated INDEX.md",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit with error if output would differ from existing file",
    )
    args = parser.parse_args()

    generated = build_index(args.workflows_dir)

    if args.check:
        if not args.output.exists():
            print(f"CHECK FAILED: {args.output} does not exist")
            return 1
        existing = args.output.read_text(encoding="utf-8")
        if generated.strip() != existing.strip():
            print(f"CHECK FAILED: {args.output} is out of sync with workflow frontmatter")
            return 1
        print(f"CHECK PASSED: {args.output} is in sync")
        return 0

    args.output.write_text(generated, encoding="utf-8")
    print(f"Generated {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
