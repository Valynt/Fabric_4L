#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TARGETS = [
    ROOT / 'k8s' / 'base' / 'postgres-backup-cronjob.yaml',
    ROOT / 'k8s' / 'base' / 'layer4-agents.yml',
    ROOT / 'k8s' / 'base' / 'redis.yml',
    ROOT / 'docker-compose.full.yml',
]

FORBIDDEN_PATTERNS: dict[str, re.Pattern[str]] = {
    'VAULT_DEV_ROOT_TOKEN_ID': re.compile(r'\bVAULT_DEV_ROOT_TOKEN_ID\b'),
    'inline postgres:postgres': re.compile(r'postgres:postgres'),
    'inline redis url without auth': re.compile(r'redis://redis:6379(?:/\d+)?'),
    'forbidden dev auth bypass env vars': re.compile(
        r'\b(?:DEV_AUTH_BYPASS|ALLOW_DEV_AUTH_BYPASS|AUTH_BYPASS_ENABLED|ALLOW_INSECURE_DEV_AUTH_BYPASS)\b'
    ),
}


@dataclass
class Violation:
    file: Path
    line: int
    rule: str
    text: str


def find_violations(files: list[Path]) -> list[Violation]:
    violations: list[Violation] = []
    for file in files:
        if not file.exists():
            continue
        for lineno, line in enumerate(file.read_text(encoding='utf-8').splitlines(), start=1):
            for rule, pattern in FORBIDDEN_PATTERNS.items():
                if pattern.search(line):
                    violations.append(Violation(file=file, line=lineno, rule=rule, text=line.strip()))
    return violations


def main() -> int:
    violations = find_violations(DEFAULT_TARGETS)
    if violations:
        print('❌ Manifest secret hygiene violations detected:')
        for v in violations:
            rel = v.file.relative_to(ROOT)
            print(f' - {rel}:{v.line} [{v.rule}] {v.text}')
        return 1

    print('✅ Manifest secret hygiene checks passed.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
