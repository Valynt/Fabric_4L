#!/usr/bin/env python3
"""Production-readiness language gate: flag unqualified readiness claims.

Scans markdown, text, and PR templates for risky phrases.
Does not ban them globally; requires approved boundary qualifiers.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

SCAN_ROOTS = (
    REPO_ROOT / "reports",
    REPO_ROOT / "docs",
    REPO_ROOT / ".github",
)

SKIP_DIRS = {"__pycache__", ".git", "node_modules"}

# Phrases that require boundary language when used in claims
RISKY_PHRASES = (
    r"\bproduction ready\b",
    r"\bGA ready\b",
    r"\bfully complete\b",
    r"\benterprise ready\b",
    r"\blaunch ready\b",
    r"\ball gates pass\b",
    r"\ball gates passed\b",
)

# Approved boundary qualifiers that make the phrase acceptable
APPROVED_QUALIFIERS = (
    r"for the tested scope",
    r"production readiness is not claimed",
    r"supports production-readiness review",
    r"blocked by the following gates",
    r"not production ready",
    r"not claimed",
    r"boundary language",
    r"ADR required",
)

FILE_PATTERNS = (".md", ".txt", ".yml", ".yaml")


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    category: str
    message: str


def _iter_files():
    import os
    for root in SCAN_ROOTS:
        if not root.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for fname in filenames:
                if fname.endswith(FILE_PATTERNS):
                    yield Path(dirpath) / fname


def _has_qualifier(window: str) -> bool:
    return any(re.search(q, window, re.IGNORECASE) for q in APPROVED_QUALIFIERS)


def scan() -> list[Finding]:
    findings: list[Finding] = []

    for path in _iter_files():
        rel = str(path.relative_to(REPO_ROOT))
        source = path.read_text(encoding="utf-8", errors="ignore")
        lines = source.splitlines()

        for i, line in enumerate(lines, start=1):
            for phrase_re in RISKY_PHRASES:
                for m in re.finditer(phrase_re, line, re.IGNORECASE):
                    # Skip if the match is inside quotes or backticks (documented/discussed, not claimed)
                    before = line[max(0, m.start() - 1) : m.start()]
                    after = line[m.end() : min(len(line), m.end() + 1)]
                    if before in ('"', "'", "`") or after in ('"', "'", "`"):
                        continue
                    # Extract a window of surrounding lines for qualifier detection
                    start = max(0, i - 3)
                    end = min(len(lines), i + 3)
                    window = "\n".join(lines[start:end])
                    if not _has_qualifier(window):
                        findings.append(Finding(
                            rel, i, "unqualified_readiness_claim",
                            f"Unqualified readiness phrase: '{m.group(0)}'"
                        ))

    seen = set()
    deduped = []
    for f in findings:
        key = (f.path, f.line, f.category, f.message)
        if key not in seen:
            seen.add(key)
            deduped.append(f)

    return deduped


BASELINE_PATH = REPO_ROOT / "docs" / "reference" / "readiness-language-baseline.json"


def _load_baseline() -> set[tuple[str, int, str, str]]:
    if not BASELINE_PATH.exists():
        return set()
    data = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    return {
        (str(item["path"]).replace("\\", "/"), int(item["line"]), str(item["category"]), str(item["message"]))
        for item in data.get("findings", [])
    }


def _subtract_baseline(
    findings: list[Finding], baseline: set[tuple[str, int, str, str]]
) -> list[Finding]:
    return [
        f for f in findings
        if (f.path.replace("\\", "/"), f.line, f.category, f.message) not in baseline
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--use-baseline", action="store_true")
    args = parser.parse_args(argv)

    findings = scan()
    if args.use_baseline:
        baseline = _load_baseline()
        findings = _subtract_baseline(findings, baseline)

    if args.json:
        print(json.dumps([asdict(f) for f in findings], indent=2))
    else:
        print(f"Readiness language findings: {len(findings)}")
        for f in findings:
            print(f"  [{f.category}] {f.path}:{f.line} :: {f.message}")

    return 1 if args.strict and findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
