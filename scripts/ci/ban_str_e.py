#!/usr/bin/env python3
"""
P0: Pre-commit hook to ban str(e) and repr(e) in production Python code.
Both str(exc) and repr(exc) leak potentially sensitive exception data.
Use structured logging (error_type=type(exc).__name__) or sanitized messages instead.
Skips test files, migration scripts, and __pycache__.
"""
import re
import sys
from pathlib import Path


_UNSAFE_PATTERN = re.compile(
    r"(str|repr)\((e|err|exc|error|exception)\b\)", re.IGNORECASE
)
_ALLOWLIST = Path("config/ci/ban_str_e_allowlist.txt")


def load_allowlist(repo_root):
    """Load reviewed exception-string debt entries keyed by path and exact line."""
    allowlist_path = repo_root / _ALLOWLIST
    if not allowlist_path.exists():
        return set()
    entries = set()
    for raw_line in allowlist_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "|" not in line:
            print(f"ERROR: malformed allowlist entry in {_ALLOWLIST}: {raw_line}")
            entries.add(("__malformed__", raw_line))
            continue
        rel_path, code = line.split("|", 1)
        entries.add((rel_path.strip(), code.strip()))
    return entries


def check_file(filepath):
    """Check a single file for str(e) and repr(e) violations."""
    try:
        content = filepath.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    issues = []
    lines = content.splitlines()
    in_logger_call = False
    for lineno, line in enumerate(lines, 1):
        # Allow explicit suppression with inline comment
        if "# ban-str-e-allow" in line:
            continue
        # Skip comments
        code = line.split("#")[0]
        # Skip getattr fallback patterns like getattr(e, "name", str(e))
        if "getattr(" in code:
            continue
        # Track multi-line logger calls with simple paren counting
        if "logger." in code and "(" in code:
            in_logger_call = True
        if in_logger_call:
            # crude paren balance: count opens and closes
            opens = code.count("(")
            closes = code.count(")")
            if closes > opens:
                in_logger_call = False
            continue
        if "extra={" in code and "error" in code:
            continue
        # Allow common internal patterns: error classification, pattern matching, tracing
        if ".lower()" in code:
            continue
        if "in str(" in code or "in repr(" in code:
            continue
        if "span.set_status(" in code:
            continue
        if _UNSAFE_PATTERN.search(code):
            issues.append((lineno, line.strip()))
    return issues


def main():
    exit_code = 0
    # scripts/ci/ban_str_e.py -> repo_root needs 3 levels up
    repo_root = Path(__file__).resolve().parents[2]
    allowlist = load_allowlist(repo_root)
    # Check all Python files in services/ and packages/
    globs = ["services/**/*.py", "packages/**/*.py"]
    for glob_pattern in globs:
        for pyfile in repo_root.glob(glob_pattern):
            # Skip tests, migrations, __pycache__, .venv, node_modules
            path_str = str(pyfile)
            if "test_" in pyfile.name or "__pycache__" in path_str:
                continue
            if "/tests/" in path_str.replace("\\", "/") or "/migrations/" in path_str.replace("\\", "/") or ".venv" in path_str or "node_modules" in path_str:
                continue
            rel_path = pyfile.relative_to(repo_root).as_posix()
            issues = check_file(pyfile)
            for lineno, line in issues:
                if (rel_path, line) in allowlist:
                    continue
                print(f"ERROR: {pyfile}:{lineno}: str(e)/repr(e) leak detected")
                print(f"  {line}")
                exit_code = 1
    if exit_code:
        print("\nstr(exc)/repr(exc)/str(error)/repr(error) leak potentially sensitive exception data.")
        print("Use structured logging (error_type=type(exc).__name__) or sanitized messages instead.")
    # Check tracing-config.yaml for insecure: true
    tracing_config = repo_root / "packages" / "shared" / "src" / "value_fabric" / "shared" / "tracing" / "tracing-config.yaml"
    if tracing_config.exists():
        tc_content = tracing_config.read_text()
        if "insecure: true" in tc_content:
            for lineno, line in enumerate(tc_content.splitlines(), 1):
                if "insecure: true" in line:
                    print(f"ERROR: {tracing_config}:{lineno}: insecure: true found — must use mTLS")
                    exit_code = 1

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
