"""Enforce S3 encryption policy in Terraform modules.

Fails if any S3 module does not enable server-side encryption.
"""

from __future__ import annotations

import argparse
import pathlib
import sys


def _scan_for_s3_encryption(terraform_dir: pathlib.Path) -> list[str]:
    violations: list[str] = []
    for module_dir in terraform_dir.glob("modules/s3/"):
        main_tf = module_dir / "main.tf"
        if not main_tf.exists():
            continue
        source = main_tf.read_text(encoding="utf-8")

        if "server_side_encryption_configuration" not in source and "sse_algorithm" not in source:
            violations.append(f"{main_tf}: Missing server-side encryption configuration")

    return violations


def main() -> int:
    parser = argparse.ArgumentParser(description="Enforce S3 encryption policy")
    parser.add_argument("terraform_dir", type=pathlib.Path, help="Path to infra/terraform")
    args = parser.parse_args()

    violations = _scan_for_s3_encryption(args.terraform_dir)
    if violations:
        print("S3 encryption policy violations found:")
        for v in violations:
            print(f"  - {v}")
        return 1

    print("S3 encryption policy check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
