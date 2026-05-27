#!/usr/bin/env python3
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCAN_DIRS = [
    ROOT / "services/layer3-knowledge",
    ROOT / "services/layer2-extraction",
    ROOT / "services/layer5-ground-truth",
    ROOT / "services/layer6-benchmarks",
]
PATTERNS = [
    re.compile(r"from\s+value_fabric\.layer3\.tracing\.tracer\s+import"),
    re.compile(r"from\s+\.\.?tracing\.tracer\s+import"),
    re.compile(r"import\s+value_fabric\.layer3\.tracing\.tracer(?:\s+as\s+\w+)?"),
    re.compile(r"import\s+\.\.?tracing\.tracer(?:\s+as\s+\w+)?"),
]


def main() -> int:
    violations: list[str] = []
    for scan_dir in SCAN_DIRS:
        for file in scan_dir.rglob("*.py"):
            if "services/layer3-knowledge/src/tracing/" in str(file):
                continue
            text = file.read_text(encoding="utf-8", errors="ignore")
            for pattern in PATTERNS:
                if pattern.search(text):
                    violations.append(str(file.relative_to(ROOT)))
                    break

    if violations:
        print("Deprecated custom tracer imports detected:")
        for v in sorted(set(violations)):
            print(f" - {v}")
        return 1

    print("No deprecated custom tracer imports found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
