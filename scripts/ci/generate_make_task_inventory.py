#!/usr/bin/env python3
"""Generate and validate the checked-in root Make task inventory."""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import re
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MAKEFILE = ROOT / "Makefile"
DEFAULT_OUTPUT = ROOT / "config" / "ci" / "make-task-inventory.json"

_RULE_RE = re.compile(
    r"^(?P<targets>[A-Za-z0-9_./%+@-]+(?:[ \t]+[A-Za-z0-9_./%+@-]+)*)"
    r"[ \t]*:(?!=)(?P<body>.*)$"
)
_SPECIAL_TARGETS = frozenset(
    {
        ".DEFAULT",
        ".DELETE_ON_ERROR",
        ".EXPORT_ALL_VARIABLES",
        ".IGNORE",
        ".INTERMEDIATE",
        ".LOW_RESOLUTION_TIME",
        ".NOTPARALLEL",
        ".ONESHELL",
        ".PHONY",
        ".POSIX",
        ".PRECIOUS",
        ".SECONDARY",
        ".SECONDEXPANSION",
        ".SILENT",
        ".SUFFIXES",
    }
)


class InventoryError(ValueError):
    """Raised when the Make task contract is ambiguous or incomplete."""


@dataclass(frozen=True)
class LogicalLine:
    """A Make logical line and its physical source span."""

    text: str
    start_line: int
    end_line: int


@dataclass(frozen=True)
class ParsedRule:
    """An explicit Make rule before inventory serialization."""

    names: tuple[str, ...]
    line: int
    end_line: int
    prerequisites: tuple[str, ...]
    public: bool
    description: str
    recipe_line_count: int
    recipe_sha256: str


def _logical_lines(lines: Sequence[str]) -> list[LogicalLine]:
    """Join Make continuation lines while preserving their physical span."""

    logical: list[LogicalLine] = []
    index = 0
    while index < len(lines):
        start = index
        parts = [lines[index]]
        while parts[-1].rstrip().endswith("\\") and index + 1 < len(lines):
            parts[-1] = parts[-1].rstrip()[:-1]
            index += 1
            parts.append(lines[index].lstrip())
        logical.append(
            LogicalLine(
                text=" ".join(part.rstrip("\n") for part in parts),
                start_line=start + 1,
                end_line=index + 1,
            )
        )
        index += 1
    return logical


def _split_rule(logical: LogicalLine) -> tuple[tuple[str, ...], str] | None:
    """Return explicit targets and rule body, excluding Make special targets."""

    if not logical.text or logical.text[0].isspace() or logical.text.startswith("#"):
        return None
    match = _RULE_RE.match(logical.text)
    if not match:
        return None
    names = tuple(match.group("targets").split())
    if any(name in _SPECIAL_TARGETS for name in names):
        return None
    return names, match.group("body")


def _parse_prerequisites(body: str) -> tuple[str, ...]:
    """Parse prerequisites before inline comments or order-only separators."""

    prerequisite_text = body.split("#", 1)[0].strip()
    if not prerequisite_text:
        return ()
    return tuple(token for token in prerequisite_text.split() if token != "|")


def _recipe_lines(lines: Sequence[str], end_line: int) -> list[str]:
    """Return physical recipe lines immediately following a rule."""

    recipe: list[str] = []
    index = end_line
    while index < len(lines):
        line = lines[index]
        if line.startswith("\t"):
            recipe.append(line.rstrip("\r\n"))
            index += 1
            continue
        if not line.strip() or line.lstrip().startswith("#"):
            index += 1
            continue
        break
    return recipe


def _parse_phony(logical_lines: Sequence[LogicalLine]) -> tuple[set[str], list[str]]:
    phony: set[str] = set()
    duplicates: list[str] = []
    for logical in logical_lines:
        match = re.match(r"^\.PHONY[ \t]*:(?!=)(?P<body>.*)$", logical.text)
        if not match:
            continue
        for name in _parse_prerequisites(match.group("body")):
            if name in phony:
                duplicates.append(name)
            phony.add(name)
    return phony, duplicates


def _parse_rules(
    lines: Sequence[str], logical_lines: Sequence[LogicalLine]
) -> list[ParsedRule]:
    rules: list[ParsedRule] = []
    for logical in logical_lines:
        split = _split_rule(logical)
        if split is None:
            continue
        names, body = split
        recipe = _recipe_lines(lines, logical.end_line)
        description = body.split("##", 1)[1].strip() if "##" in body else ""
        rules.append(
            ParsedRule(
                names=names,
                line=logical.start_line,
                end_line=logical.end_line,
                prerequisites=_parse_prerequisites(body),
                public="##" in body,
                description=description,
                recipe_line_count=len(recipe),
                recipe_sha256=hashlib.sha256(
                    "\n".join(recipe).encode("utf-8")
                ).hexdigest(),
            )
        )
    return rules


def build_inventory(makefile: Path = DEFAULT_MAKEFILE) -> dict[str, object]:
    """Build a deterministic inventory, failing on Make task contract drift."""

    source_bytes = makefile.read_bytes()
    source_text = source_bytes.decode("utf-8")
    lines = source_text.splitlines(keepends=True)
    logical_lines = _logical_lines(lines)
    phony, duplicate_phony = _parse_phony(logical_lines)
    rules = _parse_rules(lines, logical_lines)

    definitions: dict[str, ParsedRule] = {}
    duplicate_definitions: set[str] = set()
    for rule in rules:
        for name in rule.names:
            if name in definitions:
                duplicate_definitions.add(name)
            else:
                definitions[name] = rule

    unknown_phony = sorted(phony - definitions.keys())
    missing_phony = sorted(name for name in definitions if name not in phony)

    errors: list[str] = []
    if duplicate_definitions:
        errors.append(
            "duplicate target definitions: " + ", ".join(sorted(duplicate_definitions))
        )
    if duplicate_phony:
        errors.append(
            "duplicate .PHONY declarations: " + ", ".join(sorted(set(duplicate_phony)))
        )
    if unknown_phony:
        errors.append(
            ".PHONY names without target definitions: " + ", ".join(unknown_phony)
        )
    if missing_phony:
        errors.append("targets missing .PHONY: " + ", ".join(missing_phony))
    if errors:
        raise InventoryError(
            "Make task inventory validation failed:\n- " + "\n- ".join(errors)
        )

    targets: list[dict[str, object]] = []
    for name in sorted(definitions):
        rule = definitions[name]
        targets.append(
            {
                "artifacts": "undeclared",
                "cache_policy": "disabled",
                "description": rule.description,
                "environment_inputs": "ambient-unbounded",
                "implementation": (
                    "dependency-only"
                    if rule.recipe_line_count == 0 and rule.prerequisites
                    else "native"
                ),
                "line": rule.line,
                "lifecycle": "active" if rule.public else "internal",
                "name": name,
                "owner": "make",
                "owners": ["@value-fabric/sre-leads", "@value-fabric/maintainers"],
                "phony": name in phony,
                "portability": "posix-bash",
                "prerequisites": list(rule.prerequisites),
                "public": rule.public,
                "recipe_line_count": rule.recipe_line_count,
                "recipe_sha256": rule.recipe_sha256,
                "side_effects": "unbounded",
                "visibility": "public" if rule.public else "internal",
            }
        )

    public_count = sum(target["visibility"] == "public" for target in targets)
    phony_count = sum(bool(target["phony"]) for target in targets)
    return {
        "metadata": {
            "internal_target_count": len(targets) - public_count,
            "phony_target_count": phony_count,
            "public_target_count": public_count,
            "schema_version": 1,
            "source": makefile.name,
            "source_sha256": hashlib.sha256(source_bytes).hexdigest(),
            "target_count": len(targets),
        },
        "targets": targets,
    }


def render_inventory(inventory: dict[str, object]) -> str:
    """Render the canonical JSON representation."""

    return json.dumps(inventory, indent=2, sort_keys=True, ensure_ascii=True) + "\n"


def _check_output(output: Path, generated: str) -> int:
    if not output.exists():
        print(f"ERROR: task inventory does not exist: {output}", file=sys.stderr)
        print(
            "Run scripts/ci/generate_make_task_inventory.py --write.", file=sys.stderr
        )
        return 1

    existing = output.read_text(encoding="utf-8")
    if existing == generated:
        print(f"Task inventory is current: {output}")
        return 0

    print(f"ERROR: task inventory is stale: {output}", file=sys.stderr)
    diff = difflib.unified_diff(
        existing.splitlines(),
        generated.splitlines(),
        fromfile=str(output),
        tofile=f"{output} (generated)",
        lineterm="",
    )
    print("\n".join(diff), file=sys.stderr)
    print("Run scripts/ci/generate_make_task_inventory.py --write.", file=sys.stderr)
    return 1


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate or validate the checked-in root Make task inventory."
    )
    parser.add_argument("--makefile", type=Path, default=DEFAULT_MAKEFILE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--check", action="store_true", help="Validate inventory drift (default)."
    )
    mode.add_argument(
        "--write", action="store_true", help="Write the canonical inventory."
    )
    args = parser.parse_args(argv)

    try:
        generated = render_inventory(build_inventory(args.makefile))
    except (InventoryError, UnicodeDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if args.write:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(generated, encoding="utf-8")
        print(f"Wrote task inventory: {args.output}")
        return 0
    return _check_output(args.output, generated)


if __name__ == "__main__":
    raise SystemExit(main())
