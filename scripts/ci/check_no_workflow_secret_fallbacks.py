#!/usr/bin/env python3
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / '.github' / 'workflows'

PATTERNS = {
    'transition_todo': re.compile(r'#infisical-transition'),
    'openai_fallback': re.compile(r'OPENAI_API_KEY\s*=\s*(sk-ci-test-key|dummy-key-for-ci|test-key|\$\{\{\s*secrets\.OPENAI_API_KEY\s*\}\})'),
    'jwt_fallback': re.compile(r'JWT_SECRET\s*=\s*(ci-jwt-secret[^\s]*|test-jwt-secret|\$\{\{\s*secrets\.[A-Z0-9_]*JWT_SECRET\s*\}\})'),
    'default_secret_expansion': re.compile(r'\$\{[A-Z0-9_]+:-\$\{\{\s*secrets\.[^}]+\}\}\}'),
    'fallback_warning': re.compile(r'falling back to GitHub Secrets', re.IGNORECASE),
}

violations = []
for wf in sorted(WORKFLOWS.glob('*.yml')):
    for i, line in enumerate(wf.read_text().splitlines(), start=1):
        for name, pattern in PATTERNS.items():
            if pattern.search(line):
                violations.append((wf, i, name, line.strip()))

if violations:
    print('Workflow secret fallback policy violations detected:')
    for wf, line_no, name, line in violations:
        print(f'- {wf.relative_to(ROOT)}:{line_no} [{name}] {line}')
    sys.exit(1)

print('No workflow secret fallback patterns detected.')
