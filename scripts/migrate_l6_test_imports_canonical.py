#!/usr/bin/env python3
"""Migrate L6 test imports from value_fabric.layer6.* to layer6_benchmarks.*"""

import re
from pathlib import Path
from typing import Dict, List


def migrate_imports(file_path: Path) -> int:
    """Migrate imports in a single file. Returns number of changes made."""
    content = file_path.read_text(encoding="utf-8")
    original = content
    
    # Import patterns to replace
    patterns = [
        (r'import value_fabric\.layer6\.database as (\w+)', r'import layer6_benchmarks.database as \1'),
        (r'from value_fabric\.layer6\.api\.main import', r'from layer6_benchmarks.api.main import'),
        (r'from value_fabric\.layer6\.api\.schemas import', r'from layer6_benchmarks.api.schemas import'),
        (r'from value_fabric\.layer6\.api\.deps import', r'from layer6_benchmarks.api.deps import'),
        (r'from value_fabric\.layer6\.models\.benchmark_dataset import', r'from layer6_benchmarks.models.benchmark_dataset import'),
        (r'from value_fabric\.layer6\.metrics\.prometheus_metrics import', r'from layer6_benchmarks.metrics.prometheus_metrics import'),
        (r'from value_fabric\.layer6\.observability\.metrics_contract import', r'from layer6_benchmarks.observability.metrics_contract import'),
        (r'from value_fabric\.layer6\.settings import', r'from layer6_benchmarks.settings import'),
        (r'from value_fabric\.layer6\.api\.startup_logging import', r'from layer6_benchmarks.api.startup_logging import'),
        (r'from value_fabric\.layer6\.repositories\.benchmark_repository import', r'from layer6_benchmarks.repositories.benchmark_repository import'),
        (r'import value_fabric\.layer6\.api\.main as (\w+)', r'import layer6_benchmarks.api.main as \1'),
        # String-based imports (e.g., __import__ calls)
        (r'"value_fabric\.layer6\.([^"]+)"', r'"layer6_benchmarks.\1"'),
        (r"'value_fabric\.layer6\.([^']+)'", r"'layer6_benchmarks.\1'"),
    ]
    
    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content)
    
    if content != original:
        file_path.write_text(content, encoding="utf-8")
        return 1
    return 0


def main():
    test_dir = Path("services/layer6-benchmarks/tests")
    
    if not test_dir.exists():
        print(f"Test directory not found: {test_dir}")
        return
    
    # Find all test files
    test_files = list(test_dir.glob("test_*.py")) + list(test_dir.glob("*_test.py"))
    
    changes = 0
    for test_file in test_files:
        changed = migrate_imports(test_file)
        if changed:
            print(f"Migrated: {test_file}")
            changes += changed
    
    print(f"\nTotal files changed: {changes}")
    print(f"Total test files processed: {len(test_files)}")


if __name__ == "__main__":
    main()
