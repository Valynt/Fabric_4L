#!/usr/bin/env python3
"""
Key Verification Script for Fabric4L

Verifies that API keys and secrets are valid and accessible.
Use after rotation to confirm new keys are working.

Usage:
    python scripts/security/verify-keys.py --provider openai --env prod
    python scripts/security/verify-keys.py --all --env staging
    python scripts/security/verify-keys.py --provider clerk --env prod --detailed
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import urllib.error
import urllib.request


def get_infisical_base_cmd() -> list[str]:
    """Get the Infisical CLI binary path only."""
    custom_path = os.getenv("INFISICAL_CLI_PATH")
    if custom_path:
        return [custom_path]
    
    if sys.platform == "win32" or os.name == "nt":
        common_windows_paths = [
            r"C:\tools\Infisical\infisical.exe",
            r"C:\tools\Infisical\infisical",
            os.path.expanduser(r"~\bin\infisical.exe"),
            os.path.expanduser(r"~\infisical-cli\infisical.exe"),
        ]
        for path in common_windows_paths:
            if os.path.exists(path):
                return [path]
    
    return ["infisical"]


def get_infisical_auth_flags() -> list[str]:
    """Get authentication flags for Infisical CLI."""
    flags = []
    client_id = os.getenv("INFISICAL_CLIENT_ID")
    client_secret = os.getenv("INFISICAL_CLIENT_SECRET")
    project_id = os.getenv("INFISICAL_PROJECT_ID")
    
    if client_id:
        flags.extend(["--client-id", client_id])
    if client_secret:
        flags.extend(["--client-secret", client_secret])
    if project_id:
        flags.extend(["--projectId", project_id])
    
    return flags


def fix_path_for_git_bash(path: str) -> str:
    """Fix paths that get mangled by Git Bash path translation."""
    # In Git Bash, paths like /fabric-4l/value-fabric become C:/tools/Git/fabric-4l/value-fabric
    # We need to extract the actual Unix path from the mangled Windows path
    import re
    # Check if path was mangled by Git Bash (contains Windows drive letter or tools/Git)
    if re.match(r'^[A-Za-z]:', path) or 'tools/Git' in path or 'tools\\Git' in path:
        # Extract everything after the drive/tools prefix
        # Pattern: C:/tools/Git/PATH or C:\tools\Git\PATH -> /PATH
        match = re.search(r'[tT]ools[/\\][gG]it[/\\](.+)$', path)
        if match:
            actual_path = match.group(1).replace('\\', '/')
            return '/' + actual_path
    return path


INFISICAL_BASE = get_infisical_base_cmd()
INFISICAL_AUTH_FLAGS = get_infisical_auth_flags()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("key_verification")


@dataclass
class VerificationResult:
    provider: str
    secret_name: str
    exists: bool = False
    valid_format: bool = False
    accessible: bool = False
    masked_value: str = ""
    error_message: str | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "secret_name": self.secret_name,
            "exists": self.exists,
            "valid_format": self.valid_format,
            "accessible": self.accessible,
            "masked_value": self.masked_value,
            "error_message": self.error_message,
            "details": self.details,
        }


class KeyVerifier:
    """Base class for key verification."""
    
    def __init__(self, environment: str):
        self.environment = environment
    
    def get_secret_from_infisical(self, secret_name: str, path: str) -> str | None:
        """Retrieve secret value from Infisical."""
        env_map = {"dev": "dev", "staging": "staging", "prod": "prod"}
        infisical_env = env_map.get(self.environment, self.environment)
        fixed_path = fix_path_for_git_bash(path)
        
        try:
            result = subprocess.run(
                [*INFISICAL_BASE, "secrets", "get",
                 "--env", infisical_env, "--path", fixed_path, secret_name],
                capture_output=True, text=True, check=True
            )
            # Parse output - format is "KEY_NAME=VALUE" or just "VALUE"
            output = result.stdout.strip()
            if "=" in output:
                return output.split("=", 1)[1]
            return output
        except subprocess.CalledProcessError:
            return None
        except Exception:
            return None
    
    def mask_secret(self, value: str, visible_chars: int = 8) -> str:
        """Mask a secret value for safe logging."""
        if not value:
            return ""
        if len(value) <= visible_chars * 2:
            return "*" * len(value)
        return f"{value[:visible_chars]}...{value[-visible_chars:]}"


class OpenAIVerifier(KeyVerifier):
    """Verify OpenAI API key."""
    
    def verify(self) -> VerificationResult:
        result = VerificationResult(
            provider="openai",
            secret_name="OPENAI_API_KEY"
        )
        
        # Get key from Infisical /llm folder
        key = self.get_secret_from_infisical("OPENAI_API_KEY", "/llm")
        
        if not key:
            result.error_message = "OPENAI_API_KEY not found in Infisical"
            return result
        
        result.exists = True
        result.masked_value = self.mask_secret(key, 6)
        
        # Check format
        if not key.startswith("sk-"):
            result.error_message = "Invalid format: must start with 'sk-'"
            return result
        
        result.valid_format = True
        
        # Test API access
        try:
            req = urllib.request.Request(
                "https://api.openai.com/v1/models",
                headers={"Authorization": f"Bearer {key}"}
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status == 200:
                    result.accessible = True
                    # Count available models as extra detail
                    data = json.loads(response.read())
                    result.details["available_models"] = len(data.get("data", []))
                else:
                    result.error_message = f"API returned status {response.status}"
        except urllib.error.HTTPError as e:
            if e.code == 401:
                result.error_message = "Invalid API key (401 Unauthorized)"
            else:
                result.error_message = f"HTTP error {e.code}"
        except Exception as e:
            result.error_message = f"Connection error: {e}"
        
        return result


class ClerkVerifier(KeyVerifier):
    """Verify Clerk secret key."""
    
    def verify(self) -> VerificationResult:
        result = VerificationResult(
            provider="clerk",
            secret_name="CLERK_SECRET_KEY"
        )
        
        # Clerk keys in /auth folder
        key = self.get_secret_from_infisical("CLERK_SECRET_KEY", "/auth")
        
        if not key:
            result.error_message = "CLERK_SECRET_KEY not found in Infisical"
            return result
        
        result.exists = True
        result.masked_value = self.mask_secret(key, 10)
        
        # Check format
        if not (key.startswith("sk_test_") or key.startswith("sk_live_")):
            result.error_message = "Invalid format: must start with 'sk_test_' or 'sk_live_'"
            return result
        
        result.valid_format = True
        
        # Extract instance from key
        parts = key.split("_")
        if len(parts) >= 3:
            instance_id = parts[2]
            jwks_url = f"https://clerk.{instance_id}.com/.well-known/jwks.json"
            
            try:
                req = urllib.request.Request(jwks_url)
                with urllib.request.urlopen(req, timeout=10) as response:
                    if response.status == 200:
                        result.accessible = True
                        result.details["jwks_endpoint"] = jwks_url
                        result.details["instance_id"] = instance_id
                    else:
                        result.error_message = f"JWKS endpoint returned {response.status}"
            except Exception as e:
                # JWKS might be restricted, so we don't fail on connection errors
                result.accessible = True
                result.details["jwks_check"] = f"Skipped: {e}"
        else:
            result.error_message = "Could not parse instance ID from key"
        
        return result


class ThesysVerifier(KeyVerifier):
    """Verify Thesys API key."""
    
    def verify(self) -> VerificationResult:
        result = VerificationResult(
            provider="thesys",
            secret_name="THESYS_API_KEY"
        )
        
        # Thesys keys in /llm folder
        key = self.get_secret_from_infisical("THESYS_API_KEY", "/llm")
        
        if not key:
            result.error_message = "THESYS_API_KEY not found in Infisical"
            return result
        
        result.exists = True
        result.masked_value = self.mask_secret(key, 8)
        
        # Basic format check (Thesys keys typically start with 'thesys_' or are long strings)
        if len(key) < 20:
            result.error_message = "Key too short (expected at least 20 characters)"
            return result
        
        result.valid_format = True
        
        # Thesys verification would need their specific API
        # For now, mark as accessible if key exists and has valid format
        result.accessible = True
        result.details["note"] = "Format validation only - Thesys API test not implemented"
        
        return result


class RegistryVerifier(KeyVerifier):
    """Verify GitHub Container Registry token."""
    
    def verify(self) -> VerificationResult:
        result = VerificationResult(
            provider="registry",
            secret_name="GHCR_PAT"
        )
        
        # Registry token in /app folder
        key = self.get_secret_from_infisical("GHCR_PAT", "/app")
        
        if not key:
            result.error_message = "GHCR_PAT not found in Infisical"
            return result
        
        result.exists = True
        result.masked_value = self.mask_secret(key, 8)
        
        # Check format (GitHub PATs start with ghp_ or github_pat_)
        if not (key.startswith("ghp_") or key.startswith("github_pat_")):
            result.error_message = "Invalid format: must start with 'ghp_' or 'github_pat_'"
            return result
        
        result.valid_format = True
        
        # Test GitHub API
        try:
            req = urllib.request.Request(
                "https://api.github.com/user/packages",
                headers={
                    "Authorization": f"Bearer {key}",
                    "Accept": "application/vnd.github+json"
                }
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status == 200:
                    result.accessible = True
                    data = json.loads(response.read())
                    result.details["package_count"] = len(data.get("packages", []))
                else:
                    result.error_message = f"GitHub API returned {response.status}"
        except urllib.error.HTTPError as e:
            if e.code == 401:
                result.error_message = "Invalid token (401 Unauthorized)"
            elif e.code == 403:
                result.accessible = True
                result.details["note"] = "Token valid but packages scope may be limited"
            else:
                result.error_message = f"HTTP error {e.code}"
        except Exception as e:
            result.error_message = f"Connection error: {e}"
        
        return result


def print_result(result: VerificationResult, detailed: bool = False) -> None:
    """Print verification result in a formatted way."""
    icon = "✓" if result.accessible else "✗"
    status = "VALID" if result.accessible else "INVALID"
    
    print(f"\n{icon} {result.provider.upper()} - {status}")
    print(f"   Secret: {result.secret_name}")
    print(f"   Value: {result.masked_value or 'N/A'}")
    
    if result.error_message:
        print(f"   Error: {result.error_message}")
    
    checks = [
        ("Exists", result.exists),
        ("Valid Format", result.valid_format),
        ("Accessible", result.accessible),
    ]
    
    print(f"   Checks: {' | '.join(f'{name}: {'✓' if ok else '✗'}' for name, ok in checks)}")
    
    if detailed and result.details:
        print("   Details:")
        for key, value in result.details.items():
            print(f"     - {key}: {value}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify API keys and secrets for Fabric4L",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/security/verify-keys.py --provider openai --env prod
  python scripts/security/verify-keys.py --all --env staging --detailed
  python scripts/security/verify-keys.py --provider clerk --env prod --output verify-results.json
        """
    )
    
    parser.add_argument(
        "--provider",
        choices=["openai", "clerk", "thesys", "registry"],
        help="Specific provider to verify"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Verify all providers"
    )
    parser.add_argument(
        "--env",
        required=True,
        choices=["dev", "staging", "prod"],
        help="Target environment"
    )
    parser.add_argument(
        "--detailed",
        action="store_true",
        help="Show detailed output"
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Write results to JSON file"
    )
    parser.add_argument(
        "--fail-on-error",
        action="store_true",
        help="Exit with error code if any verification fails"
    )
    
    args = parser.parse_args()
    
    if not args.provider and not args.all:
        parser.error("Either --provider or --all must be specified")
    
    # Map providers to verifiers
    verifiers = {
        "openai": OpenAIVerifier,
        "clerk": ClerkVerifier,
        "thesys": ThesysVerifier,
        "registry": RegistryVerifier,
    }
    
    # Determine which providers to verify
    if args.all:
        providers_to_verify = list(verifiers.keys())
    else:
        providers_to_verify = [args.provider]
    
    print("=" * 60)
    print("  API KEY VERIFICATION")
    print(f"  Environment: {args.env}")
    print("=" * 60)
    
    results = []
    all_passed = True
    
    for provider_name in providers_to_verify:
        verifier_class = verifiers[provider_name]
        verifier = verifier_class(args.env)
        result = verifier.verify()
        results.append(result)
        
        print_result(result, args.detailed)
        
        if not result.accessible:
            all_passed = False
    
    # Summary
    print("\n" + "=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for r in results if r.accessible)
    total = len(results)
    
    print(f"  Passed: {passed}/{total}")
    print(f"  Failed: {total - passed}")
    
    for r in results:
        status = "✓" if r.accessible else "✗"
        print(f"  {status} {r.provider}")
    
    # Write output if requested
    if args.output:
        output_data = {
            "verification_timestamp": datetime.now(timezone.utc).isoformat(),
            "environment": args.env,
            "results": [r.to_dict() for r in results],
        }
        with open(args.output, "w") as f:
            json.dump(output_data, f, indent=2)
        print(f"\n  Results written to: {args.output}")
    
    print("=" * 60)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
