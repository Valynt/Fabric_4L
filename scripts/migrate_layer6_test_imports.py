#!/usr/bin/env python3
"""Revert Layer 6 test imports back to value_fabric.layer6 facade.

The canonical layer6_benchmarks module structure requires Python path setup
that the facade currently provides. Direct imports fail without proper
PYTHONPATH configuration.
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent

# Reverse mapping
REVERSE_MAPPING = {
    "layer6_benchmarks": "value_fabric.layer6",
}

def revert_file(file_path: Path) -> int:
    """Revert L6 imports in a single file. Returns number of changes made."""
    content = file_path.read_text(encoding="utf-8")
    original_content = content
    changes = 0
    
    for new, old in REVERSE_MAPPING.items():
        # Replace "from layer6_benchmarks" imports
        pattern = rf"from {new}\."
        replacement = f"from {old}."
        if re.search(pattern, content):
            content = re.sub(pattern, replacement, content)
            changes += 1
            
        # Replace "import layer6_benchmarks" imports
        pattern = rf"import {new}\."
        replacement = f"import {old}."
        if re.search(pattern, content):
            content = re.sub(pattern, replacement, content)
            changes += 1
            
        # Replace "import layer6_benchmarks as" imports
        pattern = rf"import {new} as"
        replacement = f"import {old} as"
        if re.search(pattern, content):
            content = re.sub(pattern, replacement, content)
            changes += 1
    
    if changes > 0:
        file_path.write_text(content, encoding="utf-8")
        print(f"Reverted {file_path.relative_to(REPO_ROOT)} ({changes} changes)")
    
    return changes

def main():
    """Revert L6 test imports."""
    tests_dir = REPO_ROOT / "services" / "layer6-benchmarks" / "tests"
    total_changes = 0
    
    for py_file in tests_dir.rglob("*.py"):
        changes = revert_file(py_file)
        total_changes += changes
    
    print(f"\nTotal changes: {total_changes}")

if __name__ == "__main__":
    main()
