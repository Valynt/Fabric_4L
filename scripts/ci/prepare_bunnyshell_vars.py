#!/usr/bin/env python3
"""
Generate formatted Bunnyshell environment variable import files (.bns/vars.env and .bns/secrets.env).

Usage:
    python scripts/ci/prepare_bunnyshell_vars.py [--output-dir .bns] [--from-env .env]

Outputs:
    <output_dir>/vars.env
    <output_dir>/secrets.env
"""

import argparse
import os
import secrets
import sys
from pathlib import Path


SECRET_KEYS = {
    "JWT_SECRET",
    "SERVICE_AUTH_SECRET",
    "API_KEY_HMAC_SECRET",
    "CREDENTIALS_MASTER_KEY",
    "NEO4J_PASSWORD",
    "MINIO_ROOT_PASSWORD",
    "POSTGRES_PASSWORD",
    "REDIS_PASSWORD",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
}

DEFAULT_VARS = {
    "POSTGRES_USER": "fabric_admin",
    "MINIO_ROOT_USER": "minioadmin",
    "LAYER1_ENVIRONMENT": "development",
    "LAYER1_API_PORT": "8000",
    "LOG_LEVEL": "INFO",
}


def generate_random_secret(length: int = 32) -> str:
    return secrets.token_hex(length // 2)


def parse_env_file(filepath: Path) -> dict[str, str]:
    env_vars = {}
    if not filepath.exists():
        return env_vars
    with filepath.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            env_vars[key.strip()] = val.strip().strip("'\"")
    return env_vars


def main():
    parser = argparse.ArgumentParser(description="Prepare Bunnyshell environment variable files.")
    parser.add_argument("--output-dir", default=".bns", help="Output directory (default: .bns)")
    parser.add_argument("--from-env", default=".env", help="Path to input .env file (optional)")
    parser.add_argument("--dry-run", action="store_true", help="Print output without writing files")

    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    env_file = Path(args.from_env)

    source_vars = parse_env_file(env_file)

    vars_data = {}
    secrets_data = {}

    # Standard vars
    for k, v in DEFAULT_VARS.items():
        vars_data[k] = source_vars.get(k, v)

    # Populate secrets
    for key in SECRET_KEYS:
        val = os.getenv(key) or source_vars.get(key)
        if not val or "placeholder" in val.lower() or "devpassword" in val.lower():
            if key in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY"):
                val = f"sk-bunnyshell-placeholder-{generate_random_secret(8)}"
            else:
                val = generate_random_secret(32)
        secrets_data[key] = val

    vars_content = "\n".join(f"{k}={v}" for k, v in sorted(vars_data.items())) + "\n"
    secrets_content = "\n".join(f"{k}={v}" for k, v in sorted(secrets_data.items())) + "\n"

    if args.dry_run:
        print("=== .bns/vars.env ===")
        print(vars_content)
        print("=== .bns/secrets.env ===")
        print(secrets_content)
        return

    output_dir.mkdir(parents=True, exist_ok=True)
    vars_file = output_dir / "vars.env"
    secrets_file = output_dir / "secrets.env"

    vars_file.write_text(vars_content, encoding="utf-8")
    secrets_file.write_text(secrets_content, encoding="utf-8")

    print(f"Successfully generated Bunnyshell env files in {output_dir}/:")
    print(f"  - {vars_file} ({len(vars_data)} variables)")
    print(f"  - {secrets_file} ({len(secrets_data)} secrets)")


if __name__ == "__main__":
    main()
