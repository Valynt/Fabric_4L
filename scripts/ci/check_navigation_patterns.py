#!/usr/bin/env python3
"""
Navigation Pattern Guardrail

Detects direct path navigation patterns that should use state-based navigation instead.
Per CONTRACT.md §2.6: UI State Progression and Route Model

Classification:
- hard_violations: Direct path navigation (navigateTo('/path'), router.push('/path'), etc.)
- legacy_useNavigate: Direct useNavigate() calls outside approved wrappers
- approved_state_navigation: Valid state-based navigation (navigateTo('route-state'))
- exempted: Explicitly ignored lines/files

Usage:
    python scripts/ci/check_navigation_patterns.py [--strict]

Exit codes:
    0 - No hard violations (or non-strict mode)
    1 - Hard violations found (strict mode only)
"""

import argparse
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Finding:
    """A single navigation pattern finding."""
    line_num: int
    category: str
    pattern_type: str
    line: str


def find_frontend_src() -> Path:
    """Locate the frontend source directory."""
    repo_root = Path(__file__).parent.parent.parent
    # Try new apps/web path first, then fall back to legacy frontend/client path
    frontend_src = repo_root / "apps" / "web" / "src"
    if not frontend_src.exists():
        frontend_src = repo_root / "frontend" / "client" / "src"
    if not frontend_src.exists():
        raise FileNotFoundError(f"Frontend source not found: tried {repo_root / 'apps' / 'web' / 'src'} and {repo_root / 'frontend' / 'client' / 'src'}")
    return frontend_src


def should_skip_file(file_path: Path, content: str) -> bool:
    """Determine if a file should be skipped from checking."""
    relative = str(file_path)

    # Skip navigation service implementation itself
    if "navigation" in relative.lower() and "service" in relative.lower():
        return True

    # Skip useNavigation hook (approved wrapper)
    if "navigation" in relative.lower() and "useNavigation" in relative:
        return True

    # Skip test files that intentionally validate legacy patterns
    if ".test." in relative or ".spec." in relative:
        return True

    # Skip files with explicit exemption comment at top
    if content.strip().startswith("// navigation-guardrail: exempt"):
        return True

    return False


def find_navigation_patterns(content: str) -> list[Finding]:
    """
    Find navigation patterns and classify them.
    Returns list of Finding objects with category classification.
    """
    findings = []
    lines = content.split("\n")

    # Hard violation patterns (direct path navigation)
    hard_violation_patterns = [
        ("navigateTo-backtick-path", r"navigateTo\s*\(\s*`[^`]*\/"),  # navigateTo(`/path
        ("navigateTo-double-path", r'navigateTo\s*\(\s*"[^"]*\/'),   # navigateTo("/path
        ("navigateTo-single-path", r"navigateTo\s*\(\s*'[^']*\/"),    # navigateTo('/path
        ("navigate-direct", r"\bnavigate\s*\(\s*[\"'`]\s*\/"),    # navigate("/path
        ("router-push-path", r"router\.push\s*\(\s*[\"'`]\s*\/"), # router.push("/path
        ("window-location", r"window\.location\.(href|assign|replace)"),
        ("location-direct", r"location\.(assign|replace)\s*\(\s*[\"'`]\s*\/"),
    ]

    # Legacy useNavigate patterns
    legacy_patterns = [
        ("useNavigate", r"\buseNavigate\s*\("),
    ]

    # Approved state navigation patterns (for counting, not violations)
    approved_patterns = [
        ("navigateTo-state", r"navigateTo\s*\(\s*['\"]\w+['\"]\s*[,)]"),  # navigateTo('state')
    ]

    for line_num, line in enumerate(lines, start=1):
        stripped = line.strip()
        
        # Skip comments
        if stripped.startswith("//") or stripped.startswith("*"):
            continue

        # Check for line-level exemption
        if "navigation-guardrail: ignore" in line or "navigation-guardrail: ignore" in stripped:
            findings.append(Finding(line_num, "exempted", "line-exempt", line.strip()))
            continue

        # Check hard violations first
        found = False
        for pattern_name, pattern in hard_violation_patterns:
            if re.search(pattern, line):
                findings.append(Finding(line_num, "hard_violation", pattern_name, line.strip()))
                found = True
                break

        # Check legacy useNavigate (only if no hard violation found)
        if not found:
            for pattern_name, pattern in legacy_patterns:
                if re.search(pattern, line):
                    findings.append(Finding(line_num, "legacy_useNavigate", pattern_name, line.strip()))
                    found = True
                    break

        # Count approved state navigation (only if no violation found)
        if not found:
            for pattern_name, pattern in approved_patterns:
                if re.search(pattern, line):
                    findings.append(Finding(line_num, "approved_state_navigation", pattern_name, line.strip()))
                    break

    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="Check for direct path navigation patterns")
    parser.add_argument("--strict", action="store_true", help="Exit with error code if hard violations found")
    args = parser.parse_args()

    try:
        frontend_src = find_frontend_src()
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        return 1

    total_files = 0
    file_findings: defaultdict[Path, list[Finding]] = defaultdict(list)
    
    # Category counters
    category_counts: defaultdict[str, int] = defaultdict(int)
    category_files: defaultdict[str, set[Path]] = defaultdict(set)

    # Check TypeScript/TSX files
    for file_path in frontend_src.rglob("*.ts*"):
        # Skip node_modules and type definitions
        if "node_modules" in str(file_path) or file_path.suffix == ".d.ts":
            continue

        try:
            content = file_path.read_text(encoding="utf-8")
        except (IOError, UnicodeDecodeError):
            continue

        if should_skip_file(file_path, content):
            continue

        total_files += 1
        findings = find_navigation_patterns(content)

        if findings:
            rel_path = file_path.relative_to(frontend_src.parent)
            file_findings[rel_path] = findings
            
            for finding in findings:
                category_counts[finding.category] += 1
                category_files[finding.category].add(rel_path)

    # Report findings
    print("=" * 70)
    print("Navigation Pattern Guardrail Report")
    print("=" * 70)
    print()

    print("CATEGORY BREAKDOWN:")
    print("-" * 70)
    for category in ["hard_violation", "legacy_useNavigate", "approved_state_navigation", "exempted"]:
        count = category_counts.get(category, 0)
        files = len(category_files.get(category, set()))
        print(f"  {category:30} {count:4} occurrences in {files:3} files")
    print()

    # Report hard violations (these are the real issues)
    hard_violations = [f for f in file_findings.items() if any(f2.category == "hard_violation" for f2 in f[1])]
    if hard_violations:
        print("HARD VIOLATIONS (Direct Path Navigation):")
        print("-" * 70)
        for file_path, findings in hard_violations:
            print(f"\n{file_path}:")
            for finding in findings:
                if finding.category == "hard_violation":
                    print(f"  Line {finding.line_num}: [{finding.pattern_type}] {finding.line[:70]}...")
    else:
        print("HARD VIOLATIONS: None found")
    print()

    # Report legacy useNavigate
    legacy_files = [f for f in file_findings.items() if any(f2.category == "legacy_useNavigate" for f2 in f[1])]
    if legacy_files:
        print("LEGACY useNavigate (Direct useNavigate calls):")
        print("-" * 70)
        for file_path, findings in legacy_files:
            print(f"\n{file_path}:")
            for finding in findings:
                if finding.category == "legacy_useNavigate":
                    print(f"  Line {finding.line_num}: {finding.line[:70]}...")
    else:
        print("LEGACY useNavigate: None found")
    print()

    # Summary
    print("-" * 70)
    print("SUMMARY:")
    print(f"  Total files scanned: {total_files}")
    print(f"  Hard violations: {category_counts.get('hard_violation', 0)}")
    print(f"  Legacy useNavigate: {category_counts.get('legacy_useNavigate', 0)}")
    print(f"  Approved state navigation: {category_counts.get('approved_state_navigation', 0)} (not a violation)")
    print(f"  Exempted: {category_counts.get('exempted', 0)}")
    print("-" * 70)
    print()

    # Migration guidance
    if hard_violations or legacy_files:
        print("MIGRATION RECOMMENDATIONS:")
        print("  Replace direct paths with state-based navigation:")
        print("    - navigateTo('/path') -> navigateTo('route-state')")
        print("    - navigateTo(`/path/${id}`) -> navigateTo('route-state', { id })")
        print("    - useNavigate() -> useNavigation() hook")
        print()
        print("  To exempt a line: add '// navigation-guardrail: ignore' comment")
        print("  To exempt a file: add '// navigation-guardrail: exempt' at top")
        print()

    # Exit code based on strict mode and hard violations
    hard_violation_count = category_counts.get('hard_violation', 0)
    legacy_count = category_counts.get('legacy_useNavigate', 0)
    
    if args.strict and (hard_violation_count > 0 or legacy_count > 0):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
