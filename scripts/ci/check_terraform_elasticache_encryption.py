"""Enforce ElastiCache encryption policy in Terraform modules.

Fails if any ElastiCache module does not enable at-rest and transit encryption.
"""

from __future__ import annotations

import argparse
import pathlib
import sys


def _scan_for_elasticache_encryption(terraform_dir: pathlib.Path) -> list[str]:
    violations: list[str] = []
    for module_dir in terraform_dir.glob("modules/elasticache/"):
        main_tf = module_dir / "main.tf"
        if not main_tf.exists():
            continue
        source = main_tf.read_text(encoding="utf-8")

        if "at_rest_encryption_enabled" not in source:
            violations.append(f"{main_tf}: Missing at_rest_encryption_enabled")
        elif "at_rest_encryption_enabled = true" not in source:
            violations.append(f"{main_tf}: at_rest_encryption_enabled must be true")

        if "transit_encryption_enabled" not in source:
            violations.append(f"{main_tf}: Missing transit_encryption_enabled")
        elif "transit_encryption_enabled = true" not in source:
            violations.append(f"{main_tf}: transit_encryption_enabled must be true")

    return violations


def main() -> int:
    parser = argparse.ArgumentParser(description="Enforce ElastiCache encryption policy")
    parser.add_argument("terraform_dir", type=pathlib.Path, help="Path to infra/terraform")
    args = parser.parse_args()

    violations = _scan_for_elasticache_encryption(args.terraform_dir)
    if violations:
        print("ElastiCache encryption policy violations found:")
        for v in violations:
            print(f"  - {v}")
        return 1

    print("ElastiCache encryption policy check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
