from __future__ import annotations

import argparse
import fnmatch
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

DEFAULT_BASELINE = Path("config/ci/type_escape_baseline.json")
EXCLUDED_PATTERNS = (
    "apps/web/src/api/generated/**",
    "packages/platform-contract/src/typescript/generated/**",
    "sdk/python/src/valuefabric/generated/**",
    "**/__pycache__/**",
    "**/.mypy_cache/**",
    "**/node_modules/**",
    "**/dist/**",
    "**/build/**",
)
SCAN_EXTENSIONS = {".py", ".ts", ".tsx"}
PY_ANY_RE = re.compile(r"\bAny\b")
PY_TYPE_IGNORE_RE = re.compile(r"#\s*type:\s*ignore(?:\[[^\]]+\])?")
TS_AS_ANY_RE = re.compile(r"\bas\s+any\b")


@dataclass(frozen=True, order=True)
class Finding:
    path: str
    line: int
    kind: str
    text: str

    @property
    def key(self) -> str:
        return f"{self.path}:{self.line}:{self.kind}:{self.text.strip()}"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def matches_any(path: str, patterns: list[str] | tuple[str, ...]) -> bool:
    return any(fnmatch.fnmatch(path, pattern) for pattern in patterns)


def iter_tracked_files(root: Path) -> list[Path]:
    proc = subprocess.run(
        ["git", "ls-files"],
        cwd=root,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )
    files: list[Path] = []
    for line in proc.stdout.splitlines():
        path = root / line
        if path.suffix in SCAN_EXTENSIONS and not matches_any(line, EXCLUDED_PATTERNS):
            files.append(path)
    return files


def scan_file(path: Path, root: Path) -> list[Finding]:
    relative = rel(path, root)
    findings: list[Finding] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError:
        lines = path.read_text().splitlines()
    for line_no, line in enumerate(lines, start=1):
        if path.suffix == ".py":
            if PY_TYPE_IGNORE_RE.search(line):
                findings.append(Finding(relative, line_no, "python-type-ignore", line.strip()))
            if PY_ANY_RE.search(line):
                findings.append(Finding(relative, line_no, "python-any", line.strip()))
        elif path.suffix in {".ts", ".tsx"} and TS_AS_ANY_RE.search(line):
            findings.append(Finding(relative, line_no, "typescript-as-any", line.strip()))
    return findings


def scan(root: Path, allowlisted_boundary_files: list[str]) -> list[Finding]:
    findings: list[Finding] = []
    for path in iter_tracked_files(root):
        relative = rel(path, root)
        if matches_any(relative, allowlisted_boundary_files):
            continue
        findings.extend(scan_file(path, root))
    return sorted(findings)


def load_baseline(path: Path) -> dict:
    if not path.exists():
        return {"allowlisted_boundary_files": [], "occurrences": []}
    return json.loads(path.read_text(encoding="utf-8"))


def write_baseline(path: Path, findings: list[Finding], allowlisted_boundary_files: list[str]) -> None:
    payload = {
        "description": "Generated baseline for approved Python Any/type: ignore and TypeScript as any occurrences. Generated files are excluded by scripts/ci/type_escape_ratchet.py.",
        "excluded_patterns": list(EXCLUDED_PATTERNS),
        "allowlisted_boundary_files": allowlisted_boundary_files,
        "occurrences": [asdict(finding) for finding in findings],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fail on net-new unapproved type escapes.")
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument("--update", action="store_true", help="Regenerate the checked-in baseline.")
    args = parser.parse_args(argv)

    root = repo_root()
    baseline_path = args.baseline if args.baseline.is_absolute() else root / args.baseline
    baseline = load_baseline(baseline_path)
    allowlisted_boundary_files = list(baseline.get("allowlisted_boundary_files", []))
    findings = scan(root, allowlisted_boundary_files)

    if args.update:
        write_baseline(baseline_path, findings, allowlisted_boundary_files)
        print(f"Updated {baseline_path.relative_to(root)} with {len(findings)} approved occurrences.")
        return 0

    approved = {
        f"{item['path']}:{item['line']}:{item['kind']}:{item['text'].strip()}"
        for item in baseline.get("occurrences", [])
    }
    current = {finding.key for finding in findings}
    new = [finding for finding in findings if finding.key not in approved]
    stale = sorted(approved - current)

    if new:
        print("Net-new unapproved type escapes detected:")
        for finding in new[:100]:
            print(f"  {finding.path}:{finding.line}: {finding.kind}: {finding.text}")
        if len(new) > 100:
            print(f"  ... and {len(new) - 100} more")
        print("Regenerate the baseline only after approval: python scripts/ci/type_escape_ratchet.py --update")
        return 1

    if stale:
        print(f"Type escape baseline has {len(stale)} stale approved occurrence(s); run with --update after cleanup.")
        return 1

    print(f"Type escape ratchet passed: {len(findings)} approved occurrence(s), no net-new escapes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
