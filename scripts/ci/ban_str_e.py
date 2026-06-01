#!/usr/bin/env python3
"""
P0: Pre-commit hook to ban str(e) in production Python code.
Use repr(e) instead to prevent information leakage.
Skips test files, migration scripts, and __pycache__.
"""
import re
import sys
from pathlib import Path


def check_file(filepath):
    """Check a single file for str(e) violations."""
    content = filepath.read_text()
    issues = []
    for lineno, line in enumerate(content.splitlines(), 1):
        # Skip comments
        code = line.split("#")[0]
        # Match str(e), str(err), str(exc), str(error), str(exception) etc.
        # but not getattr(e, "name", str(e)) or safe identifiers like str(extract).
        if "getattr(" in code:
            continue  # heuristic: skip lines with getattr to avoid false positives
        if re.search(r"str\((e|err|exc|error|exception)\b\)", code, re.IGNORECASE):
            # Skip if it's already repr(e)
            if "repr(e)" not in code:
                issues.append((lineno, line.strip()))
    return issues


def main():
    exit_code = 0
    # Check all Python files in services/
    repo_root = Path(__file__).parent.parent
    for pyfile in repo_root.glob("services/**/*.py"):
        # Skip tests, migrations handled separately, __pycache__
        if "test_" in pyfile.name or "__pycache__" in str(pyfile):
            continue
        issues = check_file(pyfile)
        for lineno, line in issues:
            print(f"ERROR: {pyfile}:{lineno}: str(e) detected - use repr(e) instead")
            print(f"  {line}")
            exit_code = 1
    if exit_code:
        print("\nstr(exc)/str(error)/str(e) leaks potentially sensitive exception data to logs/responses.")
        print("Use repr(e) instead, which shows the exception type and message safely.")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
