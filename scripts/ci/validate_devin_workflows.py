#!/usr/bin/env python3
"""Validate .devin/workflows/*.md against the WORKFLOW.md authoring specification.

Checks every workflow markdown file for:
1. Required YAML frontmatter (workflow_id, name, version, description, pattern, risk_level)
2. Explicit State JSON block
3. Circuit breaker configuration
4. Completion Checklist section
5. Stale path references (frontend/client/, frontend/node_modules/, etc.)

Exit codes:
  0 = all workflows valid
  1 = one or more violations found
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_WORKFLOWS_DIR = ROOT / ".devin" / "workflows"

REQUIRED_FRONTMATTER_FIELDS = {
    "workflow_id",
    "name",
    "version",
    "description",
    "pattern",
    "risk_level",
}

VALID_PATTERNS = {
    "manager-worker",
    "pipeline-dag",
    "human-in-the-loop",
    "circuit-breaker",
}

VALID_RISK_LEVELS = {
    "low",
    "medium",
    "high",
}

STALE_PATH_PATTERNS = [
    re.compile(r"frontend/client/"),
    re.compile(r"frontend/node_modules/"),
    re.compile(r"frontend/\.eslintrc\.js"),
    re.compile(r"frontend/\.eslintrc\.cjs"),
    re.compile(r"frontend/client/src/"),
]

FRONTMATTER_RE = re.compile(
    r"^---\s*\n(.*?)\n---\s*\n",
    re.DOTALL,
)


class ValidationError:
    def __init__(self, file: Path, category: str, message: str) -> None:
        self.file = file
        self.category = category
        self.message = message

    def __str__(self) -> str:
        return f"[{self.category}] {self.file.name}: {self.message}"


def parse_frontmatter(content: str) -> dict[str, Any] | None:
    match = FRONTMATTER_RE.match(content)
    if not match:
        return None
    try:
        return yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        return None


def check_frontmatter(file: Path, content: str) -> list[ValidationError]:
    errors: list[ValidationError] = []
    fm = parse_frontmatter(content)

    if fm is None:
        errors.append(ValidationError(file, "frontmatter", "Missing or malformed YAML frontmatter block"))
        return errors

    if not isinstance(fm, dict):
        errors.append(ValidationError(file, "frontmatter", "Frontmatter is not a YAML mapping"))
        return errors

    missing = REQUIRED_FRONTMATTER_FIELDS - set(fm.keys())
    if missing:
        errors.append(
            ValidationError(
                file,
                "frontmatter",
                f"Missing required field(s): {', '.join(sorted(missing))}",
            )
        )

    if "pattern" in fm and fm["pattern"] not in VALID_PATTERNS:
        errors.append(
            ValidationError(
                file,
                "frontmatter",
                f"Invalid pattern '{fm['pattern']}'; must be one of {VALID_PATTERNS}",
            )
        )

    if "risk_level" in fm and fm["risk_level"] not in VALID_RISK_LEVELS:
        errors.append(
            ValidationError(
                file,
                "frontmatter",
                f"Invalid risk_level '{fm['risk_level']}'; must be one of {VALID_RISK_LEVELS}",
            )
        )

    return errors


def check_state_json(file: Path, content: str) -> list[ValidationError]:
    errors: list[ValidationError] = []
    # Look for a JSON code block containing "stage" and "circuit_breaker"
    json_blocks = re.findall(r"```json\n(.*?)\n```", content, re.DOTALL)
    found_valid = False
    for block in json_blocks:
        if '"stage"' in block and '"circuit_breaker"' in block:
            found_valid = True
            break
    if not found_valid:
        errors.append(
            ValidationError(
                file,
                "state_json",
                "Missing explicit State JSON block with 'stage' and 'circuit_breaker' keys",
            )
        )
    return errors


def check_circuit_breaker(file: Path, content: str) -> list[ValidationError]:
    errors: list[ValidationError] = []
    # Accept YAML-style circuit_breaker block or inline JSON circuit breaker config
    has_yaml_cb = re.search(r"circuit_breaker:\s*\n", content) is not None
    has_json_cb = re.search(r'"circuit_breaker"', content) is not None
    if not has_yaml_cb and not has_json_cb:
        errors.append(
            ValidationError(
                file,
                "circuit_breaker",
                "Missing circuit breaker configuration (YAML block or JSON key)",
            )
        )
    return errors


def check_completion_checklist(file: Path, content: str) -> list[ValidationError]:
    errors: list[ValidationError] = []
    checklist_match = re.search(
        r"##\s+Completion Checklist\s*\n((?:\s*-\s*\[\s*[ x]\s*\].*\n)+)",
        content,
        re.IGNORECASE,
    )
    if not checklist_match:
        errors.append(
            ValidationError(
                file,
                "checklist",
                "Missing '## Completion Checklist' section with markdown checkboxes",
            )
        )
        return errors

    items = re.findall(r"-\s*\[\s*[ x]\s*\]", checklist_match.group(1))
    if len(items) < 3:
        errors.append(
            ValidationError(
                file,
                "checklist",
                f"Completion checklist has only {len(items)} item(s); minimum is 3",
            )
        )
    return errors


def check_stale_paths(file: Path, content: str) -> list[ValidationError]:
    errors: list[ValidationError] = []
    for pattern in STALE_PATH_PATTERNS:
        for match in pattern.finditer(content):
            errors.append(
                ValidationError(
                    file,
                    "stale_path",
                    f"Stale path reference '{match.group(0)}' at column {match.start()}",
                )
            )
    return errors


def validate_file(file: Path) -> list[ValidationError]:
    content = file.read_text(encoding="utf-8")
    errors: list[ValidationError] = []
    errors.extend(check_frontmatter(file, content))
    # Only run deeper checks if frontmatter is parseable; otherwise content boundaries may be off
    if not any(e.category == "frontmatter" and "Missing or malformed" in e.message for e in errors):
        errors.extend(check_state_json(file, content))
        errors.extend(check_circuit_breaker(file, content))
        errors.extend(check_completion_checklist(file, content))
        errors.extend(check_stale_paths(file, content))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate .devin/workflows against WORKFLOW.md spec")
    parser.add_argument(
        "--workflows-dir",
        type=Path,
        default=DEFAULT_WORKFLOWS_DIR,
        help="Directory containing workflow .md files",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit results as JSON",
    )
    parser.add_argument(
        "--check-index",
        action="store_true",
        help="Also verify INDEX.md is present and references each workflow",
    )
    args = parser.parse_args()

    if not args.workflows_dir.exists():
        print(f"ERROR: Workflows directory does not exist: {args.workflows_dir}", file=sys.stderr)
        return 1

    # Only validate actual workflow definitions, not the spec doc or index
    EXCLUDED_NAMES = {"WORKFLOW.md", "INDEX.md"}
    workflow_files = sorted(
        p for p in args.workflows_dir.iterdir()
        if p.suffix == ".md" and not p.name.startswith("_") and p.name not in EXCLUDED_NAMES
    )
    # Also include templates
    template_files = sorted(
        p for p in (args.workflows_dir / "_templates").iterdir() if p.suffix == ".md"
    ) if (args.workflows_dir / "_templates").exists() else []

    all_files = workflow_files + template_files
    all_errors: list[ValidationError] = []
    file_errors: dict[str, list[ValidationError]] = {}

    for wf in all_files:
        errs = validate_file(wf)
        if errs:
            file_errors[wf.name] = errs
            all_errors.extend(errs)

    if args.check_index:
        index_path = args.workflows_dir / "INDEX.md"
        if not index_path.exists():
            err = ValidationError(index_path, "index", "INDEX.md is missing")
            all_errors.append(err)
            file_errors.setdefault("INDEX.md", []).append(err)
        else:
            index_content = index_path.read_text(encoding="utf-8")
            for wf in workflow_files:
                if wf.stem not in index_content and wf.name not in index_content:
                    err = ValidationError(
                        index_path,
                        "index",
                        f"INDEX.md does not reference workflow '{wf.name}'",
                    )
                    all_errors.append(err)
                    file_errors.setdefault("INDEX.md", []).append(err)

    if args.json:
        import json
        output = {
            "valid": len(all_errors) == 0,
            "total_files": len(all_files),
            "total_errors": len(all_errors),
            "files_with_errors": {
                name: [{"category": e.category, "message": e.message} for e in errs]
                for name, errs in file_errors.items()
            },
        }
        print(json.dumps(output, indent=2))
    else:
        if all_errors:
            print(f"Found {len(all_errors)} violation(s) across {len(file_errors)} file(s):\n")
            for name, errs in sorted(file_errors.items()):
                print(f"  {name}:")
                for e in errs:
                    print(f"    {e}")
                print()
        else:
            print(f"All {len(all_files)} workflow file(s) passed validation.")

    return 1 if all_errors else 0


if __name__ == "__main__":
    sys.exit(main())
