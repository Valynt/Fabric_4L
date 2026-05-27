#!/usr/bin/env python3
from pathlib import Path
import re
import sys

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
]
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
    sys.exit(1)

print("No deprecated custom tracer imports found.")
