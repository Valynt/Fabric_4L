#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TARGETS = [
    ROOT / 'k8s' / 'base' / 'postgres-backup-cronjob.yaml',
    ROOT / 'k8s' / 'base' / 'layer4-agents.yml',
    ROOT / 'k8s' / 'base' / 'redis.yml',
    ROOT / 'docker-compose.full.yml',
    ROOT / 'docker-compose.dev.yml',
    ROOT / '.env.example',
]

STRICT_FORBIDDEN_PATTERNS: dict[str, re.Pattern[str]] = {
    'VAULT_DEV_ROOT_TOKEN_ID': re.compile(r'\bVAULT_DEV_ROOT_TOKEN_ID\b'),
    'inline postgres:postgres': re.compile(r'postgres:postgres'),
    'inline redis url without auth': re.compile(r'redis://redis:6379(?:/\d+)?'),
    'forbidden dev auth bypass env vars': re.compile(
        r'\b(?:DEV_AUTH_BYPASS|ALLOW_DEV_AUTH_BYPASS|AUTH_BYPASS_ENABLED|ALLOW_INSECURE_DEV_AUTH_BYPASS)\b'
    ),
}

DEV_ONLY_COMPOSE_DEFAULTS: dict[str, re.Pattern[str]] = {
    'dev Keycloak bootstrap admin password': re.compile(
        r'\bKC_BOOTSTRAP_ADMIN_PASSWORD\b.*(?::-[\"\']?admin[\"\']?|[=:]\s*[\"\']?admin[\"\']?$)'
    ),
    'dev MinIO root credentials': re.compile(r'\bMINIO_ROOT_(?:USER|PASSWORD)\b.*(?:=|:)\s*minioadmin\b'),
    'dev inline postgres password': re.compile(r'postgres:postgres'),
}

ENV_EXAMPLE_FORBIDDEN_DEFAULTS: dict[str, re.Pattern[str]] = {
    'reusable Redis password in .env.example': re.compile(r'^\s*REDIS_PASSWORD\s*=\s*\S+'),
    'reusable MinIO credentials in .env.example': re.compile(
        r'^\s*(?:MINIO_ACCESS_KEY_ID|MINIO_SECRET_ACCESS_KEY|S3_ACCESS_KEY_ID|S3_SECRET_ACCESS_KEY)\s*=\s*minioadmin\s*$'
    ),
    'Keycloak admin password in .env.example': re.compile(r'^\s*KEYCLOAK_ADMIN_PASSWORD\s*=\s*admin\s*$'),
}

DEV_ONLY_COMPOSE_NAMES = {'docker-compose.dev.yml', 'docker-compose.full.dev-vault.yml'}
DEPLOYABLE_COMPOSE_NAMES = {'docker-compose.yml', 'docker-compose.full.yml', 'docker-compose.live.yml'}
ALLOWED_DEV_PROFILE_NAMES = {'dev', 'local-dev'}
DEV_COMPOSE_ALLOWED_STRICT_RULES = {
    'VAULT_DEV_ROOT_TOKEN_ID',
    'inline postgres:postgres',
    'inline redis url without auth',
}


def _is_dev_only_compose(file: Path) -> bool:
    return file.name in DEV_ONLY_COMPOSE_NAMES


def _line_has_allowed_dev_profile_marker(line: str) -> bool:
    stripped = line.split('#', 1)[0].strip().strip('-').strip().strip('\"\'')
    return stripped in ALLOWED_DEV_PROFILE_NAMES


def _service_blocks(lines: list[str]) -> list[tuple[int, list[str]]]:
    blocks: list[tuple[int, list[str]]] = []
    in_services = False
    current_start: int | None = None
    current_lines: list[str] = []
    service_header = re.compile(r'^  [A-Za-z0-9_.-]+:\s*(?:#.*)?$')

    for lineno, line in enumerate(lines, start=1):
        if line.startswith('services:'):
            in_services = True
            continue
        if not in_services:
            continue
        if line and not line.startswith(' '):
            break
        if service_header.match(line):
            if current_start is not None:
                blocks.append((current_start, current_lines))
            current_start = lineno
            current_lines = [line]
        elif current_start is not None:
            current_lines.append(line)

    if current_start is not None:
        blocks.append((current_start, current_lines))
    return blocks


def _dev_mode_service_violations(file: Path, lines: list[str]) -> list[Violation]:
    violations: list[Violation] = []
    for start, block in _service_blocks(lines):
        uncommented = [(idx, line) for idx, line in enumerate(block, start=start) if not line.lstrip().startswith('#')]
        dev_command_line = next((idx for idx, line in uncommented if 'server -dev' in line), None)
        if dev_command_line is None:
            continue
        has_dev_profile = any(_line_has_allowed_dev_profile_marker(line) for _, line in uncommented)
        if not has_dev_profile:
            violations.append(
                Violation(
                    file=file,
                    line=dev_command_line,
                    rule='dev compose service lacks dev-only profile',
                    text='deployable compose service contains dev mode without a dev/local-dev profile',
                )
            )
    return violations


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

        lines = file.read_text(encoding='utf-8').splitlines()
        is_env_example = file.name == '.env.example'
        is_compose = file.name.startswith('docker-compose') and file.suffix in {'.yml', '.yaml'}
        is_dev_compose = is_compose and _is_dev_only_compose(file)
        is_deployable_compose = is_compose and file.name in DEPLOYABLE_COMPOSE_NAMES

        if is_deployable_compose:
            violations.extend(_dev_mode_service_violations(file, lines))

        for lineno, line in enumerate(lines, start=1):
            for rule, pattern in STRICT_FORBIDDEN_PATTERNS.items():
                if is_dev_compose and rule in DEV_COMPOSE_ALLOWED_STRICT_RULES:
                    continue
                if pattern.search(line):
                    violations.append(Violation(file=file, line=lineno, rule=rule, text=line.strip()))

            if is_env_example:
                for rule, pattern in ENV_EXAMPLE_FORBIDDEN_DEFAULTS.items():
                    if pattern.search(line):
                        violations.append(Violation(file=file, line=lineno, rule=rule, text=line.strip()))

            if is_compose and not is_dev_compose:
                for rule, pattern in DEV_ONLY_COMPOSE_DEFAULTS.items():
                    if pattern.search(line):
                        violations.append(Violation(file=file, line=lineno, rule=rule, text=line.strip()))
    return violations


def main() -> int:
    violations = find_violations(DEFAULT_TARGETS)
    if violations:
        print('FAIL: Manifest secret hygiene violations detected:')
        for v in violations:
            rel = v.file.relative_to(ROOT)
            print(f' - {rel}:{v.line} [{v.rule}] {v.text}')
        return 1

    print('PASS: Manifest secret hygiene checks passed.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
