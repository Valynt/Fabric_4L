#!/usr/bin/env python3
"""Generate a category summary for the centralized security pytest suite."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tests.security.security_suite_manifest import SECURITY_CATEGORIES, python_test_paths  # noqa: E402


def build_summary() -> dict[str, object]:
    categories = []
    for category in SECURITY_CATEGORIES:
        missing = [path for path in category.paths if not (REPO_ROOT / path).exists()]
        categories.append(
            {
                "key": category.key,
                "title": category.title,
                "description": category.description,
                "references": list(category.paths),
                "pytest_modules": list(python_test_paths(category)),
                "missing_references": missing,
            }
        )
    return {
        "suite": "tests/security",
        "command": "pytest tests/security/",
        "categories": categories,
    }


def render_markdown(summary: dict[str, object]) -> str:
    lines = [
        "# Security Test Summary",
        "",
        f"Suite: `{summary['suite']}`",
        f"Canonical command: `{summary['command']}`",
        "",
        "| Category | Referenced pytest modules | Total references | Missing references |",
        "| --- | ---: | ---: | ---: |",
    ]
    for category in summary["categories"]:  # type: ignore[index]
        lines.append(
            "| {title} | {pytest_count} | {ref_count} | {missing_count} |".format(
                title=category["title"],
                pytest_count=len(category["pytest_modules"]),
                ref_count=len(category["references"]),
                missing_count=len(category["missing_references"]),
            )
        )
    lines.append("")
    for category in summary["categories"]:  # type: ignore[index]
        lines.extend(
            [
                f"## {category['title']}",
                "",
                str(category["description"]),
                "",
            ]
        )
        for reference in category["references"]:
            lines.append(f"- `{reference}`")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--markdown", type=Path, help="Write Markdown summary to this path.")
    parser.add_argument("--json", type=Path, help="Write JSON summary to this path.")
    args = parser.parse_args()

    summary = build_summary()
    if args.markdown:
        args.markdown.parent.mkdir(parents=True, exist_ok=True)
        args.markdown.write_text(render_markdown(summary), encoding="utf-8")
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not args.markdown and not args.json:
        print(render_markdown(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
