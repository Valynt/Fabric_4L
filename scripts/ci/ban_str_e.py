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
            issues = check_file(pyfile)
            for lineno, line in issues:
                print(f"ERROR: {pyfile}:{lineno}: str(e)/repr(e) leak detected")
                print(f"  {line}")
                exit_code = 1
    if exit_code:
        print("\nstr(exc)/repr(exc)/str(error)/repr(error) leak potentially sensitive exception data.")
        print("Use structured logging (error_type=type(exc).__name__) or sanitized messages instead.")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
