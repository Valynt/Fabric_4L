#!/usr/bin/env python3
"""
Inventory script for value_fabric.layer* facade imports.

This script scans the codebase for all imports from the deprecated value_fabric.layer*
namespace and generates a detailed report. It does NOT fail CI - it only reports
the current state to establish a baseline for migration.

Usage:
    python scripts/ci/inventory_value_fabric_facade.py
"""

import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

REPO_ROOT = Path(__file__).parent.parent.parent

# Patterns to match
IMPORT_PATTERNS = [
    r"from value_fabric\.layer(\d)",
    r"import value_fabric\.layer(\d)",
]

# File type classification
FILE_TYPE_MAP = {
    "tests/": "test",
    "services/": "service",
    "scripts/": "ci_script",
    "docs/": "documentation",
    "k8s/": "kubernetes",
    "packages/": "package",
}


def classify_file(file_path: Path) -> str:
    """Classify a file by its directory path."""
    relative_path = file_path.relative_to(REPO_ROOT)
    path_str = str(relative_path).replace("\\", "/")  # Normalize path separators
    
    for prefix, file_type in FILE_TYPE_MAP.items():
        if path_str.startswith(prefix):
            return file_type
    
    return "other"


def scan_file(file_path: Path) -> List[Tuple[str, int, str]]:
    """
    Scan a single file for value_fabric.layer* imports.
    
    Returns:
        List of (layer_number, line_number, matched_line)
    """
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception:
        return []
    
    matches = []
    lines = content.split("\n")
    
    for line_num, line in enumerate(lines, 1):
        for pattern in IMPORT_PATTERNS:
            if re.search(pattern, line):
                # Extract layer number
                match = re.search(r"layer(\d)", line)
                if match:
                    layer_num = match.group(1)
                    matches.append((layer_num, line_num, line.strip()))
                    break  # Don't count same line multiple times
    
    return matches


def scan_directory(directory: Path) -> Dict[str, Dict]:
    """
    Scan directory recursively for Python files with value_fabric.layer* imports.
    
    Returns:
        Dict with structure:
        {
            "by_layer": { "1": count, "2": count, ... },
            "by_file_type": { "test": count, "service": count, ... },
            "by_file": { "path/to/file.py": [matches], ... },
            "total_files": int,
            "total_imports": int
        }
    """
    results = {
        "by_layer": defaultdict(int),
        "by_file_type": defaultdict(int),
        "by_file": {},
        "total_files": 0,
        "total_imports": 0,
    }
    
    for py_file in directory.rglob("*.py"):
        matches = scan_file(py_file)
        if matches:
            file_type = classify_file(py_file)
            results["by_file_type"][file_type] += 1
            results["by_file"][str(py_file.relative_to(REPO_ROOT))] = matches
            results["total_files"] += 1
            
            for layer_num, line_num, line in matches:
                results["by_layer"][layer_num] += 1
                results["total_imports"] += 1
    
    return results


def generate_report(results: Dict) -> str:
    """Generate a markdown report from scan results."""
    report = []
    report.append("# Value Fabric Facade Import Inventory")
    report.append("")
    report.append(f"Generated: {__import__('datetime').datetime.now().isoformat()}")
    report.append("")
    
    # Summary
    report.append("## Summary")
    report.append("")
    report.append(f"- **Total files with facade imports**: {results['total_files']}")
    report.append(f"- **Total facade import statements**: {results['total_imports']}")
    report.append("")
    
    # By layer
    report.append("## Imports by Layer")
    report.append("")
    report.append("| Layer | Count |")
    report.append("|-------|-------|")
    for layer in sorted(results["by_layer"].keys()):
        count = results["by_layer"][layer]
        report.append(f"| {layer} | {count} |")
    report.append("")
    
    # By file type
    report.append("## Imports by File Type")
    report.append("")
    report.append("| File Type | Count |")
    report.append("|-----------|-------|")
    for file_type in sorted(results["by_file_type"].keys()):
        count = results["by_file_type"][file_type]
        report.append(f"| {file_type} | {count} |")
    report.append("")
    
    # Detailed file listing
    report.append("## Files with Facade Imports")
    report.append("")
    
    for file_path in sorted(results["by_file"].keys()):
        matches = results["by_file"][file_path]
        file_type = classify_file(REPO_ROOT / file_path)
        
        report.append(f"### `{file_path}` ({file_type})")
        report.append("")
        report.append(f"**Total imports**: {len(matches)}")
        report.append("")
        report.append("| Layer | Line | Import Statement |")
        report.append("|-------|------|-----------------|")
        
        for layer_num, line_num, line in matches:
            # Truncate long lines
            display_line = line if len(line) <= 80 else line[:77] + "..."
            report.append(f"| {layer_num} | {line_num} | `{display_line}` |")
        
        report.append("")
    
    # Runtime vs test classification
    report.append("## Runtime vs Test Classification")
    report.append("")
    runtime_count = results["by_file_type"].get("service", 0)
    test_count = results["by_file_type"].get("test", 0)
    ci_count = results["by_file_type"].get("ci_script", 0)
    
    report.append(f"- **Runtime/Service imports**: {runtime_count}")
    report.append(f"- **Test imports**: {test_count}")
    report.append(f"- **CI Script imports**: {ci_count}")
    report.append("")
    
    # Migration priority
    report.append("## Migration Priority")
    report.append("")
    report.append("Based on file type classification:")
    report.append("")
    report.append("1. **HIGH PRIORITY - Runtime/Service code**")
    report.append(f"   - {runtime_count} files")
    report.append("   - Must migrate first to ensure services work without facades")
    report.append("")
    report.append("2. **MEDIUM PRIORITY - CI Scripts**")
    report.append(f"   - {ci_count} files")
    report.append("   - Migrate in batches by category")
    report.append("")
    report.append("3. **LOWER PRIORITY - Test code**")
    report.append(f"   - {test_count} files")
    report.append("   - Migrate layer by layer after runtime is clean")
    report.append("")
    
    return "\n".join(report)


def main():
    """Main entry point."""
    print("Scanning for value_fabric.layer* facade imports...")
    
    results = scan_directory(REPO_ROOT)
    
    # Generate report
    report = generate_report(results)
    
    # Write report
    report_dir = REPO_ROOT / "reports"
    report_dir.mkdir(exist_ok=True)
    report_path = report_dir / "value-fabric-facade-inventory.md"
    
    report_path.write_text(report, encoding="utf-8")
    
    print(f"Report generated: {report_path}")
    print(f"Total files with facade imports: {results['total_files']}")
    print(f"Total facade import statements: {results['total_imports']}")
    
    # Print summary to stdout
    print("\n=== SUMMARY ===")
    print(f"By layer: {dict(results['by_layer'])}")
    print(f"By file type: {dict(results['by_file_type'])}")


if __name__ == "__main__":
    main()
