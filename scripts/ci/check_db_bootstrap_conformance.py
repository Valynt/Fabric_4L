#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB_FILES = [
    *ROOT.glob("services/*/src/**/database.py"),
    *ROOT.glob("value_fabric/layer*/**/database*.py"),
]

violations: list[str] = []
for path in sorted(set(DB_FILES)):
    text = path.read_text(encoding="utf-8")
    if "neo4j" in text.lower() and "sqlalchemy" not in text.lower():
        continue
    uses_shared = "RuntimeDatabaseAdapter" in text
    intentional = "INTENTIONAL_DB_ADAPTER_BYPASS = True" in text
    if not uses_shared and not intentional:
        violations.append(str(path.relative_to(ROOT)))

if violations:
    print("Non-conforming runtime DB bootstrap modules found:")
    for v in violations:
        print(f" - {v}")
    raise SystemExit(1)

print("DB bootstrap conformance check passed.")
