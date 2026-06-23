"""Terraform staging preflight check.

Fails with a clear message if required AWS/GitHub configuration is missing.
This script is designed to run in GitHub Actions before Terraform commands.

Required environment variables:
  AWS_TERRAFORM_ROLE_ARN : OIDC role ARN for Terraform AWS access
  AWS_REGION             : AWS region (e.g., us-east-1)

Optional:
  GITHUB_ENVIRONMENT     : GitHub environment name (dev/staging/prod)
"""

from __future__ import annotations

import os
import sys

REQUIRED = {
    "AWS_TERRAFORM_ROLE_ARN": "GitHub repository secret for OIDC role ARN",
    "AWS_REGION": "GitHub repository variable for AWS region",
}


def main() -> int:
    missing: list[str] = []
    for key, description in REQUIRED.items():
        value = os.getenv(key, "").strip()
        if not value or value in ("TBD", "arn:aws:iam::123456789012:role/FabricTerraformRole"):
            missing.append(f"  - {key}: {description}")

    if missing:
        print("ERROR: Terraform preflight check failed. Missing required configuration:")
        for item in missing:
            print(item)
        print()
        print("Remediation:")
        print("  1. Go to GitHub repository Settings -> Secrets and variables")
        print("  2. Add AWS_TERRAFORM_ROLE_ARN as a repository secret")
        print("  3. Add AWS_REGION as a repository variable")
        print("  4. Ensure the IAM role trusts the GitHub OIDC provider")
        print("  5. Re-run this workflow")
        return 1

    role_arn = os.environ["AWS_TERRAFORM_ROLE_ARN"]
    region = os.environ["AWS_REGION"]
    env_name = os.getenv("GITHUB_ENVIRONMENT", "unknown")

    print("Terraform preflight check passed.")
    print(f"  AWS_TERRAFORM_ROLE_ARN: {'*' * 10}{role_arn[-20:]}")
    print(f"  AWS_REGION:             {region}")
    print(f"  Environment:            {env_name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
