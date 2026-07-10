#!/usr/bin/env python3
"""Block raw HTTPException usage outside approved boundary adapters."""

from __future__ import annotations
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCAN_ROOTS = [ROOT / 'services', ROOT / 'value_fabric', ROOT / 'packages' / 'shared' / 'src' / 'value_fabric']
APPROVED_SUBSTRINGS = (
    '/api/', '/tests/', '/test_', '/middleware', '/dependencies.py', '/auth/', '/rate_limiting/'
)


def is_approved(path: Path) -> bool:
    posix = '/' + path.as_posix()
    return any(token in posix for token in APPROVED_SUBSTRINGS)


def find_violations(path: Path) -> list[int]:
    text = path.read_text(encoding='utf-8')
    tree = ast.parse(text, filename=str(path))
    lines = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Raise) and isinstance(node.exc, ast.Call):
            func = node.exc.func
            if isinstance(func, ast.Name) and func.id == 'HTTPException':
                lines.append(node.lineno)
            elif isinstance(func, ast.Attribute) and func.attr == 'HTTPException':
                lines.append(node.lineno)
    return lines


def main() -> int:
    violations: list[str] = []
    for root in SCAN_ROOTS:
        for path in root.rglob('*.py'):
            if any(part in {'.venv','venv','site-packages'} for part in path.parts):
                continue
            if is_approved(path):
                continue
            lines = find_violations(path)
            for line in lines:
                violations.append(f"{path.relative_to(ROOT)}:{line}")
    if violations:
        print('Raw HTTPException raise is only allowed in boundary adapter files. Violations:')
        for v in violations:
            print(f' - {v}')
        return 1
    print('No raw HTTPException violations found outside approved boundary adapters.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
