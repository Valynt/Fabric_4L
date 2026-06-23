#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ALLOWED_DEV_FILES = {
    "infra/compose/docker-compose.full.dev-vault.yml",
    "k8s/dev-only/vault-deployment.yaml",
}
FORBIDDEN_PATTERNS = (
    "VAULT_DEV_ROOT_TOKEN_ID",
    "-dev-root-token-id=",
)
SCAN_GLOBS = (
    "docker-compose*.yml",
    "infra/compose/docker-compose*.yml",
    "k8s/**/*.y*ml",
)


def main() -> int:
    violations: list[str] = []
    scanned: set[Path] = set()
    for pattern in SCAN_GLOBS:
        for file in REPO_ROOT.glob(pattern):
            if not file.is_file():
                continue
            rel = file.relative_to(REPO_ROOT).as_posix()
            scanned.add(file)
            text = file.read_text(encoding="utf-8")
            if rel in ALLOWED_DEV_FILES:
                continue
            for marker in FORBIDDEN_PATTERNS:
                if marker in text:
                    violations.append(f"{rel}: forbidden dev-mode Vault marker '{marker}'")

    if violations:
        print("FAIL: Vault dev-mode boundary violations detected")
        for violation in violations:
            print(f" - {violation}")
        return 1

    print(f"PASS: Vault dev-mode boundary check passed ({len(scanned)} files scanned)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
