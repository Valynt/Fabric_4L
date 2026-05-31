"""Enforce RDS backup retention policy in Terraform modules.

Fails if any RDS module in the Terraform tree has a backup_retention_period
less than the required minimum for its environment.
"""

from __future__ import annotations

import argparse
import pathlib
import sys


def _scan_for_rds_backup_policy(terraform_dir: pathlib.Path) -> list[str]:
    violations: list[str] = []
    for env_dir in terraform_dir.glob("environments/*/"):
        main_tf = env_dir / "main.tf"
        if not main_tf.exists():
            continue
        source = main_tf.read_text(encoding="utf-8")

        env_name = env_dir.name
        expected_min = 7 if env_name == "prod" else 1

        if 'module "rds"' not in source:
            continue

        if "backup_retention_period" not in source:
            violations.append(
                f"{main_tf}: RDS module missing backup_retention_period (minimum {expected_min} required for {env_name})"
            )
            continue

        for line in source.splitlines():
            stripped = line.strip()
            if stripped.startswith("backup_retention_period"):
                try:
                    value = int(stripped.split("=")[-1].strip())
                except ValueError:
                    continue
                if value < expected_min:
                    violations.append(
                        f"{main_tf}: backup_retention_period={value} < minimum {expected_min} for {env_name}"
                    )
                break

    return violations


def main() -> int:
    parser = argparse.ArgumentParser(description="Enforce RDS backup retention policy")
    parser.add_argument("terraform_dir", type=pathlib.Path, help="Path to infra/terraform")
    args = parser.parse_args()

    violations = _scan_for_rds_backup_policy(args.terraform_dir)
    if violations:
        print("RDS backup retention policy violations found:")
        for v in violations:
            print(f"  - {v}")
        return 1

    print("RDS backup retention policy check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
