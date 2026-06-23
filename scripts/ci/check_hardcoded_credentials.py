#!/usr/bin/env python3
"""CI gate: reject hardcoded default credentials in service source files.

Scans runtime source files for known insecure default password patterns
(e.g., postgres:postgres) and fails if any are found outside of allowed
baseline paths.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

# Patterns that indicate hardcoded default/insecure credentials
PATTERNS = [
    "postgres:postgres",
]

# Files/paths that are allowed to contain placeholder documentation or test fixtures.
# Test fixtures using fake credentials are standard practice and excluded.
ALLOWLIST = {
    # All test trees (matches anywhere in path)
    "/tests/",
    # Migration scripts that read from environment
    "services/layer4-agents/migrations/env.py",
    # Documentation
    "services/layer4-agents/docs/",
    "services/layer4-agents/TASK4_IMPLEMENTATION_SUMMARY.md",
    "services/layer4-agents/README.md",
    # This script itself
    "scripts/ci/check_hardcoded_credentials.py",
    # Pre-existing hardcoded defaults in other services (tracked as debt).
    # These config modules carry a dev-only default that is fail-closed in
    # production via validate_production_safety (the URL is rejected when the
    # environment is production-like), so the default cannot reach production.
    "services/layer1-ingestion/src/shared/config.py",
    "services/layer1-ingestion/src/layer1_ingestion/shared/config.py",
    "services/layer7-billing/src/layer7_billing/database.py",
    # Validator pattern lists (false positives)
    "services/layer4-agents/src/layer4_agents/config/settings.py",
}


def _is_allowlisted(rel_path: str) -> bool:
    # Normalize to forward slashes
    normalized = rel_path.replace("\\", "/")
    # pytest modules (``*_test.py`` / ``test_*.py``) are test fixtures regardless
    # of directory; fake credentials in fixtures are standard practice.
    filename = normalized.rsplit("/", 1)[-1]
    if filename.endswith("_test.py") or filename.startswith("test_"):
        return True
    for allowed in ALLOWLIST:
        if allowed in normalized:
            return True
    return False


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]

    offenders: list[tuple[str, int, str]] = []

    for pattern in PATTERNS:
        try:
            result = subprocess.run(
                ["rg", "-n", "-i", "--type", "py", pattern, "services/", "packages/"],
                cwd=repo_root,
                capture_output=True,
                text=True,
                timeout=30,
            )
        except FileNotFoundError:
            print("ERROR: ripgrep (rg) is required for this check.", file=sys.stderr)
            return 1
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError) as e:
            print(f"ERROR: Credential scan failed: {e}", file=sys.stderr)
            return 1

        for line in result.stdout.splitlines():
            if not line.strip():
                continue
            # rg output format: path:lineno:match
            parts = line.split(":", 2)
            if len(parts) < 3:
                continue
            rel_path, lineno_str, match_line = parts[0], parts[1], parts[2]
            if _is_allowlisted(rel_path):
                continue
            # Skip __pycache__
            if "__pycache__" in rel_path:
                continue
            offenders.append((rel_path, int(lineno_str), match_line.strip()))

    if offenders:
        print("ERROR: Hardcoded insecure credentials detected:", file=sys.stderr)
        for rel_path, lineno, line in offenders:
            print(f"  {rel_path}:{lineno}: {line}", file=sys.stderr)
        print(
            "\nFix: remove hardcoded defaults, use environment variables or secrets management.",
            file=sys.stderr,
        )
        return 1

    print("OK: No hardcoded insecure credentials detected.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
