#!/usr/bin/env python
"""Migrate L1 test imports from value_fabric.layer1.* to layer1_ingestion.*."""

import re
from pathlib import Path


def migrate_imports(file_path: Path) -> int:
    """Migrate imports in a single file. Return 1 if changed, 0 if unchanged."""
    content = file_path.read_text(encoding="utf-8")
    original = content

    patterns = [
        # Import statements
        (r'import value_fabric\.layer1\.([a-z_]+(?:\.[a-z_]+)*)', r'import layer1_ingestion.\1'),
        (r'from value_fabric\.layer1\.([a-z_]+(?:\.[a-z_]+)*) import', r'from layer1_ingestion.\1 import'),
        # String-based imports (e.g., in patch targets)
        (r'"value_fabric\.layer1\.([^"]+)"', r'"layer1_ingestion.\1"'),
        (r"'value_fabric\.layer1\.([^']+)'", r"'layer1_ingestion.\1'"),
    ]

    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content)

    if content != original:
        file_path.write_text(content, encoding="utf-8")
        return 1
    return 0


def main():
    """Migrate all L1 test files."""
    tests_dir = Path("services/layer1-ingestion/tests")
    changed_files = 0

    for test_file in tests_dir.rglob("*.py"):
        if "value_fabric.layer1" in test_file.read_text(encoding="utf-8"):
            if migrate_imports(test_file):
                changed_files += 1
                print(f"Migrated: {test_file}")

    print(f"\nTotal files changed: {changed_files}")


if __name__ == "__main__":
    main()
