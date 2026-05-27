#!/usr/bin/env python3
from __future__ import annotations

import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENV_EXAMPLE = ROOT / ".env.example"

SERVICE_ENVS = {
    "layer1-ingestion": ["LAYER1_DATABASE_URL", "DATABASE_URL"],
    "layer2-extraction": ["LAYER2_DATABASE_URL", "DATABASE_URL"],
    "layer4-agents": ["LAYER4_DATABASE_URL", "CHECKPOINT_DATABASE_URL", "DATABASE_URL"],
    "layer5-ground-truth": ["LAYER5_DATABASE_URL", "DATABASE_URL", "DATABASE_URL_SYNC"],
    "layer6-benchmarks": ["LAYER6_DATABASE_URL", "DATABASE_URL", "DATABASE_URL_SYNC"],
}


def assert_single_head_per_service() -> list[str]:
    errors: list[str] = []
    services_dir = ROOT / "services"
    for service, _ in SERVICE_ENVS.items():
        versions = services_dir / service / "migrations" / "versions"
        if not versions.exists():
            continue
        revision_markers = 0
        for pyf in versions.glob("*.py"):
            text = pyf.read_text(encoding="utf-8")
            revision_markers += len(re.findall(r"^revision\s*=", text, flags=re.MULTILINE))
    return errors


def parse_env_example() -> dict[str, str]:
    parsed = {}
    for line in ENV_EXAMPLE.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        parsed[key.strip()] = value.strip()
    return parsed


def assert_runtime_urls() -> list[str]:
    env = parse_env_example()
    errors: list[str] = []
    for service, env_vars in SERVICE_ENVS.items():
        if not any(name in env for name in env_vars):
            errors.append(f"{service}: missing expected DB env vars in .env.example ({env_vars})")
            continue
        for var in env_vars:
            if var in env and env[var] and "postgresql://" not in env[var] and "postgresql+" not in env[var]:
                errors.append(f"{service}: env var {var} must be PostgreSQL DSN")
    return errors


def main() -> int:
    errors = [*assert_single_head_per_service(), *assert_runtime_urls()]
    if errors:
        for err in errors:
            print(f"ERROR: {err}")
        return 1
    print("Migration/runtime consistency checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
